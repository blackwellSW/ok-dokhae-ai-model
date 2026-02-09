import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import '../services/api_service.dart';
import '../services/mock_api_service.dart';
import 'result_screen.dart';
import '../config/api_config.dart';
import '../services/real_api_service.dart';

class SessionScreen extends StatefulWidget {
  final String id;
  final String title;

  const SessionScreen({super.key, required this.id, required this.title});

  @override
  State<SessionScreen> createState() => _SessionScreenState();
}

enum LearningStep { loading, chatting, report }

class _SessionScreenState extends State<SessionScreen> {
  late ApiService _apiService;
  
  LearningStep _currentStep = LearningStep.loading;
  List<String> _content = []; 
  
  // 초기 대화 기록을 비워둠 (사용자가 먼저 시작)
  final List<Map<String, String>> _chatHistory = [];
  
  final TextEditingController _inputController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  
  String? _attachedFileName;
  bool _isContentExpanded = false; 

  // [Logic] 응답 대기 상태 변수 추가
  bool _isLoadingResponse = false;

  // [Logic] 서버로부터 받은 리포트 데이터를 저장할 변수
  Map<String, dynamic>? _finalReport;

  @override
  void initState() {
    super.initState();
    // [Logic] 데모 모드에 따라 서비스 선택
    _apiService = ApiConfig.demoMode ? MockApiService() : RealApiService();
    _initSession();
  }

  // [Logic] 세션 시작
  Future<void> _initSession() async {
    setState(() => _currentStep = LearningStep.loading);
    
    try {
      // 1. 지문 내용 로드
      final content = await _apiService.getWorkContent(widget.id);
      
      // 2. 세션 시작 API 호출 (서버에 방 생성)
      // (AI가 먼저 질문하지 않더라도 세션 ID는 받아와야 하므로 호출)
      await _apiService.startThinkingSession(widget.id);

      if (!mounted) return;
      setState(() {
        _content = content;
        _currentStep = LearningStep.chatting;
      });
    } catch (e) {
      print("세션 초기화 실패: $e");
      // 에러 상황에서도 채팅은 가능하게 열어둠
      if (!mounted) return;
      setState(() {
        _currentStep = LearningStep.chatting;
        _content = ["내용을 불러올 수 없습니다."];
      });
    }
  }

  Future<void> _pickFile() async {
    try {
      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['pdf', 'txt', 'docx'],
      );
      if (result != null) {
        setState(() {
          _attachedFileName = result.files.single.name;
        });
      }
    } catch (e) {
      print("파일 선택 에러: $e");
    }
  }

  // 칩을 눌렀을 때 바로 질문 전송하는 함수
  void _sendChipMessage(String text) {
    _inputController.text = text;
    _sendMessage();
  }

  // [Logic] 메시지 전송 및 응답 처리
  Future<void> _sendMessage() async {
    final text = _inputController.text.trim();
    if (text.isEmpty && _attachedFileName == null) return;

    String userMsg = text;
    if (_attachedFileName != null) {
      userMsg = "[파일 첨부: $_attachedFileName]\n$text";
    }

    setState(() {
      _chatHistory.add({"role": "user", "text": userMsg});
      _inputController.clear();
      _attachedFileName = null; 
      _isLoadingResponse = true; // [Logic] 로딩 상태 true
    });
    
    // 스크롤 아래로
    _scrollToBottom();

    try {
      // [Logic] AI 응답 호출
      final response = await _apiService.getGuidance(widget.id, text);

      if (!mounted) return;
      setState(() {
        _isLoadingResponse = false;
        
        final aiText = response['text'] as String? ?? "응답이 없습니다.";
        _chatHistory.add({"role": "ai", "text": aiText});
        
        final isFinish = response['is_finish'] as bool? ?? false;
        if (isFinish) {
          // [Logic] 리포트 데이터 저장 및 상태 변경 (화면 이동 X)
          _currentStep = LearningStep.report;
          if (response.containsKey('report')) {
            _finalReport = response['report'];
          }
        } else {
          _currentStep = LearningStep.chatting;
        }
      });
      _scrollToBottom();

    } catch (e) {
      print("메시지 전송 에러: $e");
      if (!mounted) return;
      setState(() {
        _isLoadingResponse = false;
        _chatHistory.add({"role": "ai", "text": "오류가 발생했습니다. 다시 시도해주세요."});
      });
      _scrollToBottom();
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _showExitOptions() {
    showModalBottomSheet(
      context: context, 
      builder: (sheetContext) { 
        return Container(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // [수정] 진단 -> 세션 (일관성 유지)
              const Text("세션을 종료하시겠습니까?", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              const Text("지금까지의 대화 내용을 바탕으로 분석 리포트를 생성합니다.", style: TextStyle(color: Colors.grey)),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  onPressed: () {
                    Navigator.pop(sheetContext); 
                    
                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("분석 리포트를 생성합니다...")));
                    
                    Future.delayed(const Duration(milliseconds: 1500), () {
                      if (!mounted) return;
                      // [Logic] 데이터 전달하며 이동
                      Navigator.push(
                        context, 
                        MaterialPageRoute(builder: (context) => ResultScreen(
                          title: widget.title,
                          reportData: _finalReport,
                        ))
                      );
                    });
                  },
                  // 녹색 테마 유지
                  style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF02B152)),
                  child: const Text("네, 리포트 생성하기", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                ),
              ),
              const SizedBox(height: 12),
              TextButton(
                onPressed: () => Navigator.pop(sheetContext),
                child: const Text("아니요, 더 대화할래요", style: TextStyle(color: Colors.grey)),
              ),
            ],
          ),
        );
      },
    );
  }

  void _showEvidenceSheet() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return Container(
          padding: const EdgeInsets.all(24),
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Icon(Icons.menu_book, color: Color(0xFF02B152)),
                  SizedBox(width: 8),
                  Text("근거 문장 확인", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                ],
              ),
              const SizedBox(height: 16),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFFF5F5F5),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.grey.shade300),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "\"...아니 슬플소냐. 늘물이 비 오듯 하여...\"",
                      style: TextStyle(fontSize: 16, height: 1.5, fontWeight: FontWeight.w500, fontStyle: FontStyle.italic),
                    ),
                    const SizedBox(height: 8),
                    Align(
                      alignment: Alignment.centerRight,
                      child: Text("- 3번째 문단", style: TextStyle(fontSize: 12, color: Colors.grey[700], fontWeight: FontWeight.bold)),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFFFF8E1), 
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.lightbulb, size: 16, color: Color(0xFFF57F17)),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        "💡 튜터의 노트: 이 문장에서 화자의 감정이 '슬픔'임을 직접적으로 확인할 수 있어요.",
                        style: TextStyle(fontSize: 13, color: Color(0xFFBF360C), height: 1.4),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () => Navigator.pop(context),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF02B152),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  child: const Text("확인", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                ),
              )
            ],
          ),
        );
      },
    );
  }

  // [수정] 튜터 톤앤매너가 적용된 가이드 화면
  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: const BoxDecoration(
                color: Color(0xFFE8F5E9), // 연한 녹색 배경
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.chat_bubble_outline, size: 40, color: Color(0xFF02B152)),
            ),
            const SizedBox(height: 20),
            // [수정] 설명서 말투 -> 말 거는 말투
            const Text(
              "어디가 막혔나요?\n거기서부터 같이 봐요.",
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.black87, height: 1.3),
            ),
            const SizedBox(height: 12),
            // [수정] 튜터의 역할 재정의 (안심시키기)
            Text(
              "제가 질문을 던지면서\n생각을 정리하게 도와드릴게요.",
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 14, color: Colors.grey[600], height: 1.4),
            ),
            const SizedBox(height: 30),
            // [수정] 구체적인 질문 예시 (사용자가 바로 누르고 싶게)
            Wrap(
              spacing: 8,
              runSpacing: 10,
              alignment: WrapAlignment.center,
              children: [
                _buildActionChip("🤔 이 구절, 무슨 뜻인지 모르겠어"),
                _buildActionChip("🧐 화자의 감정이 정확히 뭐야?"),
                _buildActionChip("🔑 주제를 잡는 단서가 뭐야?"),
                _buildActionChip("✅ 내 해석이 맞는지 봐줘"),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionChip(String label) {
    return ActionChip(
      label: Text(label),
      backgroundColor: Colors.white,
      side: BorderSide(color: Colors.grey.shade300),
      labelStyle: const TextStyle(color: Colors.black87, fontSize: 13),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      // 이모지(2글자) 제외하고 텍스트만 전송
      onPressed: () => _sendChipMessage(label.substring(2).trim()), 
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: Text(widget.title, style: const TextStyle(color: Colors.black, fontSize: 16)),
        backgroundColor: Colors.white,
        elevation: 0,
        iconTheme: const IconThemeData(color: Colors.black),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1.0),
          child: Container(color: Colors.grey.shade200, height: 1.0),
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 8.0),
            child: TextButton.icon(
              onPressed: _showExitOptions,
              icon: const Icon(Icons.exit_to_app, size: 18, color: Color(0xFF02B152)),
              // [수정] 진단 종료 -> 세션 종료
              label: const Text("세션 종료", style: TextStyle(color: Color(0xFF02B152), fontWeight: FontWeight.bold)),
              style: TextButton.styleFrom(
                backgroundColor: Colors.grey[50],
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
              ),
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          // 상태 배지
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
            color: const Color(0xFFFAFAFA),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.edit_note, size: 16, color: Colors.grey),
                const SizedBox(width: 8),
                const Text(
                  "실시간 사고 흐름 기록 중", 
                  style: TextStyle(fontSize: 12, color: Colors.black87, fontWeight: FontWeight.w600),
                ),
                const Spacer(),
                Text("진단 준비됨", style: TextStyle(fontSize: 11, color: Colors.grey[600])),
              ],
            ),
          ),

          // 지문 영역
          AnimatedContainer(
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeInOut,
            height: _isContentExpanded ? MediaQuery.of(context).size.height * 0.4 : 56,
            decoration: BoxDecoration(
              color: const Color(0xFFF5F5F5),
              border: Border(bottom: BorderSide(color: Colors.grey.shade300)),
            ),
            child: SingleChildScrollView(
              physics: _isContentExpanded ? const AlwaysScrollableScrollPhysics() : const NeverScrollableScrollPhysics(),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  GestureDetector(
                    onTap: () => setState(() => _isContentExpanded = !_isContentExpanded),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      color: Colors.transparent,
                      child: Row(
                        children: [
                          const Icon(Icons.description_outlined, size: 18, color: Color(0xFF02B152)),
                          const SizedBox(width: 8),
                          const Text("지문 본문 보기", style: TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF02B152))),
                          const Spacer(),
                          Text(
                            _isContentExpanded ? "접기" : "펼쳐보기",
                            style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                          ),
                          const SizedBox(width: 4),
                          Icon(
                            _isContentExpanded ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
                            size: 20,
                            color: Colors.grey.shade600,
                          ),
                        ],
                      ),
                    ),
                  ),
                  if (_isContentExpanded)
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Divider(),
                           ..._content.map((sentence) => Padding(
                            padding: const EdgeInsets.only(bottom: 8.0),
                            child: Text(sentence, style: const TextStyle(fontSize: 15, height: 1.6)),
                          )),
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ),

          // 대화 영역
          Expanded(
            child: Container(
              color: Colors.white,
              child: Column(
                children: [
                  Expanded(
                    // 대화 기록이 없으면 가이드(EmptyState), 있으면 채팅 리스트
                    child: _chatHistory.isEmpty && _currentStep != LearningStep.loading
                      ? _buildEmptyState()
                      : ListView.builder(
                          controller: _scrollController,
                          padding: const EdgeInsets.all(16),
                          itemCount: _chatHistory.length + (_isLoadingResponse ? 1 : 0),
                          itemBuilder: (context, index) {
                            // [UI] 로딩 인디케이터 (메시지 마지막에 표시)
                            if (index == _chatHistory.length) {
                              return const Align(
                                alignment: Alignment.centerLeft,
                                child: Padding(
                                  padding: EdgeInsets.all(8.0),
                                  child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)),
                                ),
                              );
                            }
                            final msg = _chatHistory[index];
                            final isAi = msg['role'] == 'ai';
                            return _buildChatBubble(isAi, msg['text']!);
                          },
                        ),
                  ),
                  _buildBottomArea(),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildChatBubble(bool isAi, String text) {
    return Column(
      crossAxisAlignment: isAi ? CrossAxisAlignment.start : CrossAxisAlignment.end,
      children: [
        if (isAi) 
          const Padding(
            padding: EdgeInsets.only(left: 4, bottom: 4),
            child: Text("튜터", style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF02B152))),
          ),
        
        Container(
          margin: EdgeInsets.only(bottom: isAi ? 4 : 12), 
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.8),
          decoration: BoxDecoration(
            color: isAi ? const Color(0xFFF5F5F5) : const Color(0xFF02B152),
            borderRadius: BorderRadius.only(
              topLeft: const Radius.circular(16),
              topRight: const Radius.circular(16),
              bottomLeft: isAi ? const Radius.circular(4) : const Radius.circular(16),
              bottomRight: isAi ? const Radius.circular(16) : const Radius.circular(4),
            ),
          ),
          child: Text(
            text, 
            style: TextStyle(
              fontSize: 15, 
              height: 1.4, 
              color: isAi ? Colors.black87 : Colors.white
            )
          ),
        ),

        if (isAi)
          Padding(
            padding: const EdgeInsets.only(bottom: 16, left: 4),
            child: GestureDetector(
              onTap: _showEvidenceSheet,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: Colors.white,
                  border: Border.all(color: Colors.grey.shade300),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.format_quote, size: 12, color: Colors.grey),
                    SizedBox(width: 4),
                    Text("근거로 쓴 문장 보기", style: TextStyle(fontSize: 11, color: Colors.black87, fontWeight: FontWeight.w500)),
                  ],
                ),
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildBottomArea() {
    if (_currentStep == LearningStep.report) {
      return Container(
        padding: const EdgeInsets.all(16),
        width: double.infinity,
        child: ElevatedButton.icon(
          onPressed: () {
            // [Logic] 리포트 확인 버튼 클릭 시 화면 이동 및 데이터 전달
            Navigator.pushReplacement(
              context,
              MaterialPageRoute(builder: (context) => ResultScreen(
                title: widget.title, 
                reportData: _finalReport // 데이터 전달
              )),
            );
          },
          icon: const Icon(Icons.assessment, color: Colors.white),
          label: const Text("최종 진단 리포트 확인", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white)),
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF02B152),
            padding: const EdgeInsets.symmetric(vertical: 16),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: Colors.grey.shade200)),
      ),
      child: Column(
        children: [
          if (_attachedFileName != null)
             Align(alignment: Alignment.centerLeft, child: Padding(padding: const EdgeInsets.only(bottom: 8), child: Chip(label: Text(_attachedFileName!), onDeleted: () => setState(() => _attachedFileName = null)))),
          
          Row(
            children: [
              IconButton(onPressed: _pickFile, icon: const Icon(Icons.attach_file, color: Colors.grey)),
              const SizedBox(width: 4),
              Expanded(
                child: TextField(
                  controller: _inputController,
                  // [수정] 질문 유도형 placeholder
                  decoration: const InputDecoration(hintText: "질문이나 막힌 구절을 입력하세요...", border: InputBorder.none, isDense: true),
                  onSubmitted: (_) => _sendMessage(),
                ),
              ),
              IconButton(onPressed: _sendMessage, icon: const Icon(Icons.send, color: Color(0xFF02B152))),
            ],
          ),
        ],
      ),
    );
  }
}