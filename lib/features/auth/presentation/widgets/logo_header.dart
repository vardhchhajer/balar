import 'package:flutter/material.dart';
import 'package:baalar/core/constants/app_colors.dart';
import 'package:baalar/core/constants/app_strings.dart';
import 'package:baalar/core/constants/app_text_styles.dart';

class LogoHeader extends StatelessWidget {
  const LogoHeader({super.key});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Image.asset(
          'assets/images/logo.png',
          height: 100,
          width: 100,
        ),
        const SizedBox(height: 16),
        Text(
          AppStrings.loginTitle,
          style: AppTextStyles.heading1.copyWith(
            color: AppColors.primary,
          ),
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
