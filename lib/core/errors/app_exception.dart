class AppException implements Exception {
  final String message;
  final int? statusCode;

  const AppException({required this.message, this.statusCode});

  @override
  String toString() => message;
}

class UnauthorizedException extends AppException {
  const UnauthorizedException({String message = 'Authentication required.'})
      : super(message: message, statusCode: 401);
}

class ForbiddenException extends AppException {
  const ForbiddenException({String message = 'Access denied.'})
      : super(message: message, statusCode: 403);
}

class NotFoundException extends AppException {
  const NotFoundException({String message = 'Resource not found.'})
      : super(message: message, statusCode: 404);
}

class ServerException extends AppException {
  const ServerException({String message = 'An unexpected error occurred.'})
      : super(message: message, statusCode: 500);
}

class NetworkException extends AppException {
  const NetworkException(
      {String message =
          'Unable to connect. Please check your internet connection.'})
      : super(message: message, statusCode: null);
}
