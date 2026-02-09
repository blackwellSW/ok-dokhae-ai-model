import 'package:flutter/material.dart';

class ResultScreen extends StatelessWidget {
  final String title;
  final Map<String, dynamic>? reportData;

  const ResultScreen({
    super.key,
    required this.title,
    this.reportData,
  });

  @override
  Widget build(BuildContext context) {
    // [진단용 로그]
    if (reportData != null) {
      print("✅ [ResultScreen] 데이터 수신 성공: $reportData");
    } else {
      print("⚠️ [ResultScreen] 데이터 없음 (Mock 데이터 사용)");
    }

    // [Mock Data] fallback
    final Map<String, dynamic> mockData = {
      "summary": "서버로부터 데이터를 불러오지 못했습니다.",
      "tags": ["#데이터없음"], 
      "scores": [],
      "flow_analysis": [],
      "prescription": "잠시 후 다시 시도해주세요."
    };

    final data = reportData ?? mockData;
    
    // [데이터 파싱 및 방어 로직]
    final List<dynamic> tags = (data['tags'] is List) ? data['tags'] : [];
    final List<dynamic> scores = (data['scores'] is List) ? data['scores'] : [];
    final List<dynamic> flows = (data['flow_analysis'] is List) ? data['flow_analysis'] : [];
    
    final String summary = data['summary']?.toString() ?? "요약 내용이 없습니다.";
    final String prescription = data['prescription']?.toString() ?? "처방 내용이 없습니다.";

    return Scaffold(
      backgroundColor: Colors.grey[50],
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        title: const Text("진단 리포트", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
        leading: IconButton(
          icon: const Icon(Icons.close, color: Colors.black),
          onPressed: () => Navigator.of(context).popUntil((route) => route.isFirst),
        ),
      ),
      body: SingleChildScrollView(
        child: Column(
          children: [
            // 1. 헤더
            Container(
              width: double.infinity,
              color: Colors.white,
              padding: const EdgeInsets.fromLTRB(24, 20, 24, 30),
              child: Column(
                children: [
                  Wrap(
                    spacing: 8,
                    children: tags.map((tag) => Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: const Color(0xFFE8F5E9),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: const Color(0xFFC8E6C9)),
                      ),
                      child: Text(tag.toString(), style: const TextStyle(color: Color(0xFF1B5E20), fontWeight: FontWeight.bold, fontSize: 13)),
                    )).toList(),
                  ),
                  const SizedBox(height: 20),
                  Text(
                    summary,
                    textAlign: TextAlign.center,
                    style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, height: 1.4, color: Color(0xFF263238)),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 8),

            // 2. 역량 분석 (점수) - [수정] 점수 매핑 로직 개선
            if (scores.isNotEmpty)
              Container(
                color: Colors.white,
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text("영역별 강점 및 약점", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    const Text("이번 세션에서 관찰된 사고 패턴을 분석했습니다.", style: TextStyle(fontSize: 13, color: Colors.grey)),
                    const SizedBox(height: 24),
                    
                    ...scores.map<Widget>((item) {
                      // 1. 점수 추출 (0.0 ~ 1.0)
                      double rawScore = (item['score'] is num) ? (item['score'] as num).toDouble() : 0.0;
                      
                      // [Logic] 만약 서버가 100점 단위로 보냈다면 1.0 단위로 정규화
                      if (rawScore > 1.0) rawScore = rawScore / 100.0;
                      // 범위를 0~1로 제한
                      rawScore = rawScore.clamp(0.0, 1.0);

                      final String label = item['label']?.toString() ?? "평가 항목";
                      final String reason = item['reason']?.toString() ?? "분석 내용 없음";
                      
                      // [Logic] 점수에 따른 등급 및 색상 자동 매핑
                      String gradeText;
                      Color gradeColor;
                      
                      if (rawScore >= 0.9) {
                        gradeText = "탁월"; // S급
                        gradeColor = const Color(0xFF2E7D32); // 진한 녹색
                      } else if (rawScore >= 0.75) {
                        gradeText = "우수"; // A급
                        gradeColor = const Color(0xFF43A047); // 녹색
                      } else if (rawScore >= 0.5) {
                        gradeText = "보통"; // B급
                        gradeColor = const Color(0xFFF9A825); // 노란색
                      } else {
                        gradeText = "미흡"; // C급 이하
                        gradeColor = const Color(0xFFC62828); // 빨간색
                      }
                      
                      // 서버에서 label_text를 줬다면 그걸 우선 사용
                      final String finalLabelText = item['label_text']?.toString() ?? gradeText;

                      return Padding(
                        padding: const EdgeInsets.only(bottom: 24.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                SizedBox(width: 70, child: Text(label, style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.black87))),
                                Expanded(
                                  child: ClipRRect(
                                    borderRadius: BorderRadius.circular(4),
                                    child: LinearProgressIndicator(
                                      value: rawScore, // 0.0 ~ 1.0 사용
                                      minHeight: 8,
                                      backgroundColor: Colors.grey[100],
                                      color: gradeColor,
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 12),
                                // 등급 텍스트 (예: 탁월)
                                Text(finalLabelText, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: gradeColor)),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Padding(
                              padding: const EdgeInsets.only(left: 70), 
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Icon(Icons.subdirectory_arrow_right, size: 14, color: Colors.grey),
                                  const SizedBox(width: 4),
                                  Expanded(child: Text(reason, style: TextStyle(fontSize: 12, color: Colors.grey[700], height: 1.3))),
                                ],
                              ),
                            ),
                          ],
                        ),
                      );
                    }).toList(),
                  ],
                ),
              ),
            
            if (scores.isEmpty)
               Container(
                 width: double.infinity,
                 padding: const EdgeInsets.all(24),
                 color: Colors.white,
                 child: const Text("점수 분석 데이터를 불러오지 못했습니다.", style: TextStyle(color: Colors.grey)),
               ),

            const SizedBox(height: 8),

            // 3. 사고 흐름 분석
            if (flows.isNotEmpty)
              Container(
                color: Colors.white,
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(children: [Icon(Icons.timeline, color: Color(0xFF02B152)), SizedBox(width: 8), Text("사고 흐름 상세 진단", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold))]),
                    const SizedBox(height: 24),
                    
                    ...flows.map<Widget>((step) {
                      final status = step['status']?.toString() ?? 'weak';
                      final title = step['step']?.toString() ?? '단계';
                      final comment = step['comment']?.toString() ?? '';
                      final quote = step['quote']?.toString();

                      return IntrinsicHeight(
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Column(children: [_buildStepIcon(status), Expanded(child: Container(width: 2, color: Colors.grey[200]))]),
                            const SizedBox(width: 16),
                            Expanded(
                              child: Padding(
                                padding: const EdgeInsets.only(bottom: 30.0),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(title, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.black87)),
                                    const SizedBox(height: 4),
                                    Text(comment, style: const TextStyle(fontSize: 14, height: 1.4, color: Colors.black54)),
                                    if (quote != null && quote.isNotEmpty)
                                      Container(
                                        margin: const EdgeInsets.only(top: 8),
                                        padding: const EdgeInsets.all(10),
                                        decoration: BoxDecoration(color: const Color(0xFFF5F5F5), borderRadius: BorderRadius.circular(8), border: Border.all(color: Colors.grey.shade300)),
                                        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [const Icon(Icons.format_quote, size: 14, color: Color(0xFF02B152)), const SizedBox(width: 6), Expanded(child: Text(quote, style: const TextStyle(fontSize: 13, fontStyle: FontStyle.italic, color: Color(0xFF1B5E20))))]),
                                      ),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        ),
                      );
                    }).toList(),
                  ],
                ),
              ),

            const SizedBox(height: 8),

            // 4. 튜터의 맞춤 처방
            Container(
              color: Colors.white,
              padding: const EdgeInsets.all(24),
              width: double.infinity,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("💊 튜터의 맞춤 처방", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(color: const Color(0xFFFFF8E1), borderRadius: BorderRadius.circular(12), border: Border.all(color: const Color(0xFFFFE0B2))),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Row(children: [Icon(Icons.lightbulb_outline, color: Color(0xFFF57F17)), SizedBox(width: 8), Text("이렇게 해보면 어때요?", style: TextStyle(fontWeight: FontWeight.bold, color: Color(0xFFE65100)))]),
                        const SizedBox(height: 12),
                        Text(prescription, style: const TextStyle(fontSize: 15, height: 1.5, color: Color(0xFFBF360C))),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 40),

            // 5. 하단 버튼
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: () {
                    Navigator.of(context).popUntil((route) => route.isFirst);
                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("리포트가 저장되었습니다.")));
                  },
                  style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF02B152), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16))),
                  child: const Text("리포트 저장 및 종료", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white)),
                ),
              ),
            ),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }

  // 아이콘 매핑 함수 (상태에 따라 아이콘과 색상 반환)
  Widget _buildStepIcon(String status) {
    IconData icon;
    Color color;
    
    // 소문자로 변환해 비교 (혹시나 대문자로 올 경우 대비)
    final s = status.toLowerCase();

    if (s.contains('perfect') || s.contains('excellent')) {
      icon = Icons.check_circle;
      color = const Color(0xFF2E7D32);
    } else if (s.contains('good') || s.contains('average')) {
      icon = Icons.check_circle_outline;
      color = const Color(0xFF1976D2);
    } else {
      // weak, bad 등
      icon = Icons.error_outline;
      color = const Color(0xFFF57F17);
    }
    return Container(color: Colors.white, child: Icon(icon, color: color, size: 24));
  }
}