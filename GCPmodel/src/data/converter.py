"""
소크라틱 대화 변환 모듈
AI HUB 데이터를 소크라틱 대화 형식으로 변환
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from tqdm import tqdm


class SocraticConverter:
    """원본 Q&A를 소크라틱 대화 형식으로 변환"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_type: str = "openai",  # "openai" or "gemini"
        template_path: str = "data/templates/socratic_patterns.json"
    ):
        """
        Args:
            api_key: API 키 (환경변수 우선)
            api_type: 사용할 API 타입 ("openai" 또는 "gemini")
            template_path: 소크라틱 패턴 템플릿 경로
        """
        self.api_type = api_type
        self.api_key = api_key or os.getenv(
            "OPENAI_API_KEY" if api_type == "openai" else "GEMINI_API_KEY"
        )
        self.templates = self._load_templates(template_path)
        self._setup_client()

    def _load_templates(self, template_path: str) -> Dict:
        """템플릿 로드"""
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"템플릿 파일을 찾을 수 없습니다: {template_path}")
            return {}

    def _setup_client(self):
        """API 클라이언트 설정"""
        if not self.api_key:
            print(f"⚠️ {self.api_type.upper()} API 키가 설정되지 않았습니다.")
            print(f"   환경변수 또는 생성자에서 API 키를 설정해주세요.")
            self.client = None
            return

        if self.api_type == "openai":
            try:
                import openai
                openai.api_key = self.api_key
                self.client = openai
            except ImportError:
                print("openai 패키지를 설치해주세요: pip install openai")
                self.client = None

        elif self.api_type == "gemini":
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel('gemini-pro')
            except ImportError:
                print("google-generativeai 패키지를 설치해주세요")
                self.client = None

    def _get_conversion_prompt(
        self,
        passage: str,
        question: str,
        answer: str
    ) -> str:
        """변환 프롬프트 생성"""
        template = self.templates.get(
            "conversion_prompt_template",
            self._default_prompt_template()
        )

        return template.format(
            passage=passage,
            question=question,
            answer=answer
        )

    def _default_prompt_template(self) -> str:
        """기본 변환 프롬프트"""
        return """다음 고전문학 질문을 소크라틱 대화 형식으로 변환하세요.

[원본 지문]
{passage}

[학생 질문]
{question}

[모범 답안]
{answer}

[변환 요구사항]
1. [사고유도] 태그: 학생의 사고를 유도하는 단계적 질문 (2-3개)
2. [사고로그] 태그: 학생이 거칠 사고 과정 예측 및 기록
3. 직접 답을 주지 말고, 스스로 생각하도록 유도

[출력 형식]
[사고유도] (단계적 질문)
[사고로그] (예상 사고 과정, 추론 깊이/맥락 이해도 포함)"""

    def convert_to_socratic(
        self,
        passage: str,
        question: str,
        answer: str,
        source: str = "unknown"
    ) -> Dict:
        """
        원본 Q&A를 소크라틱 대화로 변환

        Args:
            passage: 지문 내용
            question: 학생 질문
            answer: 모범 답안
            source: 출처 (작품명)

        Returns:
            Dict: 변환된 데이터
        """
        if not self.client:
            return self._create_placeholder_data(passage, question, answer, source)

        prompt = self._get_conversion_prompt(passage, question, answer)

        try:
            if self.api_type == "openai":
                response = self.client.ChatCompletion.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": "당신은 소크라틱 대화법 전문가입니다."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
                converted_text = response.choices[0].message.content

            elif self.api_type == "gemini":
                response = self.client.generate_content(prompt)
                converted_text = response.text

            else:
                converted_text = ""

        except Exception as e:
            print(f"API 호출 오류: {e}")
            return self._create_placeholder_data(passage, question, answer, source)

        return {
            "instruction": self.templates.get(
                "instruction_template",
                "학생의 사고를 유도하며 고전문학을 가르치세요. [사고유도]와 [사고로그] 태그를 사용하세요."
            ),
            "input": f"학생: {question}",
            "output": converted_text,
            "metadata": {
                "source": source,
                "passage": passage,
                "original_answer": answer
            }
        }

    def _create_placeholder_data(
        self,
        passage: str,
        question: str,
        answer: str,
        source: str
    ) -> Dict:
        """
        API 없이 플레이스홀더 데이터 생성
        (수동 작성 또는 나중에 변환할 데이터)
        """
        return {
            "instruction": "학생의 사고를 유도하며 고전문학을 가르치세요. [사고유도]와 [사고로그] 태그를 사용하세요.",
            "input": f"학생: {question}",
            "output": "[사고유도] TODO: 변환 필요\n[사고로그] TODO: 변환 필요",
            "metadata": {
                "source": source,
                "passage": passage,
                "original_answer": answer,
                "needs_conversion": True
            }
        }

    def batch_convert(
        self,
        data_list: List[Dict],
        output_path: str,
        skip_existing: bool = True
    ) -> List[Dict]:
        """
        배치 변환

        Args:
            data_list: 변환할 데이터 리스트
            output_path: 출력 파일 경로
            skip_existing: 기존 변환 데이터 스킵 여부

        Returns:
            List[Dict]: 변환된 데이터 리스트
        """
        converted_data = []
        output_path = Path(output_path)

        # 기존 데이터 로드 (이어서 변환)
        if skip_existing and output_path.exists():
            with open(output_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        converted_data.append(json.loads(line))
            print(f"기존 변환 데이터 {len(converted_data)}개 로드")

        existing_ids = {item.get('metadata', {}).get('id') for item in converted_data}

        for i, item in enumerate(tqdm(data_list, desc="변환 중")):
            item_id = item.get('id', f"item_{i}")

            # 이미 변환된 데이터 스킵
            if skip_existing and item_id in existing_ids:
                continue

            try:
                converted = self.convert_to_socratic(
                    passage=item.get('passage', ''),
                    question=item.get('question', ''),
                    answer=item.get('answer', ''),
                    source=item.get('source', 'unknown')
                )
                converted['metadata']['id'] = item_id
                converted_data.append(converted)

                # 중간 저장 (50개마다)
                if (i + 1) % 50 == 0:
                    self._save_intermediate(converted_data, output_path)
                    print(f"\nProgress: {i+1}/{len(data_list)}")

            except Exception as e:
                print(f"Error at {i}: {e}")
                continue

        # 최종 저장
        self._save_intermediate(converted_data, output_path)
        print(f"\n✅ 변환 완료: {len(converted_data)}개")

        return converted_data

    def _save_intermediate(self, data: List[Dict], output_path: Path):
        """중간 저장"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')

    def create_manual_template(
        self,
        data_list: List[Dict],
        output_path: str,
        num_samples: int = 50
    ):
        """
        수동 작성용 템플릿 생성

        Args:
            data_list: 원본 데이터
            output_path: 출력 경로
            num_samples: 샘플 개수
        """
        import random
        samples = random.sample(data_list, min(num_samples, len(data_list)))

        template_data = []
        for i, item in enumerate(samples):
            template_data.append({
                "id": f"manual_{i+1:03d}",
                "source": item.get('source', ''),
                "passage": item.get('passage', ''),
                "question": item.get('question', ''),
                "original_answer": item.get('answer', ''),
                "thought_induction": "TODO: [사고유도] 내용 작성",
                "thought_log": "TODO: [사고로그] 내용 작성"
            })

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(template_data, f, ensure_ascii=False, indent=2)

        print(f"✅ 수동 작성 템플릿 생성: {output_path} ({len(template_data)}개)")

    def convert_manual_to_training(
        self,
        manual_path: str,
        output_path: str
    ) -> List[Dict]:
        """
        수동 작성된 데이터를 학습 형식으로 변환

        Args:
            manual_path: 수동 작성 파일 경로
            output_path: 출력 경로

        Returns:
            List[Dict]: 학습용 데이터
        """
        with open(manual_path, 'r', encoding='utf-8') as f:
            manual_data = json.load(f)

        training_data = []
        for item in manual_data:
            # TODO 항목 건너뛰기
            if "TODO" in item.get('thought_induction', ''):
                continue

            training_data.append({
                "instruction": "학생의 사고를 유도하며 고전문학을 가르치세요. [사고유도]와 [사고로그] 태그를 사용하세요.",
                "input": f"학생: {item['question']}",
                "output": f"[사고유도] {item['thought_induction']}\n\n[사고로그] {item['thought_log']}",
                "metadata": {
                    "id": item['id'],
                    "source": item['source'],
                    "passage": item['passage'],
                    "original_answer": item['original_answer']
                }
            })

        # 저장
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            for item in training_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')

        print(f"✅ 학습 데이터 변환 완료: {len(training_data)}개")
        return training_data


# 직접 실행 시
if __name__ == "__main__":
    # 사용 예시
    converter = SocraticConverter(
        api_type="gemini",  # 또는 "openai"
        # api_key="YOUR_API_KEY"  # 또는 환경변수 사용
    )

    # 테스트 데이터
    test_data = [
        {
            "id": "test_001",
            "source": "춘향전",
            "passage": "춘향전의 한 장면...",
            "question": "이몽룡이 신분을 숨긴 이유는 무엇인가요?",
            "answer": "신분제 사회에서 진정한 사랑을 확인하기 위해..."
        }
    ]

    # 수동 작성 템플릿 생성
    # converter.create_manual_template(test_data, "data/templates/manual_samples.json")

    # 배치 변환
    # converted = converter.batch_convert(test_data, "data/processed/converted.jsonl")
