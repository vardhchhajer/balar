import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:balar/core/constants/app_colors.dart';
import 'package:balar/core/constants/app_strings.dart';
import 'package:balar/core/constants/app_text_styles.dart';
import 'package:balar/core/network/api_client.dart';
import 'package:balar/features/auth/providers/auth_provider.dart';
import 'package:balar/features/profile/data/models/profile_model.dart';
import 'package:balar/shared/widgets/error_widget.dart';

final profileProvider = FutureProvider<ProfileModel>((ref) async {
  final apiClient = ref.watch(apiClientProvider);
  final response = await apiClient.get('/profile');
  return ProfileModel.fromJson(response.data);
});

final syncInfoProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final apiClient = ref.watch(apiClientProvider);
  final response = await apiClient.get('/profile/sync-info');
  return response.data as Map<String, dynamic>;
});

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profileAsync = ref.watch(profileProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        title: const Text('Profile'),
      ),
      body: profileAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => AppErrorWidget(
          message: AppStrings.couldNotLoadProfile,
          onRetry: () => ref.invalidate(profileProvider),
        ),
        data: (profile) => _buildContent(context, ref, profile),
      ),
    );
  }

  Widget _buildContent(BuildContext context, WidgetRef ref, ProfileModel profile) {
    final syncAsync = ref.watch(syncInfoProvider);
    final initials = _getInitials(profile.fullName);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          const SizedBox(height: 16),
          CircleAvatar(
            radius: 48,
            backgroundColor: AppColors.primary,
            child: Text(initials, style: AppTextStyles.heading1.copyWith(color: Colors.white)),
          ),
          const SizedBox(height: 16),
          Text(profile.fullName, style: AppTextStyles.heading2),
          const SizedBox(height: 4),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            decoration: BoxDecoration(
              color: _roleColor(profile.role).withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              profile.role.toUpperCase(),
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: _roleColor(profile.role)),
            ),
          ),
          const SizedBox(height: 8),
          Text(profile.username, style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary)),
          if (profile.partyCode != null)
            Text('Party: ${profile.partyCode}', style: AppTextStyles.bodySmall),
          if (profile.agentCode != null)
            Text('Agent: ${profile.agentCode}', style: AppTextStyles.bodySmall),
          const SizedBox(height: 8),
          Text(profile.email ?? 'No email', style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary)),
          const Divider(height: 32),
          // Sync info
          syncAsync.when(
            loading: () => const SizedBox.shrink(),
            error: (_, __) => const SizedBox.shrink(),
            data: (syncInfo) {
              final lastSync = syncInfo['last_sync_time'];
              final syncStatus = syncInfo['status'] ?? 'never';
              return Card(
                child: ListTile(
                  leading: Icon(
                    syncStatus == 'success' ? Icons.cloud_done : Icons.cloud_off,
                    color: syncStatus == 'success' ? AppColors.success : AppColors.textSecondary,
                  ),
                  title: const Text('Last Sync'),
                  subtitle: Text(lastSync != null ? _formatSyncTime(lastSync) : 'Never synced'),
                ),
              );
            },
          ),
          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: () => ref.read(authProvider.notifier).logout(),
              style: OutlinedButton.styleFrom(
                foregroundColor: AppColors.error,
                side: const BorderSide(color: AppColors.error),
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              child: Text(AppStrings.logout, style: AppTextStyles.bodyLarge.copyWith(color: AppColors.error)),
            ),
          ),
        ],
      ),
    );
  }

  Color _roleColor(String role) {
    switch (role) {
      case 'admin': return Colors.purple;
      case 'agent': return Colors.blue;
      default: return AppColors.primary;
    }
  }

  String _formatSyncTime(String isoTime) {
    try {
      final dt = DateTime.parse(isoTime);
      final now = DateTime.now();
      final diff = now.difference(dt);
      if (diff.inMinutes < 1) return 'Just now';
      if (diff.inMinutes < 60) return '${diff.inMinutes} min ago';
      if (diff.inHours < 24) return '${diff.inHours} hours ago';
      return '${diff.inDays} days ago';
    } catch (_) {
      return isoTime;
    }
  }

  String _getInitials(String fullName) {
    if (fullName.isEmpty) return '?';
    final parts = fullName.split(' ');
    if (parts.length >= 2) return '${parts[0][0]}${parts[1][0]}'.toUpperCase();
    return fullName[0].toUpperCase();
  }
}
