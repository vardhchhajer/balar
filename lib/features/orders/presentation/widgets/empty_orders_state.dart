import 'package:flutter/material.dart';
import 'package:baalar/core/constants/app_colors.dart';
import 'package:baalar/core/constants/app_strings.dart';
import 'package:baalar/core/constants/app_text_styles.dart';

class EmptyOrdersState extends StatelessWidget {
  const EmptyOrdersState({super.key});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.inbox_outlined,
            size: 80,
            color: AppColors.textSecondary,
          ),
          const SizedBox(height: 16),
          Text(
            AppStrings.noOrdersFound,
            style: AppTextStyles.heading3.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            AppStrings.pullToRefresh,
            style: AppTextStyles.bodySmall,
          ),
        ],
      ),
    );
  }
}
