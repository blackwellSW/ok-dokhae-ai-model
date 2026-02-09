import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/gestures.dart'; 
import 'dart:math';
import 'session_screen.dart';
import '../models/work.dart';
import '../services/api_service.dart';
import '../services/mock_api_service.dart';
import '../services/real_api_service.dart';
import '../config/api_config.dart';
import '../repositories/document_repository.dart';
import 'package:flutter/foundation.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late ApiService _apiService;
  late Future<List<Work>> _demoWorksFuture;
  final DocumentRepository _docRepo = DocumentRepository();
  
  final Set<String> _locallyDeletedIds = {};
  
  final ScrollController _scrollController = ScrollController();

  // [UI Logic] 화살표 표시 여부 상태
  bool _showLeftButton = false;
  bool _showRightButton = true; // 데이터가 로딩되기 전엔 일단 보이게 하거나, 로직에 따라 처리

  @override
  void initState() {
    super.initState();
    _loadWorks();
  }

  void _loadWorks() {
    _apiService = ApiConfig.demoMode ? MockApiService() : RealApiService();
    _demoWorksFuture = _apiService.getWorks();
  }

  // [UI Logic] 스크롤 버튼 상태 업데이트 함수
  bool _updateScrollVisibility(ScrollNotification notification) {
    final metrics = notification.metrics;
    
    // 왼쪽: 스크롤이 0보다 크면 보임
    final showLeft = metrics.pixels > 0;
    
    // 오른쪽: 현재 위치가 최대 길이보다 작으면 보임 (여유분 1픽셀 둠)
    final showRight = metrics.pixels < metrics.maxScrollExtent - 1;

    if (_showLeftButton != showLeft || _showRightButton != showRight) {
      setState(() {
        _showLeftButton = showLeft;
        _showRightButton = showRight;
      });
    }
    return true; // 이벤트 버블링 허용
  }

  void _scrollLeft() {
    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        _scrollController.offset - 240, 
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOutCubic,
      );
    }
  }

  void _scrollRight() {
    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        _scrollController.offset + 240,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOutCubic,
      );
    }
  }

  Future<void> _handleFileUpload() async {
    try {
      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['pdf', 'txt', 'docx'],
        withData: true, 
      );

      if (result != null) {
        final file = result.files.single;
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("문서 분석 중...")));

        final newDoc = await _docRepo.uploadDocument(
          fileName: file.name,
          filePath: kIsWeb ? null : file.path, 
          fileBytes: file.bytes,               
        );

        if (newDoc != null) {
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("분석 완료!")));
          
          setState(() {
            _loadWorks();
          });

          final int realCharCount = newDoc.charCount ?? 0;
          final int realTime = (realCharCount / 500).ceil();

          final newWork = Work(
            id: newDoc.id,
            title: newDoc.title,
            author: "방금 업로드",
            category: "개인 학습",
            baseColor: const Color(0xFF02B152), 
            patternColor: const Color(0xFFE8F5E9),
            spineColor: const Color(0xFF1B5E20),
            studyTime: "${realTime}분", 
          );

          _showContentPreview(newWork, realCharCount); 
          
        } else {
          throw Exception("업로드 실패");
        }
      }
    } catch (e) {
      print("업로드 에러: $e");
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("오류가 발생했습니다.")));
    }
  }

  Future<void> _deleteWork(String workId) async {
    bool? confirm = await showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text("문서 삭제"),
        content: const Text("목록에서 이 문서를 삭제하시겠습니까?"),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text("취소")),
          TextButton(onPressed: () => Navigator.pop(context, true), child: const Text("삭제", style: TextStyle(color: Colors.red))),
        ],
      ),
    );

    if (confirm == true) {
      await _docRepo.deleteDocument(workId);
      setState(() {
        _locallyDeletedIds.add(workId);
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("삭제되었습니다.")));
    }
  }

  void _showContentPreview(Work work, [int? specificCharCount]) {
    final displayCharCount = specificCharCount != null ? "$specificCharCount자" : "정보 없음";

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 20), decoration: BoxDecoration(color: Colors.grey[300], borderRadius: BorderRadius.circular(2)))),
              const Row(children: [
                Icon(Icons.description, color: Color(0xFF02B152)),
                SizedBox(width: 8),
                Text("학습 자료 준비 완료", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold))
              ]),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(color: const Color(0xFFF5F5F5), borderRadius: BorderRadius.circular(12)),
                child: Column(
                  children: [
                    Row(children: [
                      const Icon(Icons.check_circle, size: 20, color: Color(0xFF02B152)),
                      const SizedBox(width: 12),
                      Expanded(child: Text(work.title, style: const TextStyle(fontWeight: FontWeight.bold), overflow: TextOverflow.ellipsis)),
                    ]),
                    const SizedBox(height: 12),
                    const Divider(height: 1),
                    const SizedBox(height: 12),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _buildMetaItem("글자 수", displayCharCount), 
                        _buildMetaItem("예상 시간", work.studyTime),
                        _buildMetaItem("추출 품질", "매우 좋음"),
                      ],
                    )
                  ],
                ),
              ),
              const SizedBox(height: 24),
              const Text("지문 미리보기", style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.grey)),
              const SizedBox(height: 8),
              Container(
                height: 100,
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(border: Border.all(color: Colors.grey.shade300), borderRadius: BorderRadius.circular(8)),
                child: SingleChildScrollView(
                  child: FutureBuilder<List<String>>(
                    future: _apiService.getWorkContent(work.id),
                    builder: (context, snapshot) {
                      if (snapshot.connectionState == ConnectionState.waiting) {
                        return const Center(child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)));
                      }
                      String displayText = "내용을 불러올 수 없습니다.";
                      if (snapshot.hasData && snapshot.data!.isNotEmpty) {
                        displayText = snapshot.data!.join("\n\n");
                      }
                      return Text(displayText, style: const TextStyle(fontSize: 14, height: 1.6, color: Colors.black87));
                    },
                  ),
                ),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: () {
                    Navigator.pop(context);
                    _navigateToSession(work.id, work.title);
                  },
                  style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF02B152), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16))),
                  child: const Text("이 자료로 진단 시작하기", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildMetaItem(String label, String value) {
    return Column(
      children: [
        Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
        const SizedBox(height: 4),
        Text(label, style: TextStyle(fontSize: 12, color: Colors.grey[600])),
      ],
    );
  }

  void _navigateToSession(String id, String title) {
    Navigator.push(context, MaterialPageRoute(builder: (context) => SessionScreen(id: id, title: title)));
  }

  void _navigateToDemo(Work work) => _navigateToSession(work.id, work.title);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 30),
              child: Row(
                children: [
                  const Icon(Icons.auto_stories, color: Color(0xFF02B152), size: 28),
                  const SizedBox(width: 8),
                  const Text("OK 독해", style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: Color(0xFF1B5E20))),
                  const Spacer(),
                  IconButton(onPressed: () {}, icon: const Icon(Icons.account_circle, color: Color(0xFF02B152), size: 32)),
                ],
              ),
            ),
            const Spacer(flex: 1),
            Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text("대화로 사고를 확장하고,\n리포트로 진단해드려요.", textAlign: TextAlign.center, style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.black87, height: 1.3)),
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                    decoration: BoxDecoration(color: const Color(0xFFE8F5E9), borderRadius: BorderRadius.circular(20), border: Border.all(color: const Color(0xFFC8E6C9))),
                    child: const Text("✨ 3분 대화 후: 핵심 요약 + 사고 패턴 분석 리포트 제공", style: TextStyle(fontSize: 13, color: Color(0xFF1B5E20), fontWeight: FontWeight.bold)),
                  ),
                  const SizedBox(height: 40),
                  GestureDetector(
                    onTap: _handleFileUpload,
                    child: Container(
                      width: 280, height: 180,
                      decoration: BoxDecoration(color: const Color(0xFFF5F5F5), borderRadius: BorderRadius.circular(20), border: Border.all(color: const Color(0xFFE0E0E0), width: 2), boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 10, offset: const Offset(0, 4))]),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Container(
                            padding: const EdgeInsets.all(16),
                            decoration: BoxDecoration(color: Colors.white, shape: BoxShape.circle, boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.1), blurRadius: 8)]),
                            child: const Icon(Icons.cloud_upload_rounded, size: 40, color: Color(0xFF02B152)),
                          ),
                          const SizedBox(height: 16),
                          const Text("파일 업로드하기", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF1B5E20))),
                          const SizedBox(height: 4),
                          const Text("PDF, TXT, DOCX 지원", style: TextStyle(fontSize: 12, color: Colors.grey)),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const Spacer(flex: 2),

            Container(
              padding: const EdgeInsets.all(24),
              decoration: const BoxDecoration(color: Color(0xFFFAFAFA), borderRadius: BorderRadius.only(topLeft: Radius.circular(30), topRight: Radius.circular(30))),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("자료가 없으신가요? 예시로 시작해보세요.", style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.grey)),
                  const SizedBox(height: 16),
                  
                  SizedBox(
                    height: 100,
                    child: FutureBuilder<List<Work>>(
                      future: _demoWorksFuture,
                      builder: (context, snapshot) {
                        if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
                        
                        final works = snapshot.data!.where((w) => !_locallyDeletedIds.contains(w.id)).toList();
                        if (works.isEmpty) return const Text("등록된 문서가 없습니다.");

                        return Stack(
                          alignment: Alignment.center,
                          children: [
                            // [FIX] NotificationListener로 스크롤 감지 -> 버튼 상태 업데이트
                            NotificationListener<ScrollNotification>(
                              onNotification: _updateScrollVisibility,
                              child: ScrollConfiguration(
                                behavior: ScrollConfiguration.of(context).copyWith(
                                  dragDevices: {PointerDeviceKind.touch, PointerDeviceKind.mouse},
                                ),
                                child: ListView.separated(
                                  controller: _scrollController,
                                  scrollDirection: Axis.horizontal,
                                  itemCount: works.length,
                                  separatorBuilder: (_, __) => const SizedBox(width: 12),
                                  itemBuilder: (context, index) {
                                    final work = works[index];
                                    return GestureDetector(
                                      onTap: () => _navigateToDemo(work),
                                      child: Container(
                                        width: 220,
                                        margin: const EdgeInsets.only(bottom: 12),
                                        padding: const EdgeInsets.all(16),
                                        decoration: BoxDecoration(color: work.baseColor.withOpacity(0.1), borderRadius: BorderRadius.circular(16), border: Border.all(color: work.baseColor)),
                                        child: Row(
                                          children: [
                                            Container(width: 40, height: 40, decoration: BoxDecoration(color: work.spineColor, shape: BoxShape.circle), child: Center(child: Text(work.title.isNotEmpty ? work.title[0] : '?', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)))),
                                            const SizedBox(width: 12),
                                            Expanded(
                                              child: Column(
                                                crossAxisAlignment: CrossAxisAlignment.start,
                                                mainAxisAlignment: MainAxisAlignment.center,
                                                children: [
                                                  Text(work.title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16), maxLines: 1, overflow: TextOverflow.ellipsis),
                                                  Text(work.author, style: const TextStyle(fontSize: 12, color: Colors.black54))
                                                ]
                                              )
                                            ),
                                            IconButton(
                                              icon: const Icon(Icons.delete_outline, color: Colors.grey),
                                              onPressed: () => _deleteWork(work.id),
                                            ),
                                          ],
                                        ),
                                      ),
                                    );
                                  },
                                ),
                              ),
                            ),

                            // [UI] 왼쪽 화살표 (맨 왼쪽이면 안 보임)
                            if (_showLeftButton)
                              Positioned(
                                left: 0,
                                child: GestureDetector(
                                  onTap: _scrollLeft,
                                  child: Container(
                                    width: 48, 
                                    height: 48,
                                    decoration: BoxDecoration(
                                      color: Colors.white.withOpacity(0.95),
                                      shape: BoxShape.circle,
                                      boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.15), blurRadius: 8, offset: const Offset(0, 2))],
                                    ),
                                    child: const Icon(Icons.arrow_back_ios_new, size: 24, color: Colors.black87),
                                  ),
                                ),
                              ),

                            // [UI] 오른쪽 화살표 (맨 오른쪽이면 안 보임)
                            if (_showRightButton)
                              Positioned(
                                right: 0,
                                child: GestureDetector(
                                  onTap: _scrollRight,
                                  child: Container(
                                    width: 48,
                                    height: 48,
                                    decoration: BoxDecoration(
                                      color: Colors.white.withOpacity(0.95),
                                      shape: BoxShape.circle,
                                      boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.15), blurRadius: 8, offset: const Offset(0, 2))],
                                    ),
                                    child: const Icon(Icons.arrow_forward_ios, size: 24, color: Colors.black87),
                                  ),
                                ),
                              ),
                          ],
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}