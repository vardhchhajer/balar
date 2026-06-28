import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:baalar/core/network/api_client.dart';
import 'package:baalar/core/storage/secure_storage.dart';
import 'package:baalar/features/auth/data/models/auth_model.dart';

class AuthRepository {
  final ApiClient _apiClient;
  final SecureStorage _secureStorage;

  AuthRepository({
    required ApiClient apiClient,
    required SecureStorage secureStorage,
  })  : _apiClient = apiClient,
        _secureStorage = secureStorage;

  Future<TokenResponse> login(String username, String password) async {
    final response = await _apiClient.post(
      '/auth/login',
      data: LoginRequest(username: username, password: password).toJson(),
    );

    final tokenResponse = TokenResponse.fromJson(response.data);

    // Store tokens
    await _secureStorage.saveAccessToken(tokenResponse.accessToken);
    await _secureStorage.saveRefreshToken(tokenResponse.refreshToken);

    // Fetch and store user profile info
    try {
      final profileResponse = await _apiClient.get('/profile');
      final data = profileResponse.data;
      await _secureStorage.saveUserInfo(
        partyCode: data['party_code'] ?? '',
        fullName: data['full_name'] ?? '',
      );
    } catch (_) {
      // Non-critical: profile info is supplementary
    }

    return tokenResponse;
  }

  Future<void> refreshToken() async {
    final refreshToken = await _secureStorage.getRefreshToken();
    if (refreshToken == null) throw Exception('No refresh token');

    final response = await _apiClient.post('/auth/refresh');
    final newAccessToken = response.data['access_token'] as String;
    await _secureStorage.saveAccessToken(newAccessToken);
  }

  Future<void> logout() async {
    try {
      await _apiClient.post('/auth/logout');
    } catch (_) {
      // Proceed with local logout even if server call fails
    } finally {
      await _secureStorage.clearAll();
    }
  }
}

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(
    apiClient: ref.watch(apiClientProvider),
    secureStorage: ref.watch(secureStorageProvider),
  );
});
