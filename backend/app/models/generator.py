"""
QuestionGenerator - Phase 2 고도화 버전 (개선판)
논리 역할 우선순위, 동적 슬롯 필링, NLI 기반 피드백, 히스토리 관리 기능 포함
개선사항: 버그 수정, 로깅, 테스트 가능성, 코드 간결화
"""
import re
import random
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class QuestionGenerator:
    """
    분석된 논리 노드 정보를 기반으로 소크라테스식 질문을 생성하는 클래스.
    Phase 2: 역할 우선순위, 슬롯 필링, 피드백 고도화, 히스토리 관리
    """

    # =====================================================================
    # 클래스 상수
    # =====================================================================
    ROLE_PRIORITY_MAP: Dict[str, int] = {
        "claim": 100,
        "cause": 90,
        "result": 80,
        "evidence": 70,
        "contrast": 60,
        "general": 0,
    }
    MIN_CONFIDENCE_THRESHOLD: float = 0.70
    SMOOTHING_FACTOR: int = 10  # 낮은 우선순위도 최소 확률 보장
    
    # 불용어 리스트 (엔티티 추출 시 제외)
    STOPWORDS = {
        "그것", "이것", "저것", "무엇", "누구", "어디",  # 대명사
        "것", "수", "점", "데", "때", "바",  # 의존명사
        "하는", "있는", "되는", "만한", "할수",  # 형식명사
        "이런", "저런", "그런", "어떤"  # 지시사
    }

    def __init__(self, seed: Optional[int] = None):
        """
        Args:
            seed: 난수 시드 (테스트 시 재현성 보장, None이면 랜덤)
        """
        # 랜덤 시드 설정
        self._rng = random.Random(seed) if seed is not None else random.Random()
        
        # 템플릿 정의 (원본 유지)
        self.templates: Dict[str, List[str]] = {
            "claim": [
                "'{snippet}'에서 강조하고자 하는 핵심 주장은 무엇인가요?",
                "제시된 근거에서 이 주장('{snippet}')으로 나아가기 위해, 필자는 어떤 논리를 사용하고 있나요?",
                "어떤 상황에서 '{snippet}'(이)라는 주장이 성립하지 않을 수 있을까요?",
                "지금까지의 논리를 한 문장으로 표현해 볼까요?",
                "'{snippet}'라고 주장하는 이면에 깔린 의도는 무엇일까요?",
                "이 주장('{snippet}')을 우리 현실 문제에 적용한다면 어떤 사례를 들 수 있을까요?",
            ],
            "evidence": [
                "본문에서 '{entity}'(은)는 무엇이라고 명시되어 있나요?",
                "본문의 정확히 어느 문장이 '{snippet}' 내용을 뒷받침하나요?",
                "저자가 제시한 '{entity}' 관련 근거가 주장을 뒷받침하기에 충분히 객관적인가요?",
                "이 근거('{snippet}') 말고도 주장을 강화하기 위해 더 필요한 정보가 있다면 무엇일까요?",
                "혹시 이 근거('{snippet}')를 다른 방식으로 해석할 여지는 없을까요?",
            ],
            "cause": [
                "본문의 여러 부분을 종합해 볼 때, '{snippet}' 현상이 발생한 복합적인 원인은 무엇인가요?",
                "'{entity}' 원인과 관련하여, 텍스트에서 발견한 사실과 당신의 해석을 구분해서 설명해 줄 수 있나요?",
                "이러한 배경이 결과적으로 '{snippet}'에 어떤 영향을 미쳤는지 논리적으로 연결해 볼까요?",
                "직접적인 원인 외에, '{snippet}' 현상을 초래한 근본적인(사회적/구조적) 배경은 무엇일까요?",
                "이 원인('{snippet}')과 결과가 필연적인가요, 아니면 우연적인 요소도 있나요?",
            ],
            "result": [
                "사용자님의 해석대로라면, '{snippet}' 이후에 어떤 내용이 이어져야 논리적으로 타당할까요?",
                "'{entity}'(으)로 인한 결과를 바탕으로, 저자가 다음 단락에서 어떤 논리를 펼칠 것이라 예상하나요?",
                "만약 이 결과('{snippet}')가 발생하지 않았다면, 상황은 어떻게 달라졌을까요?",
                "이 결과와 관련하여 더 궁금한 점은 무엇인가요?",
                "이 결과('{snippet}')가 긍정적인 측면만 있을까요? 혹시 부정적인 부작용은 없을까요?",
                "이 결과('{snippet}')를 통해 저자가 최종적으로 전달하려는 메시지는 무엇일까요?",
            ],
            "contrast": [
                "필자가 '{entity}'을(를) 대비시키며 강조하고자 하는 논리적 차이점은 무엇인가요?",
                "이 대조 논리에서 놓치고 있는 예외 상황이나 허점은 없을까요?",
                "'{entity}'와(과) 비교할 때 가장 두드러지는 차이점은 무엇인가요?",
                "두 입장('{entity}') 사이에서 중재안을 찾는다면 어떤 결론을 내릴 수 있을까요?",
                "이 대조('{snippet}')를 통해 필자가 부각하고 싶은 핵심 가치는 무엇인가요?",
            ],
            "general": [
                "저자가 말한 '{snippet}' 개념을 당신의 실제 경험에 비추어 설명해 본다면?",
                "이 글의 주제와 관련하여, 당신이라면 '{entity}' 문제에 대해 어떤 해결책을 제시하겠나요?",
                "'{snippet}' 문장에서 무엇이 보이고, 그것이 무엇을 의미한다고 생각하시나요?",
                "이 문단이 전체 주장 중 어떤 논리적 단계를 담당하고 있나요?",
                "만약 '{snippet}' 내용에 반대하는 사람이 있다면, 어떤 근거를 들 수 있을까요?",
                "'{snippet}' 상황이 우리 사회(혹은 주변)에 직접 적용된다면 어떤 변화가 생길까요?",
            ],
        }

        # 피드백 템플릿
        self.feedback_templates: Dict[str, List[str]] = {
            "contradiction": [
                "잠시만요, 본문에는 '{quote}'라고 명시되어 있습니다. 답변하신 내용과 비교해 보시겠어요?",
                "논의가 조금 엇갈리는 것 같아요. 텍스트의 '{snippet}' 부분을 다시 읽어보면 어떨까요?",
                "'{quote}'라는 본문의 내용과 사용자님의 답변이 충돌하고 있어요. 이 차이를 좁혀볼까요?",
                "답변의 논리는 이해하지만, 본문의 '{snippet}' 내용과 상충되는 면이 있습니다. 다시 확인해 주세요.",
            ],
            "neutral": [
                "좋은 방향이에요! 하지만 '{keyword}' 부분에 대한 언급이 빠진 것 같아요. 조금 더 보완해 주시겠어요?",
                "핵심을 거의 짚으셨어요. '{keyword}'에 대해 좀 더 자세히 설명해 주실 수 있나요?",
                "좋은 시도예요. 다만 '{keyword}'에 대한 설명이 조금 부족해 보여요. 이 부분을 보강하면 완벽할 것 같아요.",
                "전반적인 맥락은 맞습니다. 하지만 필자가 말하는 '{keyword}'의 진짜 의미를 좀 더 파고들어 볼까요?",
            ],
            "missing_point": [
                "거의 다 왔는데, '{missed}'에 대한 내용이 빠졌네요. 이 부분을 포함해서 다시 답변해 주시겠어요?",
                "전반적으로 좋지만 '{missed}'라는 핵심 포인트를 놓치신 것 같아요. 다시 한번 생각해 볼까요?",
                "아주 중요한 내용인 '{missed}' 부분이 답변에 포함되지 않았습니다. 보완해 주세요!",
                "설명이 조금 더 구체적이어야 해요. 특히 '{missed}'에 대해 말씀해 주시면 좋을 것 같아요.",
            ],
            "length_short": [
                "답변이 조금 짧은 것 같아요. 왜 그렇게 생각하시는지 이유도 함께 설명해 주세요.",
                "좀 더 구체적으로 말씀해 주실 수 있나요?",
                "추가 설명을 덧붙여서 논리적 근거를 보강해 주세요.",
                "조금 더 자세히 설명해 주시면 좋을 것 같아요. 왜 그렇게 생각하셨나요?",
            ],
            "off_topic": [
                "질문과 조금 다른 방향으로 가신 것 같아요. 다시 한번, '{question}'에 대해 생각해 볼까요?",
                "원래 질문으로 돌아가 볼게요: {question}",
                "흥미로운 이야기지만, 지금은 '{question}'에 집중해 볼까요?",
                "잠시 길을 잃은 것 같아요. 본문의 '{snippet}' 내용으로 다시 돌아와 봅시다.",
                "본문의 맥락에서 '{question}'에 대한 답을 찾아보는 건 어떨까요?",
            ],
            "pass": [
                "완벽합니다! 다음 단계로 넘어가 볼까요?",
                "정확하게 이해하고 계시네요! 다음 내용으로 진행해 볼까요?",
                "훌륭해요! 핵심을 완벽히 파악하셨습니다. 계속해 볼까요?",
                "대단해요! 이 부분은 완전히 이해하셨군요.",
                "브라보! 정확한 근거를 바탕으로 논리정연하게 답변하셨네요.",
                "완벽해요! 저자의 의도를 정확히 꿰뚫어 보셨습니다.",
                "더할 나위 없는 답변입니다. 내용을 완전히 자신의 것으로 만드셨군요.",
                "훌륭합니다! 논리적 흐름을 아주 잘 따라오고 계세요.",
            ],
        }

        # 히스토리 관리
        self._history: List[str] = []
        self._current_node_id: Optional[str] = None

    # =========================================================================
    # 역할 추출
    # =========================================================================
    def get_primary_role(self, node: Dict) -> str:
        """node["roles"]에서 우선순위 기반으로 역할 반환"""
        if not isinstance(node, dict):
            logger.warning(f"노드가 딕셔너리가 아님: {type(node)}")
            return "general"
        
        roles = node.get("roles")
        if not roles or not isinstance(roles, list) or len(roles) == 0:
            return "general"

        # 문자열 리스트
        if isinstance(roles[0], str):
            candidates = [r for r in roles if r in self.ROLE_PRIORITY_MAP]
            if not candidates:
                return "general"
            weights = [self.ROLE_PRIORITY_MAP.get(r, 0) + self.SMOOTHING_FACTOR for r in candidates]
            return self._rng.choices(candidates, weights=weights, k=1)[0]

        # 딕셔너리 리스트 (신뢰도 포함)
        if isinstance(roles[0], dict):
            candidates, weights = [], []
            for role_info in roles:
                if role_info.get("confidence", 0.0) >= self.MIN_CONFIDENCE_THRESHOLD:
                    role_name = role_info.get("role", "general")
                    priority = self.ROLE_PRIORITY_MAP.get(role_name, 0)
                    candidates.append(role_name)
                    weights.append(priority * role_info.get("confidence", 0.0) * 100)
            if candidates:
                return self._rng.choices(candidates, weights=weights, k=1)[0]

        return "general"

    # =========================================================================
    # 슬롯 추출
    # =========================================================================
    def _extract_snippet(self, text: str, max_length: int = 40) -> str:
        """텍스트에서 핵심 문구 추출 (가중치 기반 랜덤)"""
        if not text:
            return "해당 내용"

        cleaned = " ".join(text.split())
        if len(cleaned) <= max_length:
            return cleaned

        # 가중치: start 70%, middle 10%, end 20%
        strategy = self._rng.choices(["start", "middle", "end"], weights=[70, 10, 20], k=1)[0]
        
        if strategy == "start":
            return cleaned[:max_length] + "..."
        elif strategy == "end":
            return "..." + cleaned[-max_length:]
        else:  # middle
            start_idx = self._rng.randint(0, len(cleaned) - max_length)
            return "..." + cleaned[start_idx:start_idx + max_length] + "..."

    def _extract_entity(self, text: str) -> str:
        """텍스트에서 핵심 명사 추출 (불용어 제외, 복합명사 우선)"""
        if not text:
            return "주요 대상"

        # 1단계: 복합명사 우선 추출
        compound = re.findall(r'([가-힣]{2,}\s[가-힣]{2,})(은|는|이|가|을|를)', text)
        compound_candidates = [m[0].strip() for m in compound if m[0].strip() not in self.STOPWORDS]
        if compound_candidates:
            return self._rng.choice(compound_candidates)

        # 2단계: 단일 명사 추출
        patterns = [r"([가-힣]{2,})(은|는)\s", r"([가-힣]{2,})(이|가)\s", r"([가-힣]{2,})(을|를)\s"]
        candidates = []
        for pattern in patterns:
            candidates.extend([m[0] for m in re.findall(pattern, text) if m[0] not in self.STOPWORDS])
        
        # 3단계: 첫 단어 후보
        words = text.split()
        if words:
            first = re.sub(r"[^가-힣]", "", words[0])
            if len(first) >= 2 and first not in self.STOPWORDS:
                candidates.append(first)

        return self._rng.choice(candidates) if candidates else "주요 대상"

    def _safe_format(self, template: str, slots: Dict[str, str]) -> str:
        """템플릿 슬롯 안전 삽입 (로깅 포함)"""
        defaults = {"snippet": "해당 내용", "entity": "주요 대상", "quote": "본문 내용", 
                    "keyword": "핵심 키워드", "question": "질문", "missed": "중요 내용"}
        final_slots = {**defaults, **slots}

        try:
            return template.format(**final_slots)
        except KeyError as e:
            logger.warning(f"템플릿 슬롯 누락: {e}. Template: {template[:50]}...")
            return template
        except Exception as e:
            logger.error(f"템플릿 포맷 실패: {type(e).__name__}: {e}")
            return template

    # =========================================================================
    # 히스토리 관리
    # =========================================================================
    def _update_history(self, node: Dict, template: str) -> None:
        """히스토리에 템플릿 추가 (노드 변경 시 리셋)"""
        node_id = node.get("id") or node.get("text", "")[:50]
        if node_id != self._current_node_id:
            self._history = []
            self._current_node_id = node_id
        self._history.append(template)

    def _get_available_templates(self, template_list: List[str]) -> List[str]:
        """사용 가능한 템플릿 반환 (모두 사용 시 리셋)"""
        available = [t for t in template_list if t not in self._history]
        if available:
            return available
        self._history = []
        return template_list

    def reset_history(self) -> None:
        """히스토리 초기화"""
        self._history = []
        self._current_node_id = None

    # =========================================================================
    # 메인 질문 생성
    # =========================================================================
    def generate(self, node: Dict) -> str:
        """
        소크라테스식 질문 생성
        
        Args:
            node: 분석된 노드 정보 (text, roles 포함)
        
        Returns:
            생성된 질문 문자열
        """
        # 입력 검증
        if "text" not in node or not isinstance(node.get("text"), str):
            logger.error(f"노드 text 누락 또는 잘못된 타입: {node}")
            return "이 부분에 대해 어떻게 생각하시나요?"

        # 역할 추출
        role = self.get_primary_role(node)
        template_list = self.templates.get(role, self.templates["general"])
        
        # 템플릿 선택
        available = self._get_available_templates(template_list)
        template = self._rng.choice(available)
        
        # 슬롯 채우기
        text = node["text"]
        slots = {"snippet": self._extract_snippet(text), "entity": self._extract_entity(text)}
        question = self._safe_format(template, slots)
        
        # 히스토리 업데이트
        self._update_history(node, template)
        
        return question

    def _is_gibberish(self, text: str) -> bool:
        """무의미한 반복 문자나 자음/모음만 있는 경우 감지"""
        if not text:
            return False
            
        # 1. 같은 문자 4번 이상 반복 (예: ddddd, ㅋㅋㅋㅋ, ....)
        if re.search(r'(.)\1{3,}', text):
            return True
            
        # 2. 자음/모음으로만 구성 (예: ㅎㅎㅎ, ㅜㅜ)
        if re.match(r'^[ㄱ-ㅎㅏ-ㅣ\s?!.]+$', text):
            return True
            
        return False

    # =========================================================================
    # 피드백 생성
    # =========================================================================
    def generate_feedback_question(self, evaluation: Dict, original_question: Optional[str] = None,
                                   node: Optional[Dict] = None) -> str:
        """NLI 기반 피드백 생성 (Evaluator 결과 연동 강화)"""
        user_answer = evaluation.get("user_answer", "")

        # 슬롯 준비 (미리 준비하여 off_topic 등에서도 사용)
        slots = {"quote": "", "keyword": "", "snippet": "", "question": original_question or "이전 질문", "missed": ""}
        if node:
            text = node.get("text", "")
            slots.update({"quote": self._extract_snippet(text, 30), 
                         "snippet": self._extract_snippet(text),
                         "keyword": self._extract_entity(text)})

        # 1. 무의미한 텍스트(Gibberish) 체크 -> off_topic 처리
        if self._is_gibberish(user_answer):
            return self._safe_format(self._rng.choice(self.feedback_templates["off_topic"]), slots)

        # 2. 글자 수 우선 체크 (3글자 이하일 때 length_short 템플릿)
        if user_answer and len(user_answer.strip()) <= 3:
            return self._rng.choice(self.feedback_templates["length_short"])

        if evaluation.get("is_passed", False):
            return self._rng.choice(self.feedback_templates["pass"])

        # 3. 상세 피드백 분석 (Evaluator의 feedback 메시지 활용)
        # Evaluator가 "가장 중요한 지점('...')..." 형태의 피드백을 보냈다면 이를 파싱하여 활용
        raw_feedback = evaluation.get("feedback", "")
        missed_match = re.search(r"'(.*?)'", raw_feedback) # 작은따옴표 안의 내용을 추출
        
        if missed_match and "중요한 지점" in raw_feedback:
            slots["missed"] = missed_match.group(1)
            # 놓친 내용이 있다면 'missing_point' 템플릿 우선 사용
            return self._safe_format(self._rng.choice(self.feedback_templates["missing_point"]), slots)

        # 4. 템플릿 선택
        nli = evaluation.get("nli_label", "neutral")
        sts = evaluation.get("sts_score", 0.5)
        
        if sts < 0.2:
            templates = self.feedback_templates["off_topic"]
        elif nli == "contradiction":
            templates = self.feedback_templates["contradiction"]
        else:
            templates = self.feedback_templates["neutral"]

        return self._safe_format(self._rng.choice(templates), slots)
