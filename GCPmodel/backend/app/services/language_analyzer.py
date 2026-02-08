"""
언어 분석 기반 정량 평가 시스템
역할: 어휘 다양성, 핵심 개념어, 문장 복잡도, 반복 패턴, 감정 톤 분석
"""

from collections import Counter
from typing import Dict, List
import math
import re


class LanguageAnalyzer:
    """정량적 언어 분석 시스템"""
    
    def __init__(self):
        self.okt = None
        try:
            from konlpy.tag import Okt
            self.okt = Okt()
        except ImportError:
            print("Warning: KoNLPy not installed. Using basic text analysis.")
        except Exception as e:
            print(f"Warning: KoNLPy 초기화 실패 ({e}). 기본 분석으로 대체됩니다.")
    
    def analyze(self, student_text: str) -> Dict:
        """
        학생 텍스트에 대한 종합 정량 분석
        
        Returns:
            - 어휘_다양성: TTR, MTLD 기반 점수
            - 핵심_개념어: 문학 관련 용어 사용 빈도
            - 문장_복잡도: 평균 길이 및 절 개수
            - 반복_패턴: 과도한 반복 감지
            - 감정_톤: 학습 태도 분석
        """
        
        if not student_text or not student_text.strip():
            return self._empty_result()
        
        # 형태소 분석
        morphs = self._get_morphs(student_text)
        sentences = self._split_sentences(student_text)
        
        return {
            "어휘_다양성": self._analyze_vocabulary(morphs, student_text),
            "핵심_개념어": self._analyze_concepts(morphs, student_text),
            "문장_복잡도": self._analyze_complexity(sentences, morphs),
            "반복_패턴": self._analyze_repetition(morphs),
            "감정_톤": self._analyze_sentiment(student_text),
            "통계": {
                "총_단어": len(morphs),
                "고유_단어": len(set(morphs)),
                "문장_수": len(sentences),
                "평균_문장_길이": round(len(morphs) / len(sentences), 1) if sentences else 0
            }
        }
    
    def _get_morphs(self, text: str) -> List[str]:
        """형태소 추출"""
        if self.okt:
            try:
                return self.okt.morphs(text)
            except:
                pass
        # Fallback: 공백 기준 분리
        return text.split()
    
    def _split_sentences(self, text: str) -> List[str]:
        """문장 분리"""
        return [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    
    # ============================================================
    # 1. 어휘 다양성 분석
    # ============================================================
    
    def _analyze_vocabulary(self, morphs: List[str], text: str) -> Dict:
        """
        다층적 어휘 다양성 분석
        - 기본 TTR (Type-Token Ratio)
        - MTLD (텍스트 길이 보정)
        - 학문적 어휘 비율
        """
        if not morphs:
            return {"점수": 0, "등급": "N/A", "해석": "텍스트 없음"}
        
        # 1. 기본 TTR
        basic_ttr = len(set(morphs)) / len(morphs)
        
        # 2. MTLD (간소화 버전)
        mtld_score = self._calculate_mtld(morphs)
        
        # 3. 학문적 어휘 (3음절 이상)
        academic_score = sum(1 for m in morphs if len(m) >= 3) / len(morphs)
        
        # 최종 점수
        final_score = (
            basic_ttr * 0.5 +
            mtld_score * 0.3 +
            academic_score * 0.2
        )
        
        return {
            "점수": round(final_score, 3),
            "등급": self._grade_vocabulary(final_score),
            "세부": {
                "기본_TTR": round(basic_ttr, 3),
                "MTLD": round(mtld_score, 3),
                "학문적_어휘_비율": round(academic_score, 3)
            },
            "해석": self._interpret_vocabulary(final_score)
        }
    
    def _calculate_mtld(self, morphs: List[str], threshold: float = 0.72) -> float:
        """MTLD 계산 (텍스트 길이 보정)"""
        if len(morphs) < 10:
            return len(set(morphs)) / len(morphs)
        
        factors = []
        start = 0
        
        for i in range(10, len(morphs)):
            segment = morphs[start:i]
            ttr = len(set(segment)) / len(segment)
            if ttr < threshold:
                factors.append(i - start)
                start = i
        
        if start < len(morphs):
            factors.append(len(morphs) - start)
        
        avg_factor = sum(factors) / len(factors) if factors else 10
        return min(avg_factor / 50, 1.0)
    
    def _grade_vocabulary(self, score: float) -> str:
        if score >= 0.75:
            return "우수"
        elif score >= 0.6:
            return "양호"
        elif score >= 0.4:
            return "보통"
        else:
            return "개선필요"
    
    def _interpret_vocabulary(self, score: float) -> str:
        if score >= 0.75:
            return "풍부하고 정교한 어휘 사용. 학문적 표현력 우수."
        elif score >= 0.6:
            return "적절한 어휘 사용. 다양성 양호."
        elif score >= 0.4:
            return "기본적 어휘 사용. 표현력 향상 필요."
        else:
            return "제한적 어휘. 다양한 표현 연습 권장."
    
    # ============================================================
    # 2. 핵심 개념어 분석
    # ============================================================
    
    def _analyze_concepts(self, morphs: List[str], text: str) -> Dict:
        """
        고전문학 관련 핵심 개념어 사용 분석
        """
        
        # 고전문학 핵심 개념어 목록
        concept_keywords = {
            "문학적_기법": ["상징", "은유", "비유", "복선", "반전", "갈등", "구조", "형상", "표현"],
            "사회문화적_맥락": ["신분", "계급", "시대", "배경", "사상", "유교", "가부장", "사회"],
            "인간관계_심리": ["사랑", "효", "충", "절개", "욕망", "갈등", "화해", "희생", "감정"],
            "주제_메시지": ["주제", "교훈", "풍자", "비판", "가치관", "이상", "의미", "메시지"]
        }
        
        # 카테고리별 매칭
        category_matches = {}
        total_count = 0
        
        for category, keywords in concept_keywords.items():
            matches = []
            for keyword in keywords:
                if keyword in text:
                    count = text.count(keyword)
                    matches.append({"용어": keyword, "빈도": count})
                    total_count += count
            
            if matches:
                category_matches[category] = matches
        
        coverage = len(category_matches)
        
        return {
            "카테고리별_매칭": category_matches,
            "총_개념_사용": total_count,
            "커버리지": coverage,
            "평가": self._evaluate_concepts(total_count, coverage),
            "해석": self._interpret_concepts(total_count, coverage)
        }
    
    def _evaluate_concepts(self, total: int, coverage: int) -> str:
        if total >= 5 and coverage >= 3:
            return "우수"
        elif total >= 3 and coverage >= 2:
            return "양호"
        elif total >= 1:
            return "보통"
        else:
            return "부족"
    
    def _interpret_concepts(self, total: int, coverage: int) -> str:
        if total >= 5 and coverage >= 3:
            return "다양한 문학적 개념을 적절히 활용"
        elif total >= 3:
            return "핵심 개념을 부분적으로 사용"
        else:
            return "개념적 용어 사용 부족. 문학적 개념 활용 권장"
    
    # ============================================================
    # 3. 문장 복잡도 분석
    # ============================================================
    
    def _analyze_complexity(self, sentences: List[str], morphs: List[str]) -> Dict:
        """문장 복잡도 분석"""
        if not sentences:
            return {"점수": 0, "등급": "N/A"}
        
        avg_length = len(morphs) / len(sentences)
        avg_clauses = sum(s.count(',') + 1 for s in sentences) / len(sentences)
        score = (avg_length / 10) + (avg_clauses * 2)
        
        if score >= 10:
            grade = "복잡함"
        elif score >= 6:
            grade = "적절함"
        else:
            grade = "단순함"
        
        return {
            "점수": round(score, 2),
            "등급": grade,
            "평균_문장_길이": round(avg_length, 1),
            "평균_절_개수": round(avg_clauses, 1)
        }
    
    # ============================================================
    # 4. 반복 패턴 분석
    # ============================================================
    
    def _analyze_repetition(self, morphs: List[str]) -> Dict:
        """과도한 반복 패턴 감지"""
        if not morphs:
            return {"과도한_반복": {}, "반복률": 0, "평가": "N/A"}
        
        freq = Counter(morphs)
        excessive = {w: c for w, c in freq.items() if c >= 3 and len(w) > 1}
        repetition_rate = sum(excessive.values()) / len(morphs) if morphs else 0
        
        return {
            "과도한_반복": excessive,
            "반복률": round(repetition_rate, 3),
            "평가": "주의" if repetition_rate > 0.2 else "양호"
        }
    
    # ============================================================
    # 5. 감정 톤 분석
    # ============================================================
    
    def _analyze_sentiment(self, text: str) -> Dict:
        """
        학습 태도 기반 감정 분석
        """
        
        # 학습 관련 키워드
        positive_keywords = ["흥미롭", "재미있", "이해했", "공감", "인상적", "좋", "알았"]
        negative_keywords = ["어렵", "이해안", "모르겠", "헷갈", "복잡", "힘들"]
        constructive_keywords = ["궁금", "알고싶", "생각해", "탐구", "관심", "배우"]
        
        pos_count = sum(1 for w in positive_keywords if w in text)
        neg_count = sum(1 for w in negative_keywords if w in text)
        con_count = sum(1 for w in constructive_keywords if w in text)
        
        # 학습 태도 판단
        if con_count >= 2:
            tone = "탐구적"
            score = 0.8
        elif pos_count >= neg_count + 2:
            tone = "적극적"
            score = 0.6
        elif pos_count > neg_count:
            tone = "긍정적"
            score = 0.4
        elif neg_count > pos_count + 2:
            tone = "소극적"
            score = -0.4
        else:
            tone = "중립적"
            score = 0.0
        
        return {
            "학습_태도": tone,
            "점수": round(score, 3),
            "해석": self._interpret_sentiment(tone)
        }
    
    def _interpret_sentiment(self, tone: str) -> str:
        if tone == "탐구적":
            return "학습 흥미와 탐구 의지 높음. 매우 우수한 학습 태도."
        elif tone in ["적극적", "긍정적"]:
            return "학습에 적극적. 긍정적 태도 유지."
        elif tone == "소극적":
            return "학습 동기 저하. 지원 필요."
        else:
            return "보통 수준의 학습 태도."
    
    # ============================================================
    # 유틸리티
    # ============================================================
    
    def _empty_result(self) -> Dict:
        """빈 텍스트에 대한 기본 결과"""
        return {
            "어휘_다양성": {"점수": 0, "등급": "N/A", "해석": "텍스트 없음"},
            "핵심_개념어": {"총_개념_사용": 0, "커버리지": 0, "평가": "부족", "해석": "텍스트 없음"},
            "문장_복잡도": {"점수": 0, "등급": "N/A"},
            "반복_패턴": {"반복률": 0, "평가": "N/A"},
            "감정_톤": {"학습_태도": "중립적", "점수": 0, "해석": "텍스트 없음"},
            "통계": {"총_단어": 0, "고유_단어": 0, "문장_수": 0, "평균_문장_길이": 0}
        }
    
    def calculate_quantitative_score(self, analysis: Dict) -> float:
        """
        정량 분석 결과를 100점 만점 기준으로 환산 (30% 가중치 적용)
        
        Returns:
            정량 평가 점수 (최대 30점)
        """
        # 어휘 다양성: 최대 10점
        vocab_score = analysis["어휘_다양성"]["점수"] * 10
        
        # 개념어 사용: 최대 10점
        concept_count = analysis["핵심_개념어"]["총_개념_사용"]
        concept_score = min(concept_count * 2, 10)
        
        # 문장 복잡도: 최대 10점
        complexity_score = min(analysis["문장_복잡도"]["점수"], 10)
        
        total = vocab_score + concept_score + complexity_score
        return round(total, 1)
