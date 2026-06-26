import 'package:flutter/material.dart';
import 'package:balar/core/constants/app_colors.dart';
import 'package:balar/core/constants/app_strings.dart';
import 'package:balar/core/constants/app_text_styles.dart';

class LogoHeader extends StatelessWidget {
  const LogoHeader({super.key});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        const Icon(
          Icons.inventory_2_outlined,
          size: 80,
          color: AppColors.primary,
        ),
        const SizedBox(height: 16),
        Text(
          AppStrings.loginTitle,
          style: AppTextStyles.heading1,
        ),
        const SizedBox(height: 8),
        Text(
          AppStrings.loginSubtitle,
          style: AppTextStyles.bodyMedium.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }
}
