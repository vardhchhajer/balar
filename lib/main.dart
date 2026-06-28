import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:balar/app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Show detailed errors instead of just "null check operator"
  ErrorWidget.builder = (FlutterErrorDetails details) {
    return Material(
      child: Container(
        color: Colors.white,
        padding: const EdgeInsets.all(16),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('ERROR', style: TextStyle(color: Colors.red, fontSize: 20, fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              Text(details.exception.toString(), style: const TextStyle(fontSize: 14)),
              const SizedBox(height: 16),
              Text(details.stack?.toString() ?? 'No stack trace', style: const TextStyle(fontSize: 10, color: Colors.grey)),
            ],
          ),
        ),
      ),
    );
  };
  
  runApp(const ProviderScope(child: OrderTrackerApp()));
}
