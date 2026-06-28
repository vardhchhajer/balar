import 'package:flutter/material.dart';
import 'package:baalar/core/constants/app_colors.dart';
import 'package:baalar/core/constants/app_strings.dart';

enum DisplayStatus { notDispatched, dispatched, delivered, cancelled, unavailable }

class DispatchStatusBadge extends StatelessWidget {
  final String? status;

  const DispatchStatusBadge({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
    final mapped = _mapStatus(status);
    final config = _getConfig(mapped);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: config.backgroundColor,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            config.icon,
            style: TextStyle(fontSize: 10, color: config.textColor),
          ),
          const SizedBox(width: 4),
          Text(
            config.label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: config.textColor,
            ),
          ),
        ],
      ),
    );
  }

  static DisplayStatus _mapStatus(String? rawStatus) {
    if (rawStatus == null || rawStatus.trim().isEmpty) {
      return DisplayStatus.unavailable;
    }
    switch (rawStatus.toLowerCase()) {
      case 'pending':
      case 'processing':
      case 'awaiting dispatch':
        return DisplayStatus.notDispatched;
      case 'dispatched':
        return DisplayStatus.dispatched;
      case 'delivered':
        return DisplayStatus.delivered;
      case 'cancelled':
        return DisplayStatus.cancelled;
      default:
        return DisplayStatus.unavailable;
    }
  }

  static _BadgeConfig _getConfig(DisplayStatus status) {
    switch (status) {
      case DisplayStatus.notDispatched:
        return _BadgeConfig(
          label: AppStrings.statusNotDispatched,
          icon: '○',
          backgroundColor: AppColors.notDispatchedBg,
          textColor: AppColors.notDispatchedText,
        );
      case DisplayStatus.dispatched:
        return _BadgeConfig(
          label: AppStrings.statusDispatched,
          icon: '●',
          backgroundColor: AppColors.dispatchedBg,
          textColor: AppColors.dispatchedText,
        );
      case DisplayStatus.delivered:
        return _BadgeConfig(
          label: AppStrings.statusDelivered,
          icon: '✓',
          backgroundColor: AppColors.deliveredBg,
          textColor: AppColors.deliveredText,
        );
      case DisplayStatus.cancelled:
        return _BadgeConfig(
          label: AppStrings.statusCancelled,
          icon: '✕',
          backgroundColor: AppColors.cancelledBg,
          textColor: AppColors.cancelledText,
        );
      case DisplayStatus.unavailable:
        return _BadgeConfig(
          label: AppStrings.statusUnavailable,
          icon: '?',
          backgroundColor: AppColors.unavailableBg,
          textColor: AppColors.unavailableText,
        );
    }
  }
}

class _BadgeConfig {
  final String label;
  final String icon;
  final Color backgroundColor;
  final Color textColor;

  const _BadgeConfig({
    required this.label,
    required this.icon,
    required this.backgroundColor,
    required this.textColor,
  });
}
