import 'package:intl/intl.dart';

class DateFormatter {
  DateFormatter._();

  /// Formats date string to "dd MMM yyyy" (e.g., "15 Oct 2024")
  /// Returns "\u2014" for null or empty input
  static String formatDate(String? dateStr) {
    if (dateStr == null || dateStr.isEmpty) return '\u2014';
    try {
      final date = DateTime.parse(dateStr);
      return DateFormat('dd MMM yyyy').format(date);
    } catch (_) {
      return '\u2014';
    }
  }

  /// Formats date string to "dd MMMM yyyy" (e.g., "15 October 2024")
  /// Returns "\u2014" for null or empty input
  static String formatDateLong(String? dateStr) {
    if (dateStr == null || dateStr.isEmpty) return '\u2014';
    try {
      final date = DateTime.parse(dateStr);
      return DateFormat('dd MMMM yyyy').format(date);
    } catch (_) {
      return '\u2014';
    }
  }
}
