import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:baalar/core/network/api_client.dart';
import 'package:baalar/features/orders/data/models/order_model.dart';

class OrderRepository {
  final ApiClient _apiClient;

  OrderRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  Future<OrderListResponse> getOrders({
    String? search,
    String? sortBy,
    String? sortOrder,
  }) async {
    final queryParams = <String, dynamic>{};
    if (search != null && search.isNotEmpty) queryParams['search'] = search;
    if (sortBy != null) queryParams['sort_by'] = sortBy;
    if (sortOrder != null) queryParams['sort_order'] = sortOrder;

    final response = await _apiClient.get('/orders/', queryParams: queryParams);
    return OrderListResponse.fromJson(response.data);
  }

  Future<OrderModel> getOrderById(int id) async {
    final response = await _apiClient.get('/orders/$id');
    return OrderModel.fromJson(response.data);
  }
}

final orderRepositoryProvider = Provider<OrderRepository>((ref) {
  return OrderRepository(apiClient: ref.watch(apiClientProvider));
});
