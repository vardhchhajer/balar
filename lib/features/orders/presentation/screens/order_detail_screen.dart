import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:baalar/core/constants/app_colors.dart';
import 'package:baalar/core/constants/app_strings.dart';
import 'package:baalar/core/constants/app_text_styles.dart';
import 'package:baalar/core/utils/date_formatter.dart';
import 'package:baalar/features/orders/data/models/order_model.dart';
import 'package:baalar/features/orders/presentation/widgets/dispatch_status_badge.dart';
import 'package:baalar/features/orders/providers/order_provider.dart';
import 'package:baalar/shared/widgets/error_widget.dart';

class OrderDetailScreen extends ConsumerWidget {
  final int orderId;

  const OrderDetailScreen({super.key, required this.orderId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final orderAsync = ref.watch(orderDetailProvider(orderId));

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        title: orderAsync.whenOrNull(
          data: (order) => Text(order.orderNo),
        ),
      ),
      body: orderAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => AppErrorWidget(
          message: AppStrings.couldNotLoadDetails,
          onRetry: () => ref.invalidate(orderDetailProvider(orderId)),
        ),
        data: (order) => _buildContent(context, order),
      ),
    );
  }

  Widget _buildContent(BuildContext context, OrderModel order) {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildHeroBanner(order),
          const SizedBox(height: 16),
          _buildOrderInfoSection(order),
          const SizedBox(height: 12),
          _buildDispatchDetailsSection(context, order),
          if (order.items.isNotEmpty) ...[
            const SizedBox(height: 12),
            _buildOrderItemsSection(order),
          ],
          if (order.remarks != null && order.remarks!.trim().isNotEmpty) ...[
            const SizedBox(height: 12),
            _buildRemarksSection(order),
          ],
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _buildHeroBanner(OrderModel order) {
    final status = order.dispatchStatus.toLowerCase();
    final isDispatched = status == 'dispatched' || status == 'delivered';
    final isPending = status == 'pending' ||
        status == 'processing' ||
        status == 'awaiting dispatch';

    Color bgColor;
    IconData icon;
    String title;
    String subtitle;

    if (isDispatched) {
      bgColor = AppColors.deliveredBg;
      icon = Icons.check_circle;
      title = AppStrings.dispatched;
      subtitle =
          '${AppStrings.dispatchDate}: ${DateFormatter.formatDateLong(order.dispatchDate)}';
    } else if (isPending) {
      bgColor = AppColors.notDispatchedBg;
      icon = Icons.access_time;
      title = AppStrings.notYetDispatched;
      subtitle = AppStrings.orderBeingProcessed;
    } else {
      bgColor = AppColors.unavailableBg;
      icon = Icons.info_outline;
      title = order.dispatchStatus;
      subtitle = '';
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      color: bgColor,
      child: Row(
        children: [
          Icon(icon, size: 40, color: AppColors.textPrimary),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: AppTextStyles.heading3),
                if (subtitle.isNotEmpty)
                  Text(subtitle, style: AppTextStyles.bodyMedium),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOrderInfoSection(OrderModel order) {
    return _buildSection(
      title: AppStrings.orderInformation,
      children: [
        _InfoRow(
          label: AppStrings.orderNumber,
          value: order.orderNo,
          isBold: true,
        ),
        _InfoRow(
          label: AppStrings.orderDate,
          value: DateFormatter.formatDateLong(order.orderDate),
        ),
        _InfoRow(
          label: AppStrings.status,
          child: DispatchStatusBadge(status: order.dispatchStatus),
        ),
      ],
    );
  }

  Widget _buildDispatchDetailsSection(BuildContext context, OrderModel order) {
    return _buildSection(
      title: AppStrings.dispatchDetails,
      children: [
        _InfoRow(
          label: AppStrings.dispatchStatus,
          value: order.dispatchStatus,
        ),
        _InfoRow(
          label: AppStrings.dispatchDate,
          value: DateFormatter.formatDateLong(order.dispatchDate),
        ),
        _InfoRow(
          label: AppStrings.invoiceNo,
          value: order.invoiceNo ?? AppStrings.emDash,
        ),
        _InfoRow(
          label: AppStrings.trackingNo,
          value: order.trackingNo ?? AppStrings.emDash,
          trailing: order.trackingNo != null
              ? IconButton(
                  icon: const Icon(Icons.copy, size: 18),
                  onPressed: () {
                    Clipboard.setData(ClipboardData(text: order.trackingNo!));
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Tracking number copied'),
                        duration: Duration(seconds: 2),
                      ),
                    );
                  },
                )
              : null,
        ),
      ],
    );
  }

  Widget _buildOrderItemsSection(OrderModel order) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Card(
        elevation: 1,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Order Items', style: AppTextStyles.heading3),
              const SizedBox(height: 12),
              ...order.items.map((item) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      flex: 3,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(item.productName, style: AppTextStyles.bodyMedium.copyWith(fontWeight: FontWeight.w500)),
                          Text('${item.quantity} x \u20B9${item.unitPrice.toStringAsFixed(2)}', style: AppTextStyles.bodySmall),
                        ],
                      ),
                    ),
                    Text('\u20B9${item.amount.toStringAsFixed(2)}', style: AppTextStyles.bodyMedium.copyWith(fontWeight: FontWeight.w600)),
                  ],
                ),
              )),
              const Divider(),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Total Amount', style: AppTextStyles.bodyLarge.copyWith(fontWeight: FontWeight.w600)),
                  Text('\u20B9${order.totalAmount.toStringAsFixed(2)}', style: AppTextStyles.bodyLarge.copyWith(fontWeight: FontWeight.w700, color: AppColors.primary)),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildRemarksSection(OrderModel order) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Card(
        elevation: 1,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(AppStrings.remarks, style: AppTextStyles.heading3),
              const SizedBox(height: 8),
              Text(order.remarks!, style: AppTextStyles.bodyMedium),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSection({
    required String title,
    required List<Widget> children,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Card(
        elevation: 1,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: AppTextStyles.heading3),
              const SizedBox(height: 12),
              ...children,
            ],
          ),
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String? value;
  final bool isBold;
  final Widget? child;
  final Widget? trailing;

  const _InfoRow({
    required this.label,
    this.value,
    this.isBold = false,
    this.child,
    this.trailing,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          SizedBox(
            width: MediaQuery.of(context).size.width * 0.3,
            child: Text(
              label,
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ),
          Expanded(
            child: child ??
                Text(
                  value ?? AppStrings.emDash,
                  style: AppTextStyles.bodyMedium.copyWith(
                    fontWeight: isBold ? FontWeight.w600 : FontWeight.w400,
                  ),
                ),
          ),
          if (trailing != null) trailing!,
        ],
      ),
    );
  }
}
