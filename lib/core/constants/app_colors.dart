import 'package:flutter/material.dart';

class AppColors {
  AppColors._();

  // Primary - Dark Green from logo
  static const Color primary = Color(0xFF104C24);
  static const Color primaryDark = Color(0xFF0C411E);
  static const Color primaryLight = Color(0xFF1B6B35);

  // Accent - Gold from logo
  static const Color accent = Color(0xFFC8A254);
  static const Color accentLight = Color(0xFFD4B76E);
  static const Color accentDark = Color(0xFFA8863E);

  // Background & Surface
  static const Color background = Color(0xFFF7F6F3);
  static const Color surface = Color(0xFFFFFFFF);

  // Text
  static const Color textPrimary = Color(0xFF1A1A2E);
  static const Color textSecondary = Color(0xFF6B7280);

  // Border
  static const Color border = Color(0xFFE5E7EB);

  // Status
  static const Color error = Color(0xFFDC2626);
  static const Color success = Color(0xFF16A34A);
  static const Color warning = Color(0xFFC8A254);

  // Dispatch Status Badge Colors
  static const Color notDispatchedBg = Color(0xFFFFF8E8);
  static const Color notDispatchedText = Color(0xFFA8863E);

  static const Color dispatchedBg = Color(0xFFE8F5EC);
  static const Color dispatchedText = Color(0xFF104C24);

  static const Color deliveredBg = Color(0xFFD4EDDA);
  static const Color deliveredText = Color(0xFF155724);

  static const Color cancelledBg = Color(0xFFF8D7DA);
  static const Color cancelledText = Color(0xFF721C24);

  static const Color unavailableBg = Color(0xFFE2E3E5);
  static const Color unavailableText = Color(0xFF383D41);
}
