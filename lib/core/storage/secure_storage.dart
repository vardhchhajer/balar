import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class SecureStorage {
  static const _accessTokenKey = 'access_token';
  static const _refreshTokenKey = 'refresh_token';
  static const _partyCodeKey = 'party_code';
  static const _fullNameKey = 'full_name';

  final FlutterSecureStorage _storage;

  SecureStorage({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  // Access Token
  Future<void> saveAccessToken(String token) async {
    await _storage.write(key: _accessTokenKey, value: token);
  }

  Future<String?> getAccessToken() async {
    return await _storage.read(key: _accessTokenKey);
  }

  // Refresh Token
  Future<void> saveRefreshToken(String token) async {
    await _storage.write(key: _refreshTokenKey, value: token);
  }

  Future<String?> getRefreshToken() async {
    return await _storage.read(key: _refreshTokenKey);
  }

  // User Info
  Future<void> saveUserInfo({
    required String partyCode,
    required String fullName,
  }) async {
    await _storage.write(key: _partyCodeKey, value: partyCode);
    await _storage.write(key: _fullNameKey, value: fullName);
  }

  Future<String?> getPartyCode() async {
    return await _storage.read(key: _partyCodeKey);
  }

  Future<String?> getFullName() async {
    return await _storage.read(key: _fullNameKey);
  }

  // Clear All
  Future<void> clearAll() async {
    await _storage.deleteAll();
  }
}

final secureStorageProvider = Provider<SecureStorage>((ref) {
  return SecureStorage();
});
