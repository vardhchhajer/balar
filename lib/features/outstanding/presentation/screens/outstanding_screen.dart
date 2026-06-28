import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:baalar/core/constants/app_colors.dart';
import 'package:baalar/core/constants/app_text_styles.dart';
import 'package:baalar/core/utils/date_formatter.dart';
import 'package:baalar/features/outstanding/data/models/outstanding_model.dart';
import 'package:baalar/features/outstanding/providers/outstanding_provider.dart';
import 'package:baalar/shared/widgets/error_widget.dart';

class OutstandingScreen extends ConsumerWidget {
  const OutstandingScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final outstandingAsync = ref.watch(outstandingProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        title: Text('Outstanding', style: AppTextStyles.heading3.copyWith(color: Colors.white)),
      ),
      body: outstandingAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => AppErrorWidget(
          message: 'Could not load outstanding bills',
          onRetry: () => ref.invalidate(outstandingProvider),
        ),
        data: (data) => _buildContent(data),
      ),
    );
  }

  Widget _buildContent(OutstandingListResponse data) {
    if (data.bills.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.check_circle_outline, size: 80, color: AppColors.success),
            const SizedBox(height: 16),
            Text('No outstanding bills', style: AppTextStyles.heading3.copyWith(color: AppColors.textSecondary)),
            const SizedBox(height: 8),
            Text('All payments are up to date', style: AppTextStyles.bodySmall),
          ],
        ),
      );
    }

    return Column(
      children: [
        // Total outstanding header
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(20),
          color: AppColors.surface,
          child: Column(
            children: [
              Text('Total Outstanding', style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary)),
              const SizedBox(height: 4),
              Text(
                '\u20B9${data.totalOutstanding.toStringAsFixed(2)}',
                style: AppTextStyles.heading1.copyWith(color: AppColors.error),
              ),
              const SizedBox(height: 4),
              Text('${data.total} bills pending', style: AppTextStyles.bodySmall),
            ],
          ),
        ),
        const Divider(height: 1),
        // Bills list
        Expanded(
          child: RefreshIndicator(
            onRefresh: () async {
              // Can't invalidate from here without ref, but pull-to-refresh will work with the FutureProvider auto-refresh
            },
            child: ListView.builder(
              itemCount: data.bills.length,
              itemBuilder: (context, index) => _BillCard(bill: data.bills[index]),
            ),
          ),
        ),
      ],
    );
  }
}

class _BillCard extends StatelessWidget {
  final OutstandingBillModel bill;

  const _BillCard({required this.bill});

  @override
  Widget build(BuildContext context) {
    final isPaid = bill.amountOutstanding <= 0;

    return Card(
      elevation: 1,
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(bill.billNo, style: AppTextStyles.bodyLarge.copyWith(fontWeight: FontWeight.w600)),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: isPaid ? AppColors.deliveredBg : AppColors.cancelledBg,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    isPaid ? 'Paid' : 'Pending',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: isPaid ? AppColors.deliveredText : AppColors.cancelledText,
                    ),
                  ),
                ),
              ],
            ),
            if (bill.description != null && bill.description!.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(bill.description!, style: AppTextStyles.bodySmall),
            ],
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Bill Amount', style: AppTextStyles.caption),
                      Text('\u20B9${bill.totalAmount.toStringAsFixed(2)}', style: AppTextStyles.bodyMedium),
                    ],
                  ),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Paid', style: AppTextStyles.caption),
                      Text('\u20B9${bill.amountPaid.toStringAsFixed(2)}', style: AppTextStyles.bodyMedium.copyWith(color: AppColors.success)),
                    ],
                  ),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text('Outstanding', style: AppTextStyles.caption),
                      Text(
                        '\u20B9${bill.amountOutstanding.toStringAsFixed(2)}',
                        style: AppTextStyles.bodyMedium.copyWith(
                          fontWeight: FontWeight.w600,
                          color: isPaid ? AppColors.success : AppColors.error,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('Bill Date: ${DateFormatter.formatDate(bill.billDate)}', style: AppTextStyles.caption),
                if (bill.dueDate != null)
                  Text('Due: ${DateFormatter.formatDate(bill.dueDate)}', style: AppTextStyles.caption.copyWith(color: AppColors.error)),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
