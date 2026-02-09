import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:google_sign_in/google_sign_in.dart';
import '../services/dio_client.dart';
import '../models/user_model.dart';

class AuthRepository {
  final DioClient _client = DioClient();
  final FirebaseAuth _auth = FirebaseAuth.instance;
  final GoogleSignIn _googleSignIn = GoogleSignIn();

  Future<bool> loginWithGoogle({String userType = 'student'}) async {
    try {
      // 1. 구글 로그인 트리거
      final GoogleSignInAccount? googleUser = await _googleSignIn.signIn();
      if (googleUser == null) return false;

      final GoogleSignInAuthentication googleAuth = await googleUser.authentication;

      // 2. Firebase 자격 증명 생성
      final credential = GoogleAuthProvider.credential(
        accessToken: googleAuth.accessToken,
        idToken: googleAuth.idToken,
      );

      // 3. Firebase 로그인
      final UserCredential userCredential = await _auth.signInWithCredential(credential);
      final String? firebaseIdToken = await userCredential.user?.getIdToken();

      if (firebaseIdToken == null) return false;

      // 4. 백엔드로 Firebase 토큰 전송
      final response = await _client.dio.post(
        '/auth/google-login',
        data: {'id_token': firebaseIdToken, 'user_type': userType},
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final token = response.data['access_token'];
        if (token != null) {
          await _client.saveToken(token);
          return true;
        }
      }
      return false;
    } catch (e) {
      print('Login Error: $e');
      return false;
    }
  }

  // getUserProfile 등 나머지 코드는 그대로 두셔도 됩니다.
  // 필요하면 기존 코드 유지
}