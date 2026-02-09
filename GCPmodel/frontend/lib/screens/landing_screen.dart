import 'package:flutter/gestures.dart'; // 웹에서 마우스 드래그 지원을 위해 필요
import 'package:flutter/material.dart';
import '../repositories/auth_repository.dart';
import 'home_screen.dart';
import 'session_screen.dart';

class LandingScreen extends StatefulWidget {
  const LandingScreen({super.key});

  @override
  State<LandingScreen> createState() => _LandingScreenState();
}

class _LandingScreenState extends State<LandingScreen> {
  void _startDemoSession() {
    // 로그인 없이 바로 데모 세션으로 진입 (MockApiService 기준)
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(
        builder: (context) => const SessionScreen(id: 'gwandong', title: '관동별곡'),
      ),
    );
  }

  final AuthRepository _authRepo = AuthRepository();
  bool _isLoading = false;

  Future<void> _handleGoogleLogin() async {
    if (_isLoading) return;
    setState(() => _isLoading = true);

    try {
      final bool success = await _authRepo.loginWithGoogle();
      if (!mounted) return;

      if (success) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (context) => const HomeScreen()),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("구글 로그인 실패 (백엔드 연결 확인 필요)")),
        );
      }
    } catch (e) {
      print(e);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  final PageController _pageController = PageController();
  int _currentPage = 0;

  // 온보딩 슬라이드 데이터 (3장)
  final List<Map<String, String>> _onboardingData = [
    {
      "title": "감으로 찍는 독해는\n이제 그만",
      "desc": "고어와 한자에 막혀 내용을 짐작만 하셨나요?\nAI가 정확한 해석의 길을 열어드립니다.",
      "image": "assets/images/onboarding_1.png", // 이미지 경로 (나중에 실제 파일로 교체)
      "icon": "book" 
    },
    {
      "title": "밑줄 긋고,\n근거를 찾으세요",
      "desc": "정답만 외우는 건 의미가 없습니다.\n스스로 근거를 찾아 논리적으로 설명하는 힘을 기르세요.",
      "image": "assets/images/onboarding_2.png",
      "icon": "edit"
    },
    {
      "title": "당신의 든든한\n고전 파트너",
      "desc": "심청전부터 관동별곡까지.\n가장 확실한 AI 튜터와 함께 시작해볼까요?",
      "image": "assets/images/onboarding_3.png",
      "icon": "start"
    },
  ];

  @override
  Widget build(BuildContext context) {
    // 고전문학 테마 색상 (Modern Hanok - Deep Brown)
    const primaryColor = Color(0xFF02B152); 
    const textColor = Color(0xFF3E2723);

    return Scaffold(
      backgroundColor: Colors.white,
      body: Center(
        // 웹에서도 모바일 앱처럼 보이게 가로 폭 제한 (최대 480px)
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480),
          child: Column(
            children: [
              // 1. 상단 건너뛰기(Skip) 버튼 (마지막 페이지가 아닐 때만 표시)
              Container(
                alignment: Alignment.centerRight,
                padding: const EdgeInsets.only(top: 40, right: 20),
                height: 80,
                child: _currentPage < 2
                    ? TextButton(
                        onPressed: () {
                          _pageController.animateToPage(
                            2,
                            duration: const Duration(milliseconds: 300),
                            curve: Curves.easeIn,
                          );
                        },
                        child: const Text(
                          "Skip",
                          style: TextStyle(
                            color: Colors.grey,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      )
                    : null,
              ),

              // 2. 메인 슬라이더 (PageView + 화살표)
              Expanded(
                child: Stack(
                  children: [
                    // 슬라이드 화면
                    PageView.builder(
                      controller: _pageController,
                      // 웹에서 마우스 드래그로 넘기기 허용
                      scrollBehavior: const MaterialScrollBehavior().copyWith(
                        dragDevices: {PointerDeviceKind.mouse, PointerDeviceKind.touch},
                      ),
                      onPageChanged: (value) {
                        setState(() => _currentPage = value);
                      },
                      itemCount: _onboardingData.length,
                      itemBuilder: (context, index) {
                        return Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 40), // 화살표 공간 확보
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              // 아이콘/이미지 영역
                              Container(
                                height: 200,
                                width: 200,
                                decoration: BoxDecoration(
                                  color: const Color(0xFFF5F5F5), // 연한 회색 배경
                                  shape: BoxShape.circle,
                                  border: Border.all(color: const Color(0xFFD7CCC8), width: 1),
                                ),
                                child: Icon(
                                  index == 0 ? Icons.menu_book_rounded :
                                  index == 1 ? Icons.plagiarism_rounded :
                                  Icons.history_edu_rounded,
                                  size: 80,
                                  color: primaryColor.withOpacity(0.8),
                                ),
                              ),
                              const SizedBox(height: 48),
                              
                              // 제목
                              Text(
                                _onboardingData[index]['title']!,
                                textAlign: TextAlign.center,
                                style: const TextStyle(
                                  fontFamily: 'Pretendard',
                                  fontSize: 28,
                                  fontWeight: FontWeight.w900, // 아주 굵게
                                  color: textColor,
                                  height: 1.3,
                                ),
                              ),
                              const SizedBox(height: 16),
                              
                              // 설명
                              Text(
                                _onboardingData[index]['desc']!,
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  fontFamily: 'Pretendard',
                                  fontSize: 16,
                                  color: Colors.grey[600],
                                  height: 1.6,
                                ),
                              ),
                            ],
                          ),
                        );
                      },
                    ),

                    // 왼쪽 화살표 (첫 페이지 아닐 때만 보임)
                    if (_currentPage > 0)
                      Positioned(
                        left: 0,
                        top: 0,
                        bottom: 0,
                        child: Center(
                          child: IconButton(
                            icon: const Icon(Icons.chevron_left, size: 40, color: Colors.grey),
                            onPressed: () {
                              _pageController.previousPage(
                                duration: const Duration(milliseconds: 300),
                                curve: Curves.easeInOut,
                              );
                            },
                          ),
                        ),
                      ),

                    // 오른쪽 화살표 (마지막 페이지 아닐 때만 보임)
                    if (_currentPage < _onboardingData.length - 1)
                      Positioned(
                        right: 0,
                        top: 0,
                        bottom: 0,
                        child: Center(
                          child: IconButton(
                            icon: const Icon(Icons.chevron_right, size: 40, color: Colors.grey),
                            onPressed: () {
                              _pageController.nextPage(
                                duration: const Duration(milliseconds: 300),
                                curve: Curves.easeInOut,
                              );
                            },
                          ),
                        ),
                      ),
                  ],
                ),
              ),

              // 3. 하단 영역 (인디케이터 & 로그인 버튼)
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 0, 24, 48),
                child: Column(
                  children: [
                    // 페이지 인디케이터 (점 3개)
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: List.generate(
                        _onboardingData.length,
                        (index) => GestureDetector(
                          onTap: () => _pageController.animateToPage(
                            index, 
                            duration: const Duration(milliseconds: 300), 
                            curve: Curves.easeInOut
                          ),
                          child: AnimatedContainer(
                            duration: const Duration(milliseconds: 300),
                            margin: const EdgeInsets.symmetric(horizontal: 4),
                            height: 8,
                            width: _currentPage == index ? 24 : 8, // 선택되면 길어짐
                            decoration: BoxDecoration(
                              color: _currentPage == index 
                                  ? primaryColor 
                                  : const Color(0xFFD7CCC8), // 연한 갈색
                              borderRadius: BorderRadius.circular(4),
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 32),

                    // 구글 로그인 버튼 (마지막 페이지에서만 Fade-in 등장)
                    SizedBox(
                      height: 56, // 공간 확보를 위해 항상 크기 유지
                      child: AnimatedOpacity(
                        opacity: _currentPage == 2 ? 1.0 : 0.0,
                        duration: const Duration(milliseconds: 300),
                        child: IgnorePointer(
                          ignoring: _currentPage != 2, // 안 보일 땐 클릭 금지
                          child: SizedBox(
                            width: double.infinity,
                            height: 56,
                            child: OutlinedButton(
                              onPressed: _isLoading ? null : _handleGoogleLogin,

                              style: OutlinedButton.styleFrom(
                                backgroundColor: const Color(0xFF02B152), // 기존 primaryColor (혹은 변수명 그대로 쓰셔도 됨)
                                side: BorderSide.none,
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(16),
                                ),
                                elevation: 2,
                              ),
                              
                              // [수정 2] 로딩 중이면 '뺑글이(Spinner)', 아니면 원래 '구글 로고 + 텍스트'
                              child: _isLoading
                                  ? const SizedBox(
                                      width: 24, height: 24,
                                      child: CircularProgressIndicator(
                                        color: Colors.white, 
                                        strokeWidth: 2
                                      ),
                                    )
                                  : Row(
                                      mainAxisAlignment: MainAxisAlignment.center,
                                      children: [
                                        Image.asset(
                                          'assets/images/google_logo.png',
                                          width: 24,
                                          height: 24,
                                          errorBuilder: (context, error, stackTrace) {
                                            return const Icon(Icons.login, color: Colors.white);
                                          },
                                        ),
                                        const SizedBox(width: 12),
                                        const Text(
                                          'Google로 시작하기',
                                          style: TextStyle(
                                            fontFamily: 'Pretendard',
                                            fontSize: 16,
                                            fontWeight: FontWeight.bold,
                                            color: Colors.white,
                                          ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),

                    AnimatedOpacity(
                      opacity: _currentPage == 2 ? 1.0 : 0.0,
                      duration: const Duration(milliseconds: 300),
                      child: IgnorePointer(
                        ignoring: _currentPage != 2,
                        child: RichText(
                          text: TextSpan(
                            style: TextStyle(
                              fontFamily: 'Pretendard',
                              fontSize: 14,
                              color: Colors.grey[700],
                            ),
                            children: [
                              const TextSpan(text: "구글 로그인 없이 먼저 "),
                              TextSpan(
                                text: "OK독해 체험해보기!",
                                style: const TextStyle(
                                  color: primaryColor,
                                  fontWeight: FontWeight.w700,
                                  decoration: TextDecoration.underline,
                                ),
                                recognizer: TapGestureRecognizer()..onTap = _startDemoSession,
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}