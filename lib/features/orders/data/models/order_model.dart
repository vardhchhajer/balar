class OrderItemModel {
  final int id;
  final String productName;
  final int quantity;
  final double unitPrice;
  final double amount;

  const OrderItemModel({
    required this.id,
    required this.productName,
    required this.quantity,
    required this.unitPrice,
    required this.amount,
  });

  factory OrderItemModel.fromJson(Map<String, dynamic> json) => OrderItemModel(
        id: json['id'] as int,
        productName: json['product_name'] as String,
        quantity: json['quantity'] as int,
        unitPrice: (json['unit_price'] as num).toDouble(),
        amount: (json['amount'] as num).toDouble(),
      );
}

class OrderModel {
  final int id;
  final String orderNo;
  final String orderDate;
  final String dispatchStatus;
  final String? dispatchDate;
  final String? invoiceNo;
  final String? trackingNo;
  final double totalAmount;
  final String? remarks;
  final List<OrderItemModel> items;

  const OrderModel({
    required this.id,
    required this.orderNo,
    required this.orderDate,
    required this.dispatchStatus,
    this.dispatchDate,
    this.invoiceNo,
    this.trackingNo,
    this.totalAmount = 0.0,
    this.remarks,
    this.items = const [],
  });

  factory OrderModel.fromJson(Map<String, dynamic> json) => OrderModel(
        id: json['id'] as int,
        orderNo: json['order_no'] as String,
        orderDate: json['order_date'] as String,
        dispatchStatus: json['dispatch_status'] as String,
        dispatchDate: json['dispatch_date'] as String?,
        invoiceNo: json['invoice_no'] as String?,
        trackingNo: json['tracking_no'] as String?,
        totalAmount: (json['total_amount'] as num?)?.toDouble() ?? 0.0,
        remarks: json['remarks'] as String?,
        items: (json['items'] as List?)
                ?.map((e) => OrderItemModel.fromJson(e as Map<String, dynamic>))
                .toList() ??
            [],
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'order_no': orderNo,
        'order_date': orderDate,
        'dispatch_status': dispatchStatus,
        'dispatch_date': dispatchDate,
        'invoice_no': invoiceNo,
        'tracking_no': trackingNo,
        'total_amount': totalAmount,
        'remarks': remarks,
      };
}

class OrderListResponse {
  final List<OrderModel> orders;
  final int total;

  const OrderListResponse({required this.orders, required this.total});

  factory OrderListResponse.fromJson(Map<String, dynamic> json) {
    final ordersList = (json['orders'] as List)
        .map((e) => OrderModel.fromJson(e as Map<String, dynamic>))
        .toList();
    return OrderListResponse(
      orders: ordersList,
      total: json['total'] as int,
    );
  }
}
