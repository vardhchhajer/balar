import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:baalar/core/errors/app_exception.dart';
import 'package:baalar/core/storage/secure_storage.dart';
import 'package:baalar/features/auth/data/repositories/auth_repository.dart';

enum AuthStatus { initial, authenticated, unauthenticated, loading }

class AuthState {
  final AuthStatus status;
  final String? errorMessage;
  final String? role;

  const AuthState({required this.status, this.errorMessage, this.role});

  AuthState copyWith({AuthStatus? status, String? errorMessage, String? role}) {
    return AuthState(
      status: status ?? this.status,
      errorMessage: errorMessage,
      role: role ?? this.role,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  final AuthRepository _authRepository;
  final SecureStorage _secureStorage;

  AuthNotifier({
    required AuthRepository authRepository,
    required SecureStorage secureStorage,
  })  : _authRepository = authRepository,
        _secureStorage = secureStorage,
        super(const AuthState(status: AuthStatus.initial)) {
    checkAuthStatus();
  }

  Future<void> checkAuthStatus() async {
    try {
      final token = await _secureStorage.getAccessToken();
      if (token != null && token.isNotEmpty) {
        final role = await _secureStorage.getRole();
        state = AuthState(status: AuthStatus.authenticated, role: role);
      } else {
        state = const AuthState(status: AuthStatus.unauthenticated);
      }
    } catch (e) {
      state = const AuthState(status: AuthStatus.unauthenticated);
    }
  }

  Future<void> login(String username, String password) async {
    state = const AuthState(status: AuthStatus.loading);
    try {
      await _authRepository.login(username, password);
      final role = await _secureStorage.getRole();
      state = AuthState(status: AuthStatus.authenticated, role: role);
    } on DioException catch (e) {
      String message;
      final error = e.error;
      if (error is AppException) {
        message = error.message;
      } else if (e.response?.data is Map && e.response?.data['detail'] != null) {
        message = e.response!.data['detail'].toString();
      } else {
        message = 'Something went wrong. Please try again.';
      }
      state = AuthState(status: AuthStatus.unauthenticated, errorMessage: message);
    } catch (e) {
      state = AuthState(
        status: AuthStatus.unauthenticated,
        errorMessage: e.toString(),
      );
    }
  }

  Future<void> logout() async {
    try {
      await _authRepository.logout();
    } catch (_) {}
    state = const AuthState(status: AuthStatus.unauthenticated);
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(
    authRepository: ref.watch(authRepositoryProvider),
    secureStorage: ref.watch(secureStorageProvider),
  );
});
