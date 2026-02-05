"""
데이터 전처리 모듈
AI HUB 데이터를 학습 가능한 형태로 변환
"""

import json
import os
import zipfile
from pathlib import Path
from typing import List, Dict, Any, Iterable, Union
from tqdm import tqdm


class DataPreprocessor:
    """AI HUB 데이터 전처리 클래스"""

    def __init__(self, config_path: str = "configs/training_config.yaml"):
        """
        Args:
            config_path: 설정 파일 경로
        """
        self.config = self._load_config(config_path)

        self.raw_classics_path = self.config.get("data", {}).get("raw_classics_path", "")
        self.raw_comprehension_path = self.config.get("data", {}).get("raw_comprehension_path", "")
        self.raw_evaluation_path = self.config.get("data", {}).get("raw_evaluation_path", "")

        self.output_dir = Path("data/processed")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _load_config(self, config_path: str) -> Dict:
        """설정 파일 로드"""
        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Config file not found: {config_path}")
            return {}
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}

    def _normalize_paths(self, raw_path: Union[str, List[str]]) -> List[Path]:
        """문자열/리스트 경로를 Path 리스트로 정규화"""
        if isinstance(raw_path, list):
            items = raw_path
        elif isinstance(raw_path, str) and raw_path.strip():
            items = [raw_path]
        else:
            return []

        resolved = []
        for item in items:
            if not isinstance(item, str) or not item.strip():
                continue
            p = Path(os.path.expanduser(os.path.expandvars(item.strip())))
            resolved.append(p)
        return resolved

    def _iter_records_from_json_bytes(self, raw_bytes: bytes) -> List[Dict]:
        """JSON bytes를 dict 레코드 리스트로 변환"""
        text = None
        for enc in ("utf-8", "utf-8-sig", "cp949", "euc-kr"):
            try:
                text = raw_bytes.decode(enc)
                break
            except Exception:
                continue
        if text is None:
            return []
        try:
            obj = json.loads(text)
        except Exception:
            return []
        return self._flatten_json_records(obj)

    def _iter_json_records_in_path(self, path: Path) -> Iterable[Dict]:
        """경로(파일/폴더) 내부의 json/jsonl/zip 레코드를 순회"""
        if not path.exists():
            return

        if path.is_file():
            files = [path]
        else:
            files = sorted(p for p in path.rglob("*") if p.is_file())

        for file_path in files:
            suffix = file_path.suffix.lower()
            try:
                if suffix == ".jsonl":
                    with open(file_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                obj = json.loads(line)
                            except Exception:
                                continue
                            if isinstance(obj, dict):
                                yield obj
                elif suffix == ".json":
                    with open(file_path, "rb") as f:
                        for rec in self._iter_records_from_json_bytes(f.read()):
                            yield rec
                elif suffix == ".zip":
                    with zipfile.ZipFile(file_path) as zf:
                        members = [m for m in zf.namelist() if m.lower().endswith(".json")]
                        for member in members:
                            try:
                                raw = zf.read(member)
                            except Exception:
                                continue
                            for rec in self._iter_records_from_json_bytes(raw):
                                yield rec
            except Exception as e:
                print(f"⚠️ 파일 로드 실패 ({file_path}): {e}")

    def load_classics_data(self) -> List[Dict]:
        """
        고전문학 600개 데이터 로드

        TODO: 실제 AI HUB 데이터 구조에 맞게 수정 필요

        Returns:
            List[Dict]: 고전문학 데이터 리스트
            예상 구조:
            {
                "id": "classic_001",
                "source": "춘향전",
                "passage": "지문 내용...",
                "question": "질문...",
                "answer": "모범 답안..."
            }
        """
        paths = self._normalize_paths(self.raw_classics_path)
        if not paths:
            print("⚠️ 고전문학 데이터 경로가 설정되지 않았습니다.")
            print("   configs/training_config.yaml의 data.raw_classics_path를 설정해주세요.")
            return []

        loaded_data: List[Dict] = []
        for path in paths:
            if not path.exists():
                print(f"⚠️ 경로를 찾을 수 없습니다: {path}")
                continue
            for raw_item in tqdm(self._iter_json_records_in_path(path), desc=f"고전문학 로딩 ({path.name})"):
                parsed = self.parse_classic_text(raw_item)
                if parsed.get("passage"):
                    parsed["dataset"] = "classics"
                    loaded_data.append(parsed)

        print(f"📂 데이터 경로: {', '.join(str(p) for p in paths)}")
        print(f"✅ 고전문학 데이터 로드 완료: {len(loaded_data)}개")
        return loaded_data

    def _flatten_json_records(self, obj: Any) -> List[Dict]:
        """JSON 객체를 레코드 리스트로 평탄화"""
        if isinstance(obj, list):
            return [x for x in obj if isinstance(x, dict)]

        if isinstance(obj, dict):
            candidate_keys = ["data", "items", "records", "dataset", "documents", "annotations"]
            for key in candidate_keys:
                value = obj.get(key)
                if isinstance(value, list):
                    return [x for x in value if isinstance(x, dict)]
            return [obj]

        return []

    def load_comprehension_data(self) -> List[Dict]:
        """
        국어 교과 지문형 문제 데이터 로드 (1.26GB)

        TODO: 실제 AI HUB 데이터 구조에 맞게 수정 필요

        Returns:
            List[Dict]: 지문형 문제 데이터 리스트
        """
        paths = self._normalize_paths(self.raw_comprehension_path)
        if not paths:
            print("⚠️ 지문형 문제 데이터 경로가 설정되지 않았습니다.")
            return []

        loaded_data: List[Dict] = []
        for path in paths:
            if not path.exists():
                print(f"⚠️ 경로를 찾을 수 없습니다: {path}")
                continue

            for raw_item in tqdm(self._iter_json_records_in_path(path), desc=f"지문형 로딩 ({path.name})"):
                parsed = self.parse_comprehension_item(raw_item)
                if parsed:
                    loaded_data.append(parsed)

        print(f"📂 데이터 경로: {', '.join(str(p) for p in paths)}")
        print(f"✅ 지문형 문제 데이터 로드 완료: {len(loaded_data)}개")
        return loaded_data

    def load_evaluation_data(self) -> List[Dict]:
        """
        논술형/서술형 평가 데이터 로드 (232MB)

        TODO: 실제 AI HUB 데이터 구조에 맞게 수정 필요

        Returns:
            List[Dict]: 평가 데이터 리스트
        """
        paths = self._normalize_paths(self.raw_evaluation_path)
        if not paths:
            print("⚠️ 평가 데이터 경로가 설정되지 않았습니다.")
            return []

        loaded_data: List[Dict] = []
        for path in paths:
            if not path.exists():
                print(f"⚠️ 경로를 찾을 수 없습니다: {path}")
                continue

            for raw_item in tqdm(self._iter_json_records_in_path(path), desc=f"평가데이터 로딩 ({path.name})"):
                parsed = self.parse_evaluation_item(raw_item)
                if parsed:
                    loaded_data.append(parsed)

        print(f"📂 데이터 경로: {', '.join(str(p) for p in paths)}")
        print(f"✅ 평가 데이터 로드 완료: {len(loaded_data)}개")
        return loaded_data

    def parse_classic_text(self, raw_data: Dict) -> Dict:
        """
        고전문학 원본 데이터 파싱

        TODO: AI HUB 데이터 구조에 맞게 수정 필요

        Args:
            raw_data: 원본 데이터

        Returns:
            Dict: 파싱된 데이터
            {
                "id": str,
                "source": str,  # 작품명
                "passage": str,  # 지문
                "question": str,  # 질문
                "answer": str  # 모범 답안
            }
        """
        metadata = raw_data.get("metadata", {}) if isinstance(raw_data.get("metadata"), dict) else {}

        def pick_first(keys: List[str], default: str = "") -> str:
            for key in keys:
                value = raw_data.get(key)
                if value is None:
                    continue
                if isinstance(value, list):
                    value = " ".join(str(v) for v in value if v is not None)
                value = str(value).strip()
                if value:
                    return value
            return default

        source = (
            pick_first(["source", "작품명", "work_title", "title"])
            or str(metadata.get("title", "")).strip()
            or "고전문학"
        )
        passage = (
            pick_first(["passage", "지문", "text", "content", "본문"])
            or str(raw_data.get("문제지문", "")).strip()
        )
        question = pick_first(["question", "질문", "문항", "query", "prompt"])
        answer = pick_first(["answer", "정답", "해설", "모범답안", "explanation"])

        if not question:
            question = f"{source}의 핵심 주제와 화자의 태도를 설명해 보세요."
        if not answer:
            answer = (
                "작품의 핵심 소재와 표현 방식을 근거로 주제 의식을 설명하고, "
                "화자의 정서 변화와 시대적 맥락을 함께 해석해 보세요."
            )

        data_id = (
            pick_first(["id", "data_id"])
            or str(metadata.get("data_id", "")).strip()
            or f"item_{abs(hash((source, passage[:120]))) % 10**10}"
        )

        return {
            "id": data_id,
            "source": source,
            "passage": passage,
            "question": question,
            "answer": answer
        }

    def parse_comprehension_item(self, raw_data: Dict) -> Dict:
        """국어 교과 지문형 문제 데이터 파싱"""
        if not isinstance(raw_data, dict):
            return {}
        if "learning_data_info" not in raw_data:
            return {}

        class_map: Dict[str, List[str]] = {}
        for block in raw_data.get("learning_data_info", []):
            class_name = str(block.get("class_name", "")).strip()
            if not class_name:
                continue
            texts: List[str] = []
            for info in block.get("class_info_list", []):
                txt = str(info.get("text_description", "")).strip()
                if txt:
                    texts.append(txt)
            if texts:
                class_map.setdefault(class_name, []).extend(texts)

        passage_texts = class_map.get("지문", []) + class_map.get("지문(이미지)", [])
        question_texts = class_map.get("문항", [])
        answer_texts = class_map.get("정답", []) + class_map.get("해설", [])

        passage = "\n".join(passage_texts).strip()
        question = "\n".join(question_texts).strip()
        answer = "\n".join(answer_texts).strip()

        if not (passage and question and answer):
            return {}

        raw_info = raw_data.get("raw_data_info", {})
        src_info = raw_data.get("source_data_info", {})
        source_name = str(src_info.get("source_data_name", "")).strip()
        school = str(raw_info.get("school", "")).strip()
        grade = str(raw_info.get("grade", "")).strip()
        subject = str(raw_info.get("subject", "")).strip()
        source = " / ".join(x for x in [school, grade, subject, source_name] if x)

        return {
            "id": source_name or f"comp_{abs(hash((question[:80], passage[:80]))) % 10**10}",
            "source": source or "국어 교과 지문형 문제",
            "passage": passage,
            "question": question,
            "answer": answer,
            "dataset": "comprehension"
        }

    def parse_evaluation_item(self, raw_data: Dict) -> Dict:
        """논술형/서술형 평가 데이터 파싱"""
        if not isinstance(raw_data, dict):
            return {}
        if "essay_question" not in raw_data or "essay_answer" not in raw_data:
            return {}

        question_obj = raw_data.get("essay_question", {})
        answer_obj = raw_data.get("essay_answer", {})
        rubric_obj = raw_data.get("rubric", {})

        prompt = str(question_obj.get("prompt", "")).strip()
        answer_text = str(answer_obj.get("text", "")).strip()
        topic = str(question_obj.get("topic", "")).strip()
        qtype = str(question_obj.get("type", "")).strip()
        grade = str(question_obj.get("grade", "")).strip()
        subject = str(question_obj.get("subject", "")).strip()
        keyword = question_obj.get("keyword", [])
        if isinstance(keyword, list):
            keyword_text = ", ".join(str(k).strip() for k in keyword if str(k).strip())
        else:
            keyword_text = str(keyword).strip()

        if not (prompt and answer_text):
            return {}

        passage_parts = [f"주제: {topic}" if topic else "", prompt]
        if keyword_text:
            passage_parts.append(f"핵심어: {keyword_text}")
        achievement = str(rubric_obj.get("achievement", "")).strip()
        if achievement:
            passage_parts.append(f"평가기준: {achievement}")
        passage = "\n".join(x for x in passage_parts if x).strip()

        qid = str(question_obj.get("id", "")).strip()
        aid = str(answer_obj.get("id", "")).strip()
        source = " / ".join(x for x in [qtype, grade, subject] if x)

        return {
            "id": f"{qid}_{aid}" if (qid or aid) else f"eval_{abs(hash((prompt[:80], answer_text[:80]))) % 10**10}",
            "source": source or "논술/서술형 평가",
            "passage": passage,
            "question": prompt,
            "answer": answer_text,
            "dataset": "evaluation"
        }

    def filter_quality_data(
        self,
        data: List[Dict],
        min_passage_length: int = 50,
        min_answer_length: int = 20
    ) -> List[Dict]:
        """
        저품질 데이터 필터링

        Args:
            data: 원본 데이터 리스트
            min_passage_length: 최소 지문 길이
            min_answer_length: 최소 답변 길이

        Returns:
            List[Dict]: 필터링된 데이터
        """
        filtered = []

        for item in data:
            passage = item.get("passage", "")
            answer = item.get("answer", "")
            question = item.get("question", "")

            # 기본 품질 검증
            if len(passage) < min_passage_length:
                continue
            if len(answer) < min_answer_length:
                continue
            if not question.strip():
                continue

            filtered.append(item)

        if data:
            ratio = len(filtered) / len(data) * 100
            print(f"품질 필터링: {len(data)} → {len(filtered)} ({ratio:.1f}%)")
        else:
            print("품질 필터링: 입력 데이터 0개")
        return filtered

    def split_train_valid(
        self,
        data: List[Dict],
        train_ratio: float = 0.8,
        seed: int = 42
    ) -> tuple:
        """
        학습/검증 데이터 분할

        Args:
            data: 전체 데이터
            train_ratio: 학습 데이터 비율
            seed: 랜덤 시드

        Returns:
            tuple: (train_data, valid_data)
        """
        import random
        random.seed(seed)

        shuffled = data.copy()
        random.shuffle(shuffled)

        split_idx = int(len(shuffled) * train_ratio)
        train_data = shuffled[:split_idx]
        valid_data = shuffled[split_idx:]

        print(f"데이터 분할: Train {len(train_data)}개, Valid {len(valid_data)}개")
        return train_data, valid_data

    def save_jsonl(self, data: List[Dict], output_path: str):
        """JSONL 형식으로 저장"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')

        print(f"✅ 저장 완료: {output_path} ({len(data)}개)")

    def load_jsonl(self, input_path: str) -> List[Dict]:
        """JSONL 형식 로드"""
        data = []
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
        return data

    def preprocess_pipeline(self) -> tuple:
        """
        전체 전처리 파이프라인 실행

        Returns:
            tuple: (train_data, valid_data)
        """
        print("=" * 60)
        print("📚 데이터 전처리 시작")
        print("=" * 60)

        # 1. 데이터 로드
        classics_data = self.load_classics_data()
        comprehension_data = self.load_comprehension_data()
        evaluation_data = self.load_evaluation_data()

        merged = classics_data + comprehension_data + evaluation_data

        if not merged:
            print("\n⚠️ 데이터가 없습니다. 다음 단계를 수행해주세요:")
            print("1. AI HUB에서 고전문학 데이터 다운로드")
            print("2. configs/training_config.yaml에 데이터 경로 설정")
            print("3. 데이터 경로와 압축 파일 구조를 확인")
            return [], []

        # 2. 데이터 파싱 (이미 정규화된 형식이면 그대로 사용)
        parsed_data = []
        for item in merged:
            if {"id", "source", "passage", "question", "answer"}.issubset(item.keys()):
                parsed_data.append(item)
            else:
                parsed_data.append(self.parse_classic_text(item))

        print(
            f"📊 로드 통계 - 고전문학: {len(classics_data)}, "
            f"지문형: {len(comprehension_data)}, 평가: {len(evaluation_data)}, "
            f"총합: {len(parsed_data)}"
        )

        # 3. 품질 필터링
        filtered_data = self.filter_quality_data(parsed_data)

        # 4. 학습/검증 분할
        train_data, valid_data = self.split_train_valid(filtered_data)

        # 5. 저장
        self.save_jsonl(train_data, self.output_dir / "train_raw.jsonl")
        self.save_jsonl(valid_data, self.output_dir / "valid_raw.jsonl")

        print("=" * 60)
        print("✅ 전처리 완료!")
        print("=" * 60)

        return train_data, valid_data


# 직접 실행 시
if __name__ == "__main__":
    preprocessor = DataPreprocessor()
    train_data, valid_data = preprocessor.preprocess_pipeline()
