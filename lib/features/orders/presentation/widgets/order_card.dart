import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:baalar/core/constants/app_colors.dart';
import 'package:baalar/core/constants/app_strings.dart';
import 'package:baalar/core/constants/app_text_styles.dart';
import 'package:baalar/core/utils/date_formatter.dart';
import 'package:baalar/features/orders/data/models/order_model.dart';
import 'package:baalar/features/orders/presentation/widgets/dispatch_status_badge.dart';

class OrderCard extends StatelessWidget {
  final OrderModel order;

  const OrderCard({super.key, required this.order});

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 1,
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => context.push('/orders/${order.id}'),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    order.orderNo,
                    style: AppTextStyles.bodyLarge.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  DispatchStatusBadge(status: order.dispatchStatus),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                '${AppStrings.orderDate}: ${DateFormatter.formatDate(order.orderDate)}',
                style: AppTextStyles.bodySmall,
              ),
              const SizedBox(height: 4),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    '${AppStrings.dispatchDate}: ${DateFormatter.formatDate(order.dispatchDate)}',
                    style: AppTextStyles.bodySmall,
                  ),
                  Row(
                    children: [
                      Text(
                        '\u20B9${order.totalAmount.toStringAsFixed(0)}',
                        style: AppTextStyles.bodyMedium.copyWith(
                          fontWeight: FontWeight.w600,
                          color: AppColors.primary,
                        ),
                      ),
                      const SizedBox(width: 4),
                      const Icon(
                        Icons.chevron_right,
                        color: AppColors.textSecondary,
                        size: 20,
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
