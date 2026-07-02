import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:baalar/core/constants/app_colors.dart';
import 'package:baalar/core/constants/app_text_styles.dart';
import 'package:baalar/features/outstanding/data/models/outstanding_model.dart';
import 'package:baalar/features/outstanding/providers/outstanding_provider.dart';
import 'package:baalar/features/auth/providers/auth_provider.dart';
import 'package:baalar/shared/widgets/error_widget.dart';

class OutstandingScreen extends ConsumerWidget {
  const OutstandingScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final outstandingAsync = ref.watch(outstandingProvider);
    final authState = ref.watch(authProvider);
    final isAgent = authState.role == 'agent';
    final isAdmin = authState.role == 'admin';

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
        data: (data) => (isAgent || isAdmin)
            ? _buildPartyWiseContent(data)
            : _buildPartyContent(data),
      ),
    );
  }

  /// Agent/Admin view: grouped by party
  Widget _buildPartyWiseContent(OutstandingListResponse data) {
    if (data.bills.isEmpty) {
      return _buildEmptyState();
    }

    // Group bills by party (strip "(Prior Year Balance)" suffix from OPENING lines)
    final Map<String, List<OutstandingBillModel>> grouped = {};
    for (final bill in data.bills) {
      final name = bill.isOpeningBalance
          ? bill.partyName.replaceAll(' (Prior Year Balance)', '')
          : bill.partyName;
      grouped.putIfAbsent(name, () => []).add(bill);
    }

    // Sort parties by total outstanding (descending)
    final sortedParties = grouped.entries.toList()
      ..sort((a, b) {
        final totalA = a.value.fold<double>(0, (sum, b) => sum + b.amountOutstanding);
        final totalB = b.value.fold<double>(0, (sum, b) => sum + b.amountOutstanding);
        return totalB.compareTo(totalA);
      });

    return Column(
      children: [
        // Total header
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(20),
          color: AppColors.surface,
          child: Column(
            children: [
              Text('Total Outstanding', style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary)),
              const SizedBox(height: 4),
              Text(
                '\u20B9${data.totalOutstanding.toStringAsFixed(0)}',
                style: AppTextStyles.heading1.copyWith(color: AppColors.error),
              ),
              const SizedBox(height: 4),
              Text('${sortedParties.length} parties', style: AppTextStyles.bodySmall),
            ],
          ),
        ),
        const Divider(height: 1),
        // Party-wise list
        Expanded(
          child: ListView.builder(
            itemCount: sortedParties.length,
            itemBuilder: (context, index) {
              final entry = sortedParties[index];
              final partyName = entry.key;
              final bills = entry.value;
              final partyTotal = bills.fold<double>(0, (sum, b) => sum + b.amountOutstanding);

              return _PartyOutstandingCard(
                partyName: partyName,
                bills: bills,
                totalOutstanding: partyTotal,
              );
            },
          ),
        ),
      ],
    );
  }

  /// Party view: flat list of their own bills
  Widget _buildPartyContent(OutstandingListResponse data) {
    if (data.bills.isEmpty) {
      return _buildEmptyState();
    }

    return Column(
      children: [
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(20),
          color: AppColors.surface,
          child: Column(
            children: [
              Text('Total Outstanding', style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary)),
              const SizedBox(height: 4),
              Text(
                '\u20B9${data.totalOutstanding.toStringAsFixed(0)}',
                style: AppTextStyles.heading1.copyWith(color: AppColors.error),
              ),
              const SizedBox(height: 4),
              Text('${data.bills.length} bill${data.bills.length == 1 ? '' : 's'}', style: AppTextStyles.bodySmall),
            ],
          ),
        ),
        const Divider(height: 1),
        Expanded(
          child: ListView.builder(
            itemCount: data.bills.length,
            itemBuilder: (context, index) => _BillCard(bill: data.bills[index]),
          ),
        ),
      ],
    );
  }

  Widget _buildEmptyState() {
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
}

class _PartyOutstandingCard extends StatefulWidget {
  final String partyName;
  final List<OutstandingBillModel> bills;
  final double totalOutstanding;

  const _PartyOutstandingCard({
    required this.partyName,
    required this.bills,
    required this.totalOutstanding,
  });

  @override
  State<_PartyOutstandingCard> createState() => _PartyOutstandingCardState();
}

class _PartyOutstandingCardState extends State<_PartyOutstandingCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 1,
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Column(
        children: [
          InkWell(
            borderRadius: BorderRadius.circular(12),
            onTap: () => setState(() => _expanded = !_expanded),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          widget.partyName,
                          style: AppTextStyles.bodyLarge.copyWith(fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${widget.bills.length} bill${widget.bills.length == 1 ? '' : 's'}',
                          style: AppTextStyles.bodySmall,
                        ),
                      ],
                    ),
                  ),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        '\u20B9${widget.totalOutstanding.toStringAsFixed(0)}',
                        style: AppTextStyles.bodyLarge.copyWith(
                          fontWeight: FontWeight.w700,
                          color: AppColors.error,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(width: 8),
                  Icon(
                    _expanded ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
                    color: AppColors.textSecondary,
                  ),
                ],
              ),
            ),
          ),
          if (_expanded) ...[
            const Divider(height: 1),
            // Summary row
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Total Billed', style: AppTextStyles.caption),
                        Text('\u20B9${widget.bills.fold<double>(0, (s, b) => s + b.totalAmount).toStringAsFixed(0)}', style: AppTextStyles.bodyMedium),
                      ],
                    ),
                  ),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Received', style: AppTextStyles.caption),
                        Text('\u20B9${widget.bills.fold<double>(0, (s, b) => s + b.amountPaid).toStringAsFixed(0)}', style: AppTextStyles.bodyMedium.copyWith(color: AppColors.success)),
                      ],
                    ),
                  ),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text('Outstanding', style: AppTextStyles.caption),
                        Text(
                          '\u20B9${widget.totalOutstanding.toStringAsFixed(0)}',
                          style: AppTextStyles.bodyMedium.copyWith(fontWeight: FontWeight.w600, color: AppColors.error),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            // Individual bills
            const Divider(height: 1),
            ...widget.bills.map((bill) => _BillRow(bill: bill)),
            const SizedBox(height: 8),
          ],
        ],
      ),
    );
  }
}

class _BillCard extends StatelessWidget {
  final OutstandingBillModel bill;

  const _BillCard({required this.bill});

  @override
  Widget build(BuildContext context) {
    final isOpening = bill.isOpeningBalance;

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
                Expanded(
                  child: Text(
                    isOpening ? 'Prior Year Balance' : 'Bill #${bill.billNo}',
                    style: AppTextStyles.bodyLarge.copyWith(fontWeight: FontWeight.w600),
                  ),
                ),
                Text(
                  '\u20B9${bill.amountOutstanding.toStringAsFixed(0)}',
                  style: AppTextStyles.bodyLarge.copyWith(
                    fontWeight: FontWeight.w700,
                    color: AppColors.error,
                  ),
                ),
              ],
            ),
            if (!isOpening && bill.billDate != null) ...[
              const SizedBox(height: 4),
              Text(
                bill.billDate!,
                style: AppTextStyles.bodySmall.copyWith(color: AppColors.textSecondary),
              ),
            ],
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Billed', style: AppTextStyles.caption),
                      Text('\u20B9${bill.totalAmount.toStringAsFixed(0)}', style: AppTextStyles.bodyMedium),
                    ],
                  ),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Received', style: AppTextStyles.caption),
                      Text('\u20B9${bill.amountPaid.toStringAsFixed(0)}', style: AppTextStyles.bodyMedium.copyWith(color: AppColors.success)),
                    ],
                  ),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text('Pending', style: AppTextStyles.caption),
                      Text(
                        '\u20B9${bill.amountOutstanding.toStringAsFixed(0)}',
                        style: AppTextStyles.bodyMedium.copyWith(fontWeight: FontWeight.w600, color: AppColors.error),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// Compact bill row shown inside expanded party cards (agent/admin view)
class _BillRow extends StatelessWidget {
  final OutstandingBillModel bill;

  const _BillRow({required this.bill});

  @override
  Widget build(BuildContext context) {
    final isOpening = bill.isOpeningBalance;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          Expanded(
            flex: 3,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isOpening ? 'Prior Year Balance' : 'Bill #${bill.billNo}',
                  style: AppTextStyles.bodySmall.copyWith(fontWeight: FontWeight.w500),
                ),
                if (!isOpening && bill.billDate != null)
                  Text(
                    bill.billDate!,
                    style: AppTextStyles.caption.copyWith(color: AppColors.textSecondary),
                  ),
              ],
            ),
          ),
          Expanded(
            flex: 2,
            child: Text(
              '\u20B9${bill.totalAmount.toStringAsFixed(0)}',
              style: AppTextStyles.caption,
              textAlign: TextAlign.right,
            ),
          ),
          Expanded(
            flex: 2,
            child: Text(
              '\u20B9${bill.amountPaid.toStringAsFixed(0)}',
              style: AppTextStyles.caption.copyWith(color: AppColors.success),
              textAlign: TextAlign.right,
            ),
          ),
          Expanded(
            flex: 2,
            child: Text(
              '\u20B9${bill.amountOutstanding.toStringAsFixed(0)}',
              style: AppTextStyles.caption.copyWith(fontWeight: FontWeight.w600, color: AppColors.error),
              textAlign: TextAlign.right,
            ),
          ),
        ],
      ),
    );
  }
}
