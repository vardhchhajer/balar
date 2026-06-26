import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:balar/features/auth/presentation/screens/login_screen.dart';
import 'package:balar/features/auth/providers/auth_provider.dart';
import 'package:balar/features/home/presentation/screens/home_shell.dart';
import 'package:balar/features/orders/presentation/screens/order_detail_screen.dart';
import 'package:balar/features/profile/presentation/screens/profile_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authProvider);

  return GoRouter(
    initialLocation: '/login',
    redirect: (context, state) {
      final isAuthenticated = authState.status == AuthStatus.authenticated;
      final isLoggingIn = state.matchedLocation == '/login';

      if (!isAuthenticated && !isLoggingIn) {
        return '/login';
      }

      if (isAuthenticated && isLoggingIn) {
        return '/orders';
      }

      return null;
    },
    routes: [
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/orders',
        builder: (context, state) => const HomeShell(),
      ),
      GoRoute(
        path: '/orders/:id',
        builder: (context, state) {
          final id = int.parse(state.pathParameters['id']!);
          return OrderDetailScreen(orderId: id);
        },
      ),
      GoRoute(
        path: '/profile',
        builder: (context, state) => const ProfileScreen(),
      ),
    ],
  );
});
