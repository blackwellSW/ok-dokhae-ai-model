"""
언어 분석 모듈 (정량 평가)
- 어휘 다양성 (MTLD 기반)
- 핵심 개념어 사용 (임베딩 기반)
- 문장 복잡도
- 반복 패턴
- 감정 톤 (맥락 고려 AI)
- 유해표현 감지 (AI HUB 모델)
"""

import re
import math
from collections import Counter
from typing import Dict, List, Tuple, Optional

import numpy as np


class ComprehensiveLanguageAnalyzer:
    """통합 언어 분석 시스템"""

    def __init__(
        self,
        harmful_model_path: str = "",  # TODO: 유해표현 AI 모델 경로
        use_gpu: bool = True
    ):
        """
        Args:
            harmful_model_path: AI HUB 유해표현 모델 경로
            use_gpu: GPU 사용 여부
        """
        self.harmful_model_path = harmful_model_path
        self.use_gpu = use_gpu

        # 형태소 분석기 초기화
        self.okt = None
        self._init_morpheme_analyzer()

        # 개선된 분석기들
        self.vocab_analyzer = ImprovedVocabularyAnalyzer()
        self.concept_analyzer = SemanticConceptAnalyzer(use_gpu=use_gpu)
        self.sentiment_analyzer = AdvancedSentimentAnalyzer(use_gpu=use_gpu)

        # 유해표현 AI 모델
        self.harmful_detector = None
        if harmful_model_path:
            self._load_harmful_model(harmful_model_path)

    def _init_morpheme_analyzer(self):
        """형태소 분석기 초기화"""
        try:
            from konlpy.tag import Okt
            self.okt = Okt()
        except ImportError:
            print("⚠️ konlpy가 설치되지 않았습니다. pip install konlpy")
            self.okt = None

    def _load_harmful_model(self, path: str):
        """AI HUB 유해표현 AI 모델 로드"""
        # TODO: 실제 AI HUB 모델 로딩 구현
        # 모델 구조에 따라 로딩 코드 작성 필요
        print(f"⚠️ 유해표현 모델 로딩: {path}")
        print("   실제 모델 로딩 코드를 구현해주세요.")
        self.harmful_detector = None

    def analyze(self, student_text: str) -> Dict:
        """
        종합 분석

        Args:
            student_text: 학생 텍스트

        Returns:
            Dict: 분석 결과
        """
        if not student_text.strip():
            return self._empty_result()

        # 기본 토큰화
        morphs = self._tokenize(student_text)
        sentences = self._split_sentences(student_text)

        return {
            # 개선된 분석
            "어휘_다양성": self.vocab_analyzer.calculate_diversity(student_text),
            "핵심_개념어": self.concept_analyzer.analyze_concepts(student_text),
            "감정_톤": self.sentiment_analyzer.analyze_sentiment(student_text),

            # 기존 분석
            "문장_복잡도": self._calc_complexity(sentences, morphs),
            "반복_패턴": self._analyze_repetition(morphs),
            "유해표현": self._detect_harmful(student_text),

            # 통계
            "통계": {
                "총_단어": len(morphs),
                "고유_단어": len(set(morphs)),
                "문장_수": len(sentences),
                "평균_문장_길이": round(len(morphs) / len(sentences), 1) if sentences else 0
            }
        }

    def _tokenize(self, text: str) -> List[str]:
        """형태소 토큰화"""
        if self.okt:
            return self.okt.morphs(text)
        # fallback: 공백 기준 토큰화
        return text.split()

    def _split_sentences(self, text: str) -> List[str]:
        """문장 분리"""
        return [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]

    def _calc_complexity(self, sentences: List[str], morphs: List[str]) -> Dict:
        """문장 복잡도 계산"""
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

    def _analyze_repetition(self, morphs: List[str]) -> Dict:
        """반복 패턴 분석"""
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

    def _detect_harmful(self, text: str) -> Dict:
        """유해표현 감지"""
        if self.harmful_detector:
            # TODO: 실제 모델 예측 구현
            result = {"harmful_expressions": []}
            detected_count = len(result.get('harmful_expressions', []))
        else:
            detected_count = 0

        if detected_count == 0:
            level = "안전"
        elif detected_count <= 2:
            level = "주의"
        else:
            level = "경고"

        return {
            "감지_개수": detected_count,
            "경고_레벨": level,
            "조치": "교사 알림 필요" if level == "경고" else "정상"
        }

    def _empty_result(self) -> Dict:
        """빈 결과"""
        return {
            "어휘_다양성": {"점수": 0, "등급": "N/A"},
            "핵심_개념어": {"총_개념_사용": 0, "평가": "N/A"},
            "감정_톤": {"최종_톤": "N/A", "점수": 0},
            "문장_복잡도": {"점수": 0, "등급": "N/A"},
            "반복_패턴": {"반복률": 0, "평가": "N/A"},
            "유해표현": {"감지_개수": 0, "경고_레벨": "안전"},
            "통계": {"총_단어": 0, "고유_단어": 0, "문장_수": 0}
        }


class ImprovedVocabularyAnalyzer:
    """MTLD 기반 어휘 다양성 분석"""

    def __init__(self):
        self.okt = None
        try:
            from konlpy.tag import Okt
            self.okt = Okt()
        except ImportError:
            pass

    def calculate_diversity(self, text: str) -> Dict:
        """다층적 어휘 다양성 분석"""
        if self.okt:
            morphs = self.okt.morphs(text)
        else:
            morphs = text.split()

        if not morphs:
            return {"점수": 0, "등급": "N/A", "해석": "텍스트 없음"}

        # 1. 기본 TTR
        basic_ttr = len(set(morphs)) / len(morphs)

        # 2. MTLD
        mtld_score = self._calculate_mtld(morphs)

        # 3. 품사 다양성
        pos_diversity = self._pos_diversity(text) if self.okt else 0.5

        # 4. 학문적 어휘
        academic_score = self._academic_vocabulary(morphs)

        # 최종 점수
        final_score = (
            basic_ttr * 0.3 +
            mtld_score * 0.4 +
            pos_diversity * 0.2 +
            academic_score * 0.1
        )

        return {
            "점수": round(final_score, 3),
            "등급": self._grade(final_score),
            "세부": {
                "기본_TTR": round(basic_ttr, 3),
                "MTLD": round(mtld_score, 3),
                "품사_다양성": round(pos_diversity, 3),
                "학문적_어휘": round(academic_score, 3)
            },
            "해석": self._interpret(final_score)
        }

    def _calculate_mtld(self, morphs: List[str], threshold: float = 0.72) -> float:
        """MTLD 계산 (텍스트 길이 보정)"""
        if len(morphs) < 10:
            return len(set(morphs)) / len(morphs) if morphs else 0

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

    def _pos_diversity(self, text: str) -> float:
        """품사 다양성 (엔트로피)"""
        if not self.okt:
            return 0.5

        pos = self.okt.pos(text)
        pos_counts = {"Noun": 0, "Verb": 0, "Adjective": 0, "Adverb": 0}

        for word, tag in pos:
            if tag.startswith("N"):
                pos_counts["Noun"] += 1
            elif tag.startswith("V"):
                pos_counts["Verb"] += 1
            elif tag.startswith("Adj"):
                pos_counts["Adjective"] += 1
            elif tag.startswith("Adv"):
                pos_counts["Adverb"] += 1

        total = sum(pos_counts.values())
        if total == 0:
            return 0

        entropy = 0
        for count in pos_counts.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)

        return entropy / 2  # 정규화

    def _academic_vocabulary(self, morphs: List[str]) -> float:
        """학문적 어휘 비율"""
        academic_count = sum(1 for m in morphs if len(m) >= 3)
        return academic_count / len(morphs) if morphs else 0

    def _grade(self, score: float) -> str:
        if score >= 0.75:
            return "우수"
        elif score >= 0.6:
            return "양호"
        elif score >= 0.4:
            return "보통"
        else:
            return "개선필요"

    def _interpret(self, score: float) -> str:
        if score >= 0.75:
            return "풍부하고 정교한 어휘 사용. 학문적 표현력 우수."
        elif score >= 0.6:
            return "적절한 어휘 사용. 다양성 양호."
        elif score >= 0.4:
            return "기본적 어휘 사용. 표현력 향상 필요."
        else:
            return "제한적 어휘. 다양한 표현 연습 권장."


class SemanticConceptAnalyzer:
    """의미 유사도 기반 개념어 분석"""

    def __init__(self, use_gpu: bool = True):
        self.use_gpu = use_gpu
        self.model = None
        self.okt = None

        # 핵심 개념 카테고리
        self.concept_categories = {
            "문학적_기법": ["상징", "은유", "복선", "반전", "갈등구조", "인물형상화"],
            "사회문화적_맥락": ["신분제", "시대적배경", "계급갈등", "유교사상", "가부장제"],
            "인간관계_심리": ["사랑", "효", "충", "절개", "욕망", "갈등", "화해", "희생"],
            "주제_메시지": ["주제", "교훈", "풍자", "비판", "가치관", "이상"]
        }

        self.category_embeddings = {}
        self._init_models()

    def _init_models(self):
        """모델 초기화"""
        try:
            from konlpy.tag import Okt
            self.okt = Okt()
        except ImportError:
            pass

        try:
            from sentence_transformers import SentenceTransformer
            device = "cuda" if self.use_gpu else "cpu"
            self.model = SentenceTransformer('jhgan/ko-sroberta-multitask', device=device)

            # 카테고리별 임베딩 생성
            for cat, words in self.concept_categories.items():
                self.category_embeddings[cat] = self.model.encode(words)
        except ImportError:
            print("⚠️ sentence-transformers가 설치되지 않았습니다.")
            self.model = None

    def analyze_concepts(self, student_text: str) -> Dict:
        """의미 기반 개념어 분석"""
        # 명사 추출
        if self.okt:
            nouns = self.okt.nouns(student_text)
        else:
            nouns = student_text.split()

        if not nouns:
            return self._empty_result()

        if not self.model:
            # 모델 없으면 단순 키워드 매칭
            return self._simple_matching(nouns)

        # 후보 임베딩
        candidates = list(set(nouns))
        candidate_embeddings = self.model.encode(candidates)

        # 카테고리별 매칭
        category_matches = {}
        all_similarities = []
        threshold = 0.6

        for cat_name, cat_emb in self.category_embeddings.items():
            similarities = np.dot(candidate_embeddings, cat_emb.T)
            matches = []

            for i, cand in enumerate(candidates):
                max_sim = similarities[i].max()
                if max_sim >= threshold:
                    matched = self.concept_categories[cat_name][similarities[i].argmax()]
                    matches.append({
                        "학생표현": cand,
                        "매칭개념": matched,
                        "유사도": round(float(max_sim), 3)
                    })
                    all_similarities.append(max_sim)

            if matches:
                category_matches[cat_name] = matches

        total_matches = sum(len(m) for m in category_matches.values())
        avg_similarity = float(np.mean(all_similarities)) if all_similarities else 0
        coverage = len(category_matches)

        return {
            "카테고리별_매칭": category_matches,
            "총_개념_사용": total_matches,
            "평균_유사도": round(avg_similarity, 3),
            "커버리지": coverage,
            "평가": self._evaluate(total_matches, coverage),
            "해석": self._interpret(total_matches, coverage)
        }

    def _simple_matching(self, nouns: List[str]) -> Dict:
        """단순 키워드 매칭 (모델 없을 때)"""
        all_concepts = []
        for words in self.concept_categories.values():
            all_concepts.extend(words)

        matches = [n for n in nouns if n in all_concepts]

        return {
            "카테고리별_매칭": {},
            "총_개념_사용": len(matches),
            "평균_유사도": 1.0 if matches else 0,
            "커버리지": 0,
            "평가": "양호" if len(matches) >= 3 else "보통" if matches else "부족",
            "해석": "단순 매칭 결과 (임베딩 모델 없음)"
        }

    def _evaluate(self, total: int, coverage: int) -> str:
        if total >= 5 and coverage >= 3:
            return "우수"
        elif total >= 3 and coverage >= 2:
            return "양호"
        elif total >= 1:
            return "보통"
        else:
            return "부족"

    def _interpret(self, total: int, coverage: int) -> str:
        if total >= 5 and coverage >= 3:
            return "다양한 문학적 개념을 적절히 활용"
        elif total >= 3:
            return "핵심 개념을 부분적으로 사용"
        else:
            return "개념적 용어 사용 부족. 문학적 개념 활용 권장"

    def _empty_result(self) -> Dict:
        return {
            "카테고리별_매칭": {},
            "총_개념_사용": 0,
            "평균_유사도": 0,
            "커버리지": 0,
            "평가": "부족",
            "해석": "명사 또는 개념어 감지되지 않음"
        }


class AdvancedSentimentAnalyzer:
    """KcELECTRA 기반 감정 분석"""

    def __init__(self, use_gpu: bool = True):
        self.use_gpu = use_gpu
        self.sentiment_model = None

        # 학습 관련 키워드
        self.learning_positive = ["흥미롭", "재미있", "이해했", "공감", "인상적"]
        self.learning_negative = ["어렵", "이해안", "모르겠", "헷갈", "복잡"]
        self.learning_constructive = ["궁금", "더알고싶", "생각해볼", "탐구"]

        self._init_model()

    def _init_model(self):
        """감정 분석 모델 초기화"""
        try:
            from transformers import pipeline
            device = 0 if self.use_gpu else -1
            self.sentiment_model = pipeline(
                "sentiment-analysis",
                model="beomi/KcELECTRA-base-v2022",
                device=device
            )
        except Exception as e:
            print(f"⚠️ 감정 분석 모델 로드 실패: {e}")
            self.sentiment_model = None

    def analyze_sentiment(self, text: str) -> Dict:
        """다층적 감정 분석"""
        # 1. 전체 감정 (AI 모델)
        if self.sentiment_model:
            try:
                result = self.sentiment_model(text[:512])[0]  # 최대 512자
                overall = result['label']
                confidence = result['score']
            except Exception:
                overall, confidence = "neutral", 0.5
        else:
            overall, confidence = "neutral", 0.5

        # 2. 학습 태도
        learning_tone = self._analyze_learning_tone(text)

        # 3. 맥락 감정
        contextual = self._contextual_sentiment(text)

        # 최종 통합
        final_tone, final_score = self._integrate_sentiments(
            overall, learning_tone, contextual
        )

        return {
            "전체_감정": overall,
            "신뢰도": round(confidence, 3),
            "학습_태도": learning_tone,
            "최종_톤": final_tone,
            "점수": round(final_score, 3),
            "해석": self._interpret_tone(final_tone, learning_tone)
        }

    def _analyze_learning_tone(self, text: str) -> str:
        """학습 태도 분석"""
        pos = sum(1 for w in self.learning_positive if w in text)
        neg = sum(1 for w in self.learning_negative if w in text)
        con = sum(1 for w in self.learning_constructive if w in text)

        if con >= 2:
            return "탐구적"
        elif pos >= neg + 2:
            return "적극적"
        elif pos > neg:
            return "긍정적"
        elif neg > pos + 2:
            return "소극적"
        else:
            return "중립적"

    def _contextual_sentiment(self, text: str) -> Dict:
        """맥락 고려 감정"""
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        if not sentences or not self.sentiment_model:
            return {"평균_감정": 0}

        sent_scores = []
        for sent in sentences[:5]:  # 최대 5문장
            try:
                result = self.sentiment_model(sent)[0]
                label = 1 if 'positive' in result['label'].lower() else -1
                sent_scores.append(label * result['score'])
            except Exception:
                sent_scores.append(0)

        return {"평균_감정": round(float(np.mean(sent_scores)), 3)}

    def _integrate_sentiments(
        self, overall: str, learning: str, contextual: Dict
    ) -> Tuple[str, float]:
        """감정 통합"""
        overall_score = 0.5 if 'positive' in overall.lower() else -0.5 if 'negative' in overall.lower() else 0
        learning_scores = {
            "탐구적": 0.8, "적극적": 0.6, "긍정적": 0.4,
            "중립적": 0, "소극적": -0.4
        }
        learning_score = learning_scores.get(learning, 0)
        contextual_score = contextual.get("평균_감정", 0)

        final_score = (
            overall_score * 0.3 +
            learning_score * 0.5 +
            contextual_score * 0.2
        )

        if final_score > 0.4:
            tone = "매우긍정적"
        elif final_score > 0.1:
            tone = "긍정적"
        elif final_score > -0.1:
            tone = "중립적"
        elif final_score > -0.4:
            tone = "부정적"
        else:
            tone = "매우부정적"

        return tone, final_score

    def _interpret_tone(self, tone: str, learning: str) -> str:
        if "매우긍정" in tone and learning == "탐구적":
            return "학습 흥미와 탐구 의지 높음. 매우 우수한 학습 태도."
        elif "긍정" in tone:
            return "학습에 적극적. 긍정적 태도 유지."
        elif "부정" in tone:
            return "학습 동기 저하. 지원 필요."
        else:
            return "보통 수준의 학습 태도."


# 직접 실행 시
if __name__ == "__main__":
    # 테스트
    analyzer = ComprehensiveLanguageAnalyzer()

    test_text = """
    춘향전에서 이몽룡이 신분을 숨긴 것은 당시 조선시대의 신분제와 관련이 있다고 생각합니다.
    양반과 기생의 딸인 춘향 사이의 사랑은 계급의 벽을 넘어야 했기 때문입니다.
    이것은 작품의 중요한 주제인 신분 차별에 대한 비판을 담고 있습니다.
    """

    result = analyzer.analyze(test_text)

    print("=" * 60)
    print("📊 언어 분석 결과")
    print("=" * 60)

    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
