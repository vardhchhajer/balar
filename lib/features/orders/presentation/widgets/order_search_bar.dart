import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:balar/core/constants/app_colors.dart';
import 'package:balar/core/constants/app_strings.dart';
import 'package:balar/features/orders/providers/order_provider.dart';

class OrderSearchBar extends ConsumerStatefulWidget {
  const OrderSearchBar({super.key});

  @override
  ConsumerState<OrderSearchBar> createState() => _OrderSearchBarState();
}

class _OrderSearchBarState extends ConsumerState<OrderSearchBar> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: TextField(
        controller: _controller,
        maxLength: 50,
        decoration: InputDecoration(
          hintText: AppStrings.searchHint,
          prefixIcon: const Icon(Icons.search),
          suffixIcon: _controller.text.isNotEmpty
              ? IconButton(
                  icon: const Icon(Icons.clear),
                  onPressed: () {
                    _controller.clear();
                    ref.read(ordersProvider.notifier).searchOrders('');
                    setState(() {});
                  },
                )
              : null,
          filled: true,
          fillColor: AppColors.surface,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: AppColors.border),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: AppColors.border),
          ),
          counterText: '',
        ),
        onChanged: (value) {
          ref.read(ordersProvider.notifier).searchOrders(value);
          setState(() {});
        },
      ),
    );
  }
}
