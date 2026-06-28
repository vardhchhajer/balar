// Basic smoke test for the Baalar app.

import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:baalar/app.dart';

void main() {
  testWidgets('App renders without crashing', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: BaalarApp()));
    // Verify the app builds and shows the login screen
    expect(find.text('Baalar'), findsWidgets);
  });
}
