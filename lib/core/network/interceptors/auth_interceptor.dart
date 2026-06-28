import 'dart:async';

import 'package:dio/dio.dart';
import 'package:baalar/core/storage/secure_storage.dart';

class AuthInterceptor extends Interceptor {
  final SecureStorage secureStorage;
  final Dio dio;

  bool _isRefreshing = false;
  final List<_QueuedRequest> _queue = [];

  AuthInterceptor({required this.secureStorage, required this.dio});

  @override
  void onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final token = await secureStorage.getAccessToken();
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode != 401) {
      handler.next(err);
      return;
    }

    // Skip refresh for auth endpoints
    final path = err.requestOptions.path;
    if (path.contains('/auth/login') || path.contains('/auth/refresh')) {
      handler.next(err);
      return;
    }

    if (_isRefreshing) {
      // Queue the request while refresh is in progress
      final completer = Completer<Response>();
      _queue.add(_QueuedRequest(
        requestOptions: err.requestOptions,
        completer: completer,
      ));
      try {
        final response = await completer.future;
        handler.resolve(response);
      } catch (e) {
        handler.next(err);
      }
      return;
    }

    _isRefreshing = true;

    try {
      final refreshToken = await secureStorage.getRefreshToken();
      if (refreshToken == null) {
        await _handleRefreshFailure();
        handler.next(err);
        return;
      }

      // Attempt refresh with 10s timeout
      final refreshDio = Dio(BaseOptions(
        baseUrl: dio.options.baseUrl,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
      ));

      final response = await refreshDio.post(
        '/auth/refresh',
        options: Options(headers: {'Authorization': 'Bearer $refreshToken'}),
      );

      final newAccessToken = response.data['access_token'] as String;
      await secureStorage.saveAccessToken(newAccessToken);

      // Retry original request
      final retryResponse =
          await _retryRequest(err.requestOptions, newAccessToken);
      handler.resolve(retryResponse);

      // Retry queued requests
      for (final queued in _queue) {
        try {
          final queuedResponse =
              await _retryRequest(queued.requestOptions, newAccessToken);
          queued.completer.complete(queuedResponse);
        } catch (e) {
          queued.completer.completeError(e);
        }
      }
    } catch (e) {
      await _handleRefreshFailure();
      handler.next(err);

      // Fail all queued requests
      for (final queued in _queue) {
        queued.completer.completeError(err);
      }
    } finally {
      _isRefreshing = false;
      _queue.clear();
    }
  }

  Future<Response> _retryRequest(RequestOptions options, String token) async {
    final retryDio = Dio(BaseOptions(baseUrl: dio.options.baseUrl));
    return await retryDio.request(
      options.path,
      data: options.data,
      queryParameters: options.queryParameters,
      options: Options(
        method: options.method,
        headers: {
          ...options.headers,
          'Authorization': 'Bearer $token',
        },
      ),
    );
  }

  Future<void> _handleRefreshFailure() async {
    await secureStorage.clearAll();
  }
}

class _QueuedRequest {
  final RequestOptions requestOptions;
  final Completer<Response> completer;

  _QueuedRequest({required this.requestOptions, required this.completer});
}
