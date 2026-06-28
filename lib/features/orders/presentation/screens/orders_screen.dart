import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shimmer/shimmer.dart';
import 'package:baalar/core/constants/app_colors.dart';
import 'package:baalar/core/constants/app_strings.dart';
import 'package:baalar/core/constants/app_text_styles.dart';
import 'package:baalar/features/auth/providers/auth_provider.dart';
import 'package:baalar/features/orders/providers/order_provider.dart';
import 'package:baalar/features/orders/presentation/widgets/order_card.dart';
import 'package:baalar/features/orders/presentation/widgets/order_search_bar.dart';
import 'package:baalar/features/orders/presentation/widgets/empty_orders_state.dart';
import 'package:baalar/shared/widgets/error_widget.dart';

class OrdersScreen extends ConsumerStatefulWidget {
  const OrdersScreen({super.key});

  @override
  ConsumerState<OrdersScreen> createState() => _OrdersScreenState();
}

class _OrdersScreenState extends ConsumerState<OrdersScreen> {
  bool _hasLoaded = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      if (!_hasLoaded) {
        _hasLoaded = true;
        ref.read(ordersProvider.notifier).fetchOrders();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final ordersState = ref.watch(ordersProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Text(AppStrings.ordersTitle, style: AppTextStyles.heading3.copyWith(color: Colors.white)),
        backgroundColor: AppColors.primary,
        actions: [
          PopupMenuButton<String>(
            icon: const Icon(Icons.person_outline, color: Colors.white),
            onSelected: (value) {
              if (!mounted) return;
              if (value == 'profile') {
                context.push('/profile');
              } else if (value == 'outstanding') {
                context.push('/outstanding');
              } else if (value == 'logout') {
                ref.read(authProvider.notifier).logout();
              }
            },
            itemBuilder: (context) => [
              const PopupMenuItem(
                value: 'outstanding',
                child: Row(
                  children: [
                    Icon(Icons.account_balance_wallet_outlined, size: 20),
                    SizedBox(width: 8),
                    Text('Outstanding'),
                  ],
                ),
              ),
              const PopupMenuItem(
                value: 'profile',
                child: Row(
                  children: [
                    Icon(Icons.person_outline, size: 20),
                    SizedBox(width: 8),
                    Text('Profile'),
                  ],
                ),
              ),
              const PopupMenuItem(
                value: 'logout',
                child: Row(
                  children: [
                    Icon(Icons.logout, size: 20, color: Colors.red),
                    SizedBox(width: 8),
                    Text('Logout', style: TextStyle(color: Colors.red)),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
      body: Column(
        children: [
          const OrderSearchBar(),
          Expanded(
            child: ordersState.when(
              loading: () => _buildShimmerList(),
              error: (error, _) => AppErrorWidget(
                message: AppStrings.couldNotLoadOrders,
                onRetry: () {
                  if (mounted) {
                    ref.read(ordersProvider.notifier).fetchOrders();
                  }
                },
              ),
              data: (orders) {
                if (orders.isEmpty) {
                  return const EmptyOrdersState();
                }
                return RefreshIndicator(
                  onRefresh: () => ref.read(ordersProvider.notifier).refreshOrders(),
                  child: ListView.builder(
                    itemCount: orders.length,
                    itemBuilder: (context, index) => OrderCard(order: orders[index]),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildShimmerList() {
    return Shimmer.fromColors(
      baseColor: Colors.grey[300]!,
      highlightColor: Colors.grey[100]!,
      child: ListView.builder(
        itemCount: 6,
        itemBuilder: (_, __) => Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
          child: Container(
            height: 100,
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
            ),
          ),
        ),
      ),
    );
  }
}
