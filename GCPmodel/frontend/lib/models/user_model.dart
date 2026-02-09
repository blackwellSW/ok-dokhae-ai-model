class UserProfile {
  final String userId;
  final String email;
  final String username;
  final String userType; // 'student', 'teacher', 'admin'
  final bool isActive;

  UserProfile({
    required this.userId,
    required this.email,
    required this.username,
    required this.userType,
    required this.isActive,
  });

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      userId: json['user_id'] ?? '',
      email: json['email'] ?? '',
      username: json['username'] ?? '',
      userType: json['user_type'] ?? 'student',
      isActive: json['is_active'] ?? true,
    );
  }
}