import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:balar/core/network/api_client.dart';
import 'package:balar/features/outstanding/data/models/outstanding_model.dart';

class OutstandingRepository {
  final ApiClient _apiClient;

  OutstandingRepository({required ApiClient apiClient})
      : _apiClient = apiClient;

  Future<OutstandingListResponse> getOutstandingBills() async {
    final response = await _apiClient.get('/outstanding');
    return OutstandingListResponse.fromJson(response.data);
  }
}

final outstandingRepositoryProvider = Provider<OutstandingRepository>((ref) {
  return OutstandingRepository(apiClient: ref.watch(apiClientProvider));
});
