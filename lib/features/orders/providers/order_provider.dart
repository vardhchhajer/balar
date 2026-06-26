import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:balar/features/orders/data/models/order_model.dart';
import 'package:balar/features/orders/data/repositories/order_repository.dart';

class OrdersNotifier extends StateNotifier<AsyncValue<List<OrderModel>>> {
  final OrderRepository _repository;
  List<OrderModel> _allOrders = [];
  String _searchQuery = '';
  Timer? _debounceTimer;

  OrdersNotifier({required OrderRepository repository})
      : _repository = repository,
        super(const AsyncValue.loading());

  Future<void> fetchOrders() async {
    state = const AsyncValue.loading();
    try {
      final response = await _repository.getOrders();
      _allOrders = response.orders;
      _applyFilter();
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  void searchOrders(String query) {
    _debounceTimer?.cancel();
    _debounceTimer = Timer(const Duration(milliseconds: 400), () {
      _searchQuery = query;
      _applyFilter();
    });
  }

  void _applyFilter() {
    if (_searchQuery.isEmpty) {
      state = AsyncValue.data(_allOrders);
    } else {
      final filtered = _allOrders
          .where((order) => order.orderNo
              .toLowerCase()
              .contains(_searchQuery.toLowerCase()))
          .toList();
      state = AsyncValue.data(filtered);
    }
  }

  Future<void> refreshOrders() async {
    try {
      final response = await _repository.getOrders();
      _allOrders = response.orders;
      _applyFilter();
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  @override
  void dispose() {
    _debounceTimer?.cancel();
    super.dispose();
  }
}

final ordersProvider =
    StateNotifierProvider<OrdersNotifier, AsyncValue<List<OrderModel>>>((ref) {
  return OrdersNotifier(repository: ref.watch(orderRepositoryProvider));
});

final orderDetailProvider =
    FutureProvider.family<OrderModel, int>((ref, orderId) async {
  final repository = ref.watch(orderRepositoryProvider);
  return await repository.getOrderById(orderId);
});
