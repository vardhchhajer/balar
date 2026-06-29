class AppStrings {
  AppStrings._();

  static const String appName = 'Baalar';
  static const String baseUrl = 'http://35.200.191.241:8080';

  // Login
  static const String loginTitle = 'Baalar';
  static const String loginSubtitle = 'Your business, simplified.';
  static const String usernameHint = 'Username';
  static const String passwordHint = 'Password';
  static const String loginButton = 'Login';
  static const String usernameRequired = 'Username is required';
  static const String passwordRequired = 'Password is required';
  static const String passwordMinLength = 'Password must be at least 6 characters';

  // Orders
  static const String ordersTitle = 'Baalar';
  static const String searchHint = 'Search orders';
  static const String noOrdersFound = 'No orders yet';
  static const String pullToRefresh = 'Pull down to refresh';
  static const String orderDate = 'Order Date';
  static const String dispatchDate = 'Dispatch Date';

  // Order Detail
  static const String orderInformation = 'Order Information';
  static const String dispatchDetails = 'Dispatch Details';
  static const String remarks = 'Remarks';
  static const String dispatched = 'DISPATCHED';
  static const String notYetDispatched = 'NOT YET DISPATCHED';
  static const String orderBeingProcessed = 'Your order is being processed';
  static const String orderNumber = 'Order Number';
  static const String status = 'Status';
  static const String dispatchStatus = 'Dispatch Status';
  static const String invoiceNo = 'Invoice No.';
  static const String trackingNo = 'Tracking No.';

  // Status Display
  static const String statusNotDispatched = 'Not Dispatched';
  static const String statusDispatched = 'Dispatched';
  static const String statusDelivered = 'Delivered';
  static const String statusCancelled = 'Cancelled';
  static const String statusPartiallyDispatched = 'Partially Dispatched';
  static const String statusStopped = 'Stopped';
  static const String statusUnavailable = 'Status Unavailable';

  // Profile
  static const String profileTitle = 'Profile';
  static const String logout = 'Logout';
  static const String logoutConfirmTitle = 'Confirm Logout';
  static const String logoutConfirmMessage = 'Are you sure you want to log out?';
  static const String cancel = 'Cancel';
  static const String noEmail = 'No email on file';

  // Errors
  static const String networkError = 'Unable to connect. Please check your internet connection.';
  static const String genericError = 'Something went wrong. Please try again.';
  static const String retry = 'Retry';
  static const String couldNotLoadOrders = 'Could not load orders';
  static const String couldNotLoadDetails = 'Could not load order details';
  static const String couldNotLoadProfile = 'Could not load profile information';

  // Misc
  static const String emDash = '—';
}
