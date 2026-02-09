class ApiConfig {
  /// true면 Mock(데모), false면 Real(실서버)
  static const bool demoMode =
      bool.fromEnvironment('DEMO_MODE', defaultValue: false);

  /// 실서버 Base URL (demoMode=false일 때 사용)
  /// 마지막 슬래시 없이 넣는 걸 권장합니다.
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue:
        'https://ok-dokhae-backend-84537953160.us-central1.run.app',
  );

  /// 네트워크 타임아웃(초)
  static const int connectTimeoutSec =
      int.fromEnvironment('CONNECT_TIMEOUT_SEC', defaultValue: 10);
  static const int receiveTimeoutSec =
      int.fromEnvironment('RECEIVE_TIMEOUT_SEC', defaultValue: 10);
}
