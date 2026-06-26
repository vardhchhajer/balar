import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:balar/features/outstanding/data/models/outstanding_model.dart';
import 'package:balar/features/outstanding/data/repositories/outstanding_repository.dart';

final outstandingProvider =
    FutureProvider<OutstandingListResponse>((ref) async {
  final repository = ref.watch(outstandingRepositoryProvider);
  return await repository.getOutstandingBills();
});
