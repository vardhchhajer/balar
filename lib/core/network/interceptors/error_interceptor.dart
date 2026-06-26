import 'package:dio/dio.dart';
import 'package:balar/core/errors/app_exception.dart';

class ErrorInterceptor extends Interceptor {
  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    switch (err.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.receiveTimeout:
      case DioExceptionType.sendTimeout:
        handler.next(DioException(
          requestOptions: err.requestOptions,
          error: const NetworkException(),
          type: err.type,
        ));
        return;
      case DioExceptionType.connectionError:
        handler.next(DioException(
          requestOptions: err.requestOptions,
          error: const NetworkException(),
          type: err.type,
        ));
        return;
      case DioExceptionType.badResponse:
        final statusCode = err.response?.statusCode;
        final detail = _extractDetail(err.response);

        AppException exception;
        switch (statusCode) {
          case 401:
            exception = UnauthorizedException(message: detail);
            break;
          case 403:
            exception = ForbiddenException(message: detail);
            break;
          case 404:
            exception = NotFoundException(message: detail);
            break;
          default:
            exception = ServerException(message: detail);
        }
        handler.next(DioException(
          requestOptions: err.requestOptions,
          error: exception,
          response: err.response,
          type: err.type,
        ));
        return;
      default:
        handler.next(err);
    }
  }

  String _extractDetail(Response? response) {
    if (response?.data is Map<String, dynamic>) {
      final data = response!.data as Map<String, dynamic>;
      if (data.containsKey('detail') && data['detail'] is String) {
        return data['detail'] as String;
      }
    }
    return 'Something went wrong. Please try again.';
  }
}
