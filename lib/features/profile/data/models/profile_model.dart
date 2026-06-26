class ProfileModel {
  final int id;
  final String username;
  final String role;
  final String fullName;
  final String? email;
  final String? partyCode;
  final String? agentCode;

  const ProfileModel({
    required this.id,
    required this.username,
    required this.role,
    required this.fullName,
    this.email,
    this.partyCode,
    this.agentCode,
  });

  factory ProfileModel.fromJson(Map<String, dynamic> json) => ProfileModel(
        id: json['id'] as int,
        username: json['username'] as String,
        role: json['role'] as String,
        fullName: json['full_name'] as String,
        email: json['email'] as String?,
        partyCode: json['party_code'] as String?,
        agentCode: json['agent_code'] as String?,
      );
}
