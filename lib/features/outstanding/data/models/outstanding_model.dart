class OutstandingBillModel {
  final int id;
  final String billNo;
  final String billDate;
  final double totalAmount;
  final double amountPaid;
  final double amountOutstanding;
  final String? dueDate;
  final String? description;

  const OutstandingBillModel({
    required this.id,
    required this.billNo,
    required this.billDate,
    required this.totalAmount,
    required this.amountPaid,
    required this.amountOutstanding,
    this.dueDate,
    this.description,
  });

  factory OutstandingBillModel.fromJson(Map<String, dynamic> json) =>
      OutstandingBillModel(
        id: json['id'] as int,
        billNo: json['bill_no'] as String,
        billDate: json['bill_date'] as String,
        totalAmount: (json['total_amount'] as num).toDouble(),
        amountPaid: (json['amount_paid'] as num).toDouble(),
        amountOutstanding: (json['amount_outstanding'] as num).toDouble(),
        dueDate: json['due_date'] as String?,
        description: json['description'] as String?,
      );
}

class OutstandingListResponse {
  final List<OutstandingBillModel> bills;
  final double totalOutstanding;
  final int total;

  const OutstandingListResponse({
    required this.bills,
    required this.totalOutstanding,
    required this.total,
  });

  factory OutstandingListResponse.fromJson(Map<String, dynamic> json) {
    final billsList = (json['bills'] as List)
        .map((e) => OutstandingBillModel.fromJson(e as Map<String, dynamic>))
        .toList();
    return OutstandingListResponse(
      bills: billsList,
      totalOutstanding: (json['total_outstanding'] as num).toDouble(),
      total: json['total'] as int,
    );
  }
}
