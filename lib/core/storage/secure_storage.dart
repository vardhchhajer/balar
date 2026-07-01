import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class SecureStorage {
  static const _accessTokenKey = 'balar_access_token';
  static const _refreshTokenKey = 'balar_refresh_token';
  static const _partyCodeKey = 'balar_party_code';
  static const _fullNameKey = 'balar_full_name';
  static const _roleKey = 'balar_role';

  final FlutterSecureStorage? _secureStorage;
  
  // Fallback in-memory store for web
  static final Map<String, String> _memStore = {};

  SecureStorage()
      : _secureStorage = kIsWeb ? null : const FlutterSecureStorage();

  Future<void> saveAccessToken(String token) async {
    if (kIsWeb) {
      _memStore[_accessTokenKey] = token;
    } else {
      await _secureStorage!.write(key: _accessTokenKey, value: token);
    }
  }

  Future<String?> getAccessToken() async {
    if (kIsWeb) {
      return _memStore[_accessTokenKey];
    }
    return await _secureStorage!.read(key: _accessTokenKey);
  }

  Future<void> saveRefreshToken(String token) async {
    if (kIsWeb) {
      _memStore[_refreshTokenKey] = token;
    } else {
      await _secureStorage!.write(key: _refreshTokenKey, value: token);
    }
  }

  Future<String?> getRefreshToken() async {
    if (kIsWeb) {
      return _memStore[_refreshTokenKey];
    }
    return await _secureStorage!.read(key: _refreshTokenKey);
  }

  Future<void> saveUserInfo({
    required String partyCode,
    required String fullName,
    String? role,
  }) async {
    if (kIsWeb) {
      _memStore[_partyCodeKey] = partyCode;
      _memStore[_fullNameKey] = fullName;
      if (role != null) _memStore[_roleKey] = role;
    } else {
      await _secureStorage!.write(key: _partyCodeKey, value: partyCode);
      await _secureStorage!.write(key: _fullNameKey, value: fullName);
      if (role != null) await _secureStorage!.write(key: _roleKey, value: role);
    }
  }

  Future<String?> getRole() async {
    if (kIsWeb) return _memStore[_roleKey];
    return await _secureStorage!.read(key: _roleKey);
  }

  Future<String?> getPartyCode() async {
    if (kIsWeb) return _memStore[_partyCodeKey];
    return await _secureStorage!.read(key: _partyCodeKey);
  }

  Future<String?> getFullName() async {
    if (kIsWeb) return _memStore[_fullNameKey];
    return await _secureStorage!.read(key: _fullNameKey);
  }

  Future<void> clearAll() async {
    if (kIsWeb) {
      _memStore.clear();
    } else {
      await _secureStorage!.deleteAll();
    }
  }
}

final secureStorageProvider = Provider<SecureStorage>((ref) {
  return SecureStorage();
});
