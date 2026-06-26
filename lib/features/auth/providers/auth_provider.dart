import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:balar/core/errors/app_exception.dart';
import 'package:balar/core/storage/secure_storage.dart';
import 'package:balar/features/auth/data/repositories/auth_repository.dart';

enum AuthStatus { initial, authenticated, unauthenticated, loading }

class AuthState {
  final AuthStatus status;
  final String? errorMessage;

  const AuthState({required this.status, this.errorMessage});

  AuthState copyWith({AuthStatus? status, String? errorMessage}) {
    return AuthState(
      status: status ?? this.status,
      errorMessage: errorMessage,
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
    final token = await _secureStorage.getAccessToken();
    if (token != null) {
      state = const AuthState(status: AuthStatus.authenticated);
    } else {
      state = const AuthState(status: AuthStatus.unauthenticated);
    }
  }

  Future<void> login(String username, String password) async {
    state = const AuthState(status: AuthStatus.loading);
    try {
      await _authRepository.login(username, password);

      // Fetch profile to get user info for storage
      await _secureStorage.saveUserInfo(
        partyCode: '',
        fullName: '',
      );

      state = const AuthState(status: AuthStatus.authenticated);
    } on DioException catch (e) {
      final error = e.error;
      String message;
      if (error is AppException) {
        message = error.message;
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
    await _authRepository.logout();
    state = const AuthState(status: AuthStatus.unauthenticated);
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(
    authRepository: ref.watch(authRepositoryProvider),
    secureStorage: ref.watch(secureStorageProvider),
  );
});
