# QuestionGenerator : 논리 역할 우선순위, 동적 슬롯 필링, NLI 기반 피드백, 히스토리 관리 기능 포함
import re
import random
from typing import List, Dict, Optional
from .templates.question_templates import QUESTION_TEMPLATES
from .templates.feedback_templates import FEEDBACK_TEMPLATES


class QuestionGenerator:
    """
    분석된 논리 노드 정보를 기반으로 소크라테스식 질문을 생성하는 클래스.
    Phase 2에서 역할 우선순위, 슬롯 필링, 피드백 고도화, 히스토리 관리 기능이 추가됨.
    """
    _ENTITY_STOPWORDS = {
        "것", "수", "점", "데", "때", "년", "월", "일",
        "내용", "의미", "이유", "부분", "문장", "본문",
        "질문", "답변", "사람", "경우", "상황",
        "관련", "대해", "통해", "정도",
    }

    _BAD_ENTITY_PATTERNS = [
        r".*(하다|되다|이다)$",
        r"^[0-9]+$",
    ]

    # [1] Role Priority: 논리 역할 우선순위 정의
    ROLE_PRIORITY_MAP: Dict[str, int] = {
        "definition": 100,
        "claim": 90,
        "result": 80,
        "cause": 70,
        "evidence": 60,
        "contrast": 50,
        "report": 40,
        "general": 0,
    }
    MIN_CONFIDENCE_THRESHOLD: float = 0.70  # 70% 미만이면 general로 처리

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.templates = QUESTION_TEMPLATES
        self.feedback_templates = FEEDBACK_TEMPLATES

        # [4] History: 질문 중복 방지를 위한 히스토리
        self._history: List[str] = []
        self._current_node_id: Optional[str] = None

    # [1] Role Priority: 우선순위 기반 역할 추출 함수
    def get_primary_role(self, node: Dict) -> str:
        """
        node["roles"] 목록 중 가장 높은 우선순위의 역할을 반환합니다.
        roles가 비어있거나 None인 경우 'general'을 반환합니다.
        신뢰도가 MIN_CONFIDENCE_THRESHOLD 미만이면 'general'로 처리합니다.
        """
        roles = node.get("roles")

        # 예외 처리: roles가 None이거나 빈 리스트인 경우
        if not roles:
            return "general"

        # roles가 문자열 리스트인 경우 (간단한 형태)
        if isinstance(roles[0], str):
            candidate = [r for r in roles if r in self.ROLE_PRIORITY_MAP]
            if not candidate:
                return "general"
            return max(candidate, key=lambda r: self.ROLE_PRIORITY_MAP[r])

        # roles가 딕셔너리 리스트인 경우 (신뢰도 포함 형태)
        if isinstance(roles[0], dict):
            best_role, best_score = "general", 0.0
            for info in roles:
                role = info.get("role", "general")
                conf = float(info.get("confidence", 0.0))
                if conf < self.MIN_CONFIDENCE_THRESHOLD:
                    continue
                if role not in self.ROLE_PRIORITY_MAP:
                    continue
                score = self.ROLE_PRIORITY_MAP[role] * conf
                if score > best_score:
                    best_role, best_score = role, score
            return best_role

        return "general"

    # [2] Template Slot Filling: 텍스트 스니펫 및 엔티티 추출
    def _extract_snippet(self, text: str, max_length: int = 40) -> str:
        """
        텍스트에서 핵심 문구(최대 max_length자)를 추출합니다.
        단순히 앞부분만 자르는 것이 아니라, 랜덤하게 중간이나 뒷부분을 선택하여 다양성을 줍니다.
        """
        if not text:
            return "해당 내용"

        # 불필요한 공백 제거
        cleaned = " ".join(text.split())
        
        if len(cleaned) <= max_length:
            return cleaned

        # 다양성을 위해 3가지 전략 중 하나 랜덤 선택
        strategy = self.rng.choice(["start", "middle", "end"])
        
        if strategy == "start":
            return cleaned[:max_length] + "..."
            
        elif strategy == "end":
            return "..." + cleaned[-max_length:]
            
        else: # middle
            start_idx = self.rng.randint(0, len(cleaned) - max_length)
            return "..." + cleaned[start_idx : start_idx + max_length] + "..."

    def _extract_entity(self, text: str) -> str:
        """
        텍스트에서 핵심 명사(주어/목적어)를 추출합니다.
        다양한 조사 패턴을 확인하고, 매칭되는 것들 중 랜덤하게 하나를 선택합니다.
        """
        if not text:
            return "주요 대상"

        # 한글 명사구 패턴 (2글자 이상의 한글 단어 + 조사)
        patterns = [
            r"([가-힣]{2,})(은|는)\s",      # 주제격
            r"([가-힣]{2,})(이|가)\s",      # 주격
            r"([가-힣]{2,})(을|를)\s",      # 목적격
            r"([가-힣]{2,})(수|것|점|데)\s", # 의존명사 (제외 대상이지만 일단 추출 후 필터링 가능)
        ]
        
        candidates = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                w = match[0].strip()

                if w in self._ENTITY_STOPWORDS:
                    continue

                if any(re.match(p, w) for p in self._BAD_ENTITY_PATTERNS):
                    continue

                if len(w) < 2:
                    continue

                candidates.append(w)
        
        # 첫 단어도 후보에 포함 (명사일 확률 높음)
        words = text.split()
        if words:
            first_word = re.sub(r"[^가-힣]", "", words[0])
            if (
                len(first_word) >= 2
                and first_word not in self._ENTITY_STOPWORDS
                and not any(re.match(p, first_word) for p in self._BAD_ENTITY_PATTERNS)
            ):
                candidates.append(first_word)

        if candidates:
            return self.rng.choice(candidates)

        return "해당 내용"

    def _safe_format(self, template: str, slots: Dict[str, str]) -> str:
        """
        템플릿에 슬롯 값을 안전하게 삽입합니다.
        KeyError 방지를 위해 누락된 슬롯은 기본값으로 대체합니다.
        """
        defaults = {
            "snippet": "해당 내용",
            "entity": "주요 대상",
            "quote": "본문 내용",
            "keyword": "핵심 키워드",
            "question": "질문",
        }

        # 기본값과 실제 슬롯 병합
        final_slots = {**defaults, **slots}

        try:
            return template.format(**final_slots)
        except KeyError:
            # 예상치 못한 슬롯이 있는 경우 원본 반환
            return template
        except Exception:
            return template

    # [4] History Management: 중복 방지 및 히스토리 관리
    def _update_history(self, node: Dict, template_id: str) -> None:
        """생성된 질문을 히스토리에 추가합니다."""
        node_id = node.get("id")
        # id가 없으면 리셋
        if not node_id:
            self._history = []
            self._current_node_id = None
            return
        
        if node_id != self._current_node_id:
            self._history = []
            self._current_node_id = node_id

        self._history.append(template_id)

    def _get_available_templates(self, template_list: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        히스토리에 없는 사용 가능한 템플릿을 반환합니다.
        모든 템플릿이 히스토리에 있으면 히스토리를 리셋하여 다시 랜덤하게 섞이도록 합니다.
        """
        available = [t for t in template_list if t["id"] not in self._history]

        if available:
            return available

        # 모든 템플릿을 다 썼으면 히스토리 리셋 (새로운 사이클 시작)
        # 단, 현재 노드 ID는 유지해야 함
        self._history = [] 
        return template_list

    def reset_history(self) -> None:
        """히스토리를 명시적으로 초기화합니다."""
        self._history = []
        self._current_node_id = None

    # 메인 질문 생성 함수
    def generate(self, node: Dict, history: Optional[List[str]] = None) -> str:
        # Role: 우선순위 기반 역할 추출
        primary_role = self.get_primary_role(node)

        # Template 선택
        template_list = self.templates.get(primary_role, self.templates["general"])
        available = self._get_available_templates(template_list)

        chosen = self.rng.choice(available)
        template_id = chosen["id"]
        template_text = chosen["text"]

        if primary_role == "evidence":
            text = node.get("text", "") or ""
            sentence_count = len([s for s in re.split(r"[.!?]\s*", text) if s.strip()])

            is_too_short = len(text.strip()) < 80  # 임계값은 필요하면 조정
            is_single_sentence = sentence_count <= 1

            if template_id == "evidence_02" and (is_too_short or is_single_sentence):
                fallback_candidates = [t for t in available if t["id"] != "evidence_02"]
                if fallback_candidates:
                    chosen = self.rng.choice(fallback_candidates)
                    template_id = chosen["id"]
                    template_text = chosen["text"]

        text = node.get("text", "")
        slots = {
            "snippet": self._extract_snippet(text),
            "entity": self._extract_entity(text),
        }

        question = self._safe_format(template_text, slots)
        self._update_history(node, template_id)
        return question

    # [3] Feedback: NLI 라벨 기반 피드백 고도화
    def generate_feedback_question(
        self,
        evaluation: Dict,
        original_question: Optional[str] = None,
        node: Optional[Dict] = None,
    ) -> str:
        
        is_passed = evaluation.get("is_passed", False)
        nli_label = evaluation.get("nli_label", "neutral")
        user_answer = evaluation.get("user_answer", "")

        # 성공한 경우
        if is_passed:
            template = self.rng.choice(self.feedback_templates["pass"])
            return template

        # 슬롯 준비
        slots = {
            "quote": "",
            "keyword": "",
            "snippet": "",
            "question": original_question or "이전 질문",
        }

        if node:
            text = node.get("text", "")
            slots["quote"] = self._extract_snippet(text, max_length=30)
            slots["snippet"] = self._extract_snippet(text)
            slots["keyword"] = self._extract_entity(text)

        sts_score = evaluation.get("sts_score", 0.5)
        if sts_score < 0.2:
            templates = self.feedback_templates["off_topic"]
            template = self.rng.choice(templates)
            return self._safe_format(template, slots)
        
        # 답변이 너무 짧은 경우
        if user_answer and len(user_answer.strip()) < 10:
            template = self.rng.choice(self.feedback_templates["length_short"])
            return template

        # 템플릿 초기화 (기본값: neutral)
        templates = self.feedback_templates["neutral"]

        # NLI 라벨이 모순인 경우만 교체
        if nli_label == "contradiction":
            templates = self.feedback_templates["contradiction"]

        template = self.rng.choice(templates)
        return self._safe_format(template, slots)