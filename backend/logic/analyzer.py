import kss
import re
import hashlib
from typing import List, Dict

class LogicAnalyzer:
    def __init__(self):
        # 논리적 표지어 사전 고도화
        self.patterns = {
            "definition": [
                r"란 ", r"이란 ", r"정의", r"의미", r"단위", r"라 불리", r"라고 부른다"
            ],
            "claim": [
                r"해야 한다", r"함이 중요하다", r"라고 주장한다", r"로 밝혀졌다",
                r"임이 분명하다", r"할 필요가 있다", r"결론적으로", r"공통점(이|을) 갖고 있다", 
                r"주역", r"바꿨다", r"변경했다", r"없앴다", r"전망(했|했다|된다)", 
                r"평가(했|했다|된다)", r"꼽힌다", r"기여(했|했다|된다)", r"부정했다",
                r"분석(했|했다|된다)", r"풀이(했|했다|된다)", r"해석(했|했다|된다)", r"추정(했|했다|된다)"
            ],
            "report": [
                r"강조했다", r"밝혔다", r"말했다", r"전했다", r"설명했다"
            ],
            "evidence": [
                r"에 따르면", r"가 보여주듯", r"는 사실이다", r"예를 들어",
                r"실제로", r"연구에 의하면", r"라는 조사 결과",
                r"%", r"점", r"등급", r"최우수", r"우수", r"승", r"패"
            ],
            "cause": [
                r"때문에", r"로 인하여", r"의 원인은", r"가 계기가 되어",
                r"에 기인한다", r"의 배경에는"
            ],
            "result": [
                r"따라서", r"그러므로", r"결과적으로", r"이로 인해",
                r"하게 되었다", r"를 초래했다", r"결국"
            ],
            "contrast": [
                r"하지만", r"그러나", r"반면", r"이와 달리",
                r"그럼에도 불구하고", r"반대로"
            ]
        }

        self.role_priority = ["definition", "claim", "result", "cause", "evidence", "contrast", "report", "general"]

    def _should_filter_out(self, sentence: str) -> bool:
        s = sentence.strip()
        if not s:
            return True

        # 짧은 문장 하드 필터링
        if len(s) < 20 or len(s.split()) < 3:
            if re.search(r"(정의|의미|단위|란 |이란 |따라서|결론)", s):
                return False
            return True

        # 질문/대화체/감탄 등(노이즈)
        noise_patterns = [
            r"^(네|아니요|맞아요|그렇습니다|그럼요|좋아요)\.?$",
            r"^감사합니다\.?$",
            r"^\(?참고\)?",          # "참고:" "참고로" 류
            r"^요약", r"^정리",       # 메타문장
        ]
        for p in noise_patterns:
            if re.search(p, s):
                return True

        return False

    def analyze(self, text: str) -> List[Dict]:
        # 텍스트를 문장 단위로 분리하고, 각 문장의 논리적 역할과 핵심 키워드를 추출합니다.
        sentences = kss.split_sentences(text)
        total = len(sentences)

        nodes = []
        filtered_count = 0

        for i, s in enumerate(sentences):
            if self._should_filter_out(s):
                filtered_count += 1
                continue

            roles = self._detect_roles(s)
            roles = self._order_roles(roles)
            if not roles:
                roles = ["general"]
            if roles == ["general"] and self._is_low_info_general(s):
                continue


            primary = self._primary_role(roles, s)
            keywords = self._extract_keywords(s)

            # 후보만 score 계산
            score = self._score_sentence(s, roles, i, total)
            
            normalized = re.sub(r"\s+", " ", s).strip()
            node_id = hashlib.sha1(f"{i}:{normalized}".encode("utf-8")).hexdigest()[:12]
            
            nodes.append({
                "id": node_id,
                "index": i,
                "text": s,
                "roles": roles,
                "type": primary,
                "keywords": keywords,
                "score": score,
                "is_key_node": False
            })

        # 후보가 0이면 그대로 반환
        if not nodes:
            return []

        # Stage 2: Top-K 선택(다양성)
        key_ids = self._select_topk_with_diversity(nodes, K=3)

        for n in nodes:
            if n["id"] in key_ids:
                n["is_key_node"] = True

        return nodes
    
    def _is_low_info_general(self, sentence: str) -> bool:
        return not re.search(r"(\d|%|하지만|그러나|때문에|따라서|결론|정의|의미|즉|요컨대|결국|다시 말해)", sentence)

    
    def _select_topk_with_diversity(self, nodes: List[Dict], K: int = 3) -> set[str]:
        # 점수 높은 순
        ranked = sorted(nodes, key=lambda x: x["score"], reverse=True)

        selected = []
        type_count = {}

        def can_take(n: Dict) -> bool:
            t = n.get("type", "general")
            # 같은 타입 최대 2개
            return type_count.get(t, 0) < 2

        # 1) definition/claim 중 하나를 먼저 확보(가능하면)
        priority_anchor = None
        for n in ranked:
            if n.get("type") in ("definition", "claim"):
                if can_take(n):
                    priority_anchor = n
                    break

        if priority_anchor:
            selected.append(priority_anchor)
            t = priority_anchor["type"]
            type_count[t] = type_count.get(t, 0) + 1

        # 2) 나머지 K개를 score 순으로 채우되 타입 제한
        for n in ranked:
            if len(selected) >= K:
                break
            if n in selected:
                continue
            if not can_take(n):
                continue
            selected.append(n)
            t = n.get("type", "general")
            type_count[t] = type_count.get(t, 0) + 1

        # 3) 그래도 부족하면(타입 제한 때문에) 제한 무시하고 채움
        if len(selected) < K:
            for n in ranked:
                if len(selected) >= K:
                    break
                if n in selected:
                    continue
                selected.append(n)

        return {n["id"] for n in selected}
    
    def _detect_roles(self, sentence: str) -> List[str]:
        roles = set()
        for role, pats in self.patterns.items():
            for p in pats:
                if re.search(p, sentence):
                    roles.add(role)
                    break
        return list(roles)
    
    def _primary_role(self, roles: List[str], sentence: str) -> str:
        # roles가 비었으면 general
        if not roles:
            roles = ["general"]

        ordered = self._order_roles(roles)
        if not ordered:
            return "general"

        # definition 과검출 완화
        if ordered[0] == "definition":
            if re.search(r"(란 |이란 |정의|의미|단위|라고 부른다|라 불리)", sentence):
                return "definition"
            # 단순 "이다"만으로 definition 된 케이스는 다음 우선순위로
            for r in ordered[1:]:
                return r
            return "general"

        return ordered[0]
    
    def _order_roles(self, roles: list[str]) -> list[str]:
        return [r for r in self.role_priority if r in roles]
    
    def _extract_keywords(self, sentence: str) -> List[str]:
        # TODO: KoNLPy 또는 Transformers 기반 키워드 추출 도입 가능
        # 현재는 명사성 간단 추출 (가이드라인 수준)
        words = sentence.split()
        return [w for w in words if len(w) > 1][:5]

    def _score_sentence(self, sentence: str, roles: List[str], index: int, total: int) -> float:
        score = 0.0

        # 1. role 기반 가중치
        role_weight = {
            "definition": 3.0,
            "claim": 3.0,
            "result": 3.0,
            "cause": 2.0,
            "evidence": 1.5,
            "contrast": 1.0,
            "general": 0.5
        }
        primary = self._primary_role(roles, sentence)
        
        score += role_weight.get(primary, 0.5)
        
        # report가 점수로 과대평가 된다면 제외하기
        # secondary = [r for r in roles if r != primary and r != "report"]
        secondary = [r for r in roles if r != primary]
        score += 0.3 * len(secondary)

        # 정의 / 분류 패턴 가산 (서사·설명 텍스트 대응)
        if primary == "definition" and re.search(r"(란 |이란 |정의|의미|단위|라고 부른다|라 불리)", sentence):
            score += 0.7

        # 숫자가 많으면 통계/기록 문장일 확률↑
        digit_cnt = len(re.findall(r"\d", sentence))
        has_unit = bool(re.search(r"(%|점|등급|승|패|명|원|만원|억|배|년|월|일)", sentence))
        if digit_cnt >= 2 and has_unit:
            score += 0.3
        if digit_cnt >= 6 and has_unit:
            score += 0.3

        # 3. 고유명사/용어 느낌 (따옴표)
        if "‘" in sentence or "’" in sentence or "'" in sentence:
            score += 1.0

        # 4. 첫/마지막 문장 약한 보너스 (강제 X)
        if index == 0 or index == total - 1:
            score += 0.5
        
        if re.search(r"(말했|밝혔|전했|설명했)", sentence):
            score += 0.2
        if re.search(r"(주장했|강조했|부정했)", sentence) and primary in ("claim", "result"):
            score += 0.4


        return score
