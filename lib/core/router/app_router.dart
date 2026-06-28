import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:baalar/features/auth/presentation/screens/login_screen.dart';
import 'package:baalar/features/auth/providers/auth_provider.dart';
import 'package:baalar/features/home/presentation/screens/home_shell.dart';
import 'package:baalar/features/orders/presentation/screens/order_detail_screen.dart';
import 'package:baalar/features/outstanding/presentation/screens/outstanding_screen.dart';
import 'package:baalar/features/profile/presentation/screens/profile_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authProvider);

  return GoRouter(
    initialLocation: '/login',
    redirect: (context, state) {
      // Don't redirect while still checking auth status
      if (authState.status == AuthStatus.initial) {
        return null;
      }

      final isAuthenticated = authState.status == AuthStatus.authenticated;
      final location = state.matchedLocation;
      final isLoggingIn = location == '/login';

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
          final idStr = state.pathParameters['id'] ?? '0';
          final id = int.tryParse(idStr) ?? 0;
          return OrderDetailScreen(orderId: id);
        },
      ),
      GoRoute(
        path: '/profile',
        builder: (context, state) => const ProfileScreen(),
      ),
      GoRoute(
        path: '/outstanding',
        builder: (context, state) => const OutstandingScreen(),
      ),
    ],
  );
});
