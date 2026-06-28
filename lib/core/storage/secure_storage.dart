import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/foundation.dart';

// Simple storage using a Map for web (flutter_secure_storage has bugs on web)
// For mobile builds, swap this back to flutter_secure_storage
class SecureStorage {
  static const _accessTokenKey = 'balar_access_token';
  static const _refreshTokenKey = 'balar_refresh_token';
  static const _partyCodeKey = 'balar_party_code';
  static const _fullNameKey = 'balar_full_name';

  // In-memory store that persists for the session
  static final Map<String, String> _store = {};

  Future<void> saveAccessToken(String token) async {
    _store[_accessTokenKey] = token;
  }

  Future<String?> getAccessToken() async {
    return _store[_accessTokenKey];
  }

  Future<void> saveRefreshToken(String token) async {
    _store[_refreshTokenKey] = token;
  }

  Future<String?> getRefreshToken() async {
    return _store[_refreshTokenKey];
  }

  Future<void> saveUserInfo({
    required String partyCode,
    required String fullName,
  }) async {
    _store[_partyCodeKey] = partyCode;
    _store[_fullNameKey] = fullName;
  }

  Future<String?> getPartyCode() async {
    return _store[_partyCodeKey];
  }

  Future<String?> getFullName() async {
    return _store[_fullNameKey];
  }

  Future<void> clearAll() async {
    _store.clear();
  }
}

final secureStorageProvider = Provider<SecureStorage>((ref) {
  return SecureStorage();
});
