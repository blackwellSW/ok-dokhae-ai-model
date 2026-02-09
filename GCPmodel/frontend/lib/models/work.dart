import 'package:flutter/material.dart';

// [데이터 모델] 작품(Work) 정보
// 기존 Book 클래스를 API 명세에 맞춰 Work로 변경
class Work {
  final String id;          // 작품 고유 ID (예: 'simcheong')
  final String title;       // 제목
  final String author;      // 작가
  final String category;    // 카테고리 (고전소설, 고전시가 등)
  
  // UI용 디자인 속성 (나중엔 서버에서 테마 코드로 받을 수도 있음)
  final Color baseColor;    
  final Color patternColor; 
  final Color spineColor;   
  
  final int completedSets;  // 완료한 세트 수
  final String studyTime;   // 예상 학습 시간
  final String difficulty;  // 난이도 (상/중/하)

  Work({
    required this.id,
    required this.title,
    required this.author,
    required this.category,
    required this.baseColor,
    required this.patternColor,
    required this.spineColor,
    this.completedSets = 0,
    this.studyTime = '5분',
    this.difficulty = '중',
  });
}