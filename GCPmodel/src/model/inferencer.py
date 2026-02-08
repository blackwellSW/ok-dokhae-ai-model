"""
사고유도 추론 엔진
파인튜닝된 Gemma 모델로 [사고유도] + [사고로그] 생성
"""

import re
import json
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel


class ThoughtInducer:
    """사고유도 추론 엔진"""

    def __init__(
        self,
        model_path: str = "",  # TODO: 파인튜닝된 모델 경로
        base_model_name: str = "google/gemma-3-9b-it",
        load_in_4bit: bool = True,
        device: Optional[str] = None
    ):
        """
        Args:
            model_path: 파인튜닝된 LoRA 모델 경로 (비어있으면 base 모델만 사용)
            base_model_name: 베이스 모델 이름
            load_in_4bit: 4-bit 양자화 사용 여부
            device: 사용할 디바이스 (None이면 자동 선택)
        """
        self.model_path = model_path
        self.base_model_name = base_model_name
        self.load_in_4bit = load_in_4bit
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.model = None
        self.tokenizer = None
        self.is_loaded = False

        # 시스템 프롬프트
        self.system_prompt = """학생의 사고를 유도하며 고전문학을 가르치세요. [사고유도]와 [사고로그] 태그를 사용하세요.

[사고유도]: 학생이 스스로 생각할 수 있도록 단계적 질문을 제시합니다.
[사고로그]: 학생의 사고 과정을 관찰하고 기록합니다."""

    def load_model(self):
        """모델 로드"""
        if self.is_loaded:
            print("모델이 이미 로드되어 있습니다.")
            return

        print(f"📦 모델 로딩 중...")

        # Tokenizer 로드
        tokenizer_path = self.model_path if self.model_path else self.base_model_name
        self.tokenizer = AutoTokenizer.from_pretrained(
            tokenizer_path,
            trust_remote_code=True
        )
        self.tokenizer.pad_token = self.tokenizer.eos_token

        # 양자화 설정
        if self.load_in_4bit:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
            )
        else:
            bnb_config = None

        # 베이스 모델 로드
        base_model = AutoModelForCausalLM.from_pretrained(
            self.base_model_name,
            quantization_config=bnb_config,
            device_map="auto",
            torch_dtype=torch.bfloat16,
            trust_remote_code=True
        )

        # LoRA 어댑터 로드 (파인튜닝된 모델이 있는 경우)
        if self.model_path and Path(self.model_path).exists():
            print(f"   LoRA 어댑터 로드: {self.model_path}")
            self.model = PeftModel.from_pretrained(base_model, self.model_path)
        else:
            print(f"   ⚠️ 파인튜닝된 모델 없음. 베이스 모델 사용.")
            self.model = base_model

        self.model.eval()
        self.is_loaded = True
        print("✅ 모델 로드 완료")

    def generate_response(
        self,
        student_input: str,
        context: Optional[str] = None,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        do_sample: bool = True
    ) -> Dict:
        """
        사고유도 응답 생성

        Args:
            student_input: 학생 질문/입력
            context: 추가 맥락 (작품명, 지문 등)
            max_new_tokens: 최대 생성 토큰 수
            temperature: 샘플링 온도
            top_p: top-p 샘플링
            do_sample: 샘플링 사용 여부

        Returns:
            Dict: {
                "induction": 사고유도 내용,
                "log": 사고로그 내용,
                "full_response": 전체 응답,
                "metadata": 메타데이터
            }
        """
        if not self.is_loaded:
            self.load_model()

        # 프롬프트 구성
        if context:
            prompt = f"""{self.system_prompt}

[맥락]
{context}

학생: {student_input}

AI: [사고유도]"""
        else:
            prompt = f"""{self.system_prompt}

학생: {student_input}

AI: [사고유도]"""

        # 토큰화
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=1024
        ).to(self.model.device)

        # 생성
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=do_sample,
                top_p=top_p,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )

        # 디코딩
        full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # AI 응답 부분만 추출
        ai_response = full_response.split("AI: ")[-1] if "AI: " in full_response else full_response

        # 태그 추출
        induction = self._extract_tag(ai_response, "사고유도")
        log = self._extract_tag(ai_response, "사고로그")

        return {
            "induction": induction,
            "log": log,
            "full_response": ai_response,
            "metadata": {
                "student_input": student_input,
                "context": context,
                "timestamp": datetime.now().isoformat(),
                "model_path": self.model_path or self.base_model_name
            }
        }

    def _extract_tag(self, text: str, tag: str) -> str:
        """태그 내용 추출"""
        # [태그] 내용 추출 패턴
        pattern = rf"\[{tag}\]\s*(.*?)(?=\[|$)"
        match = re.search(pattern, text, re.DOTALL)

        if match:
            return match.group(1).strip()
        return ""

    def chat(
        self,
        messages: List[Dict[str, str]],
        max_new_tokens: int = 512
    ) -> Dict:
        """
        멀티턴 대화 지원

        Args:
            messages: 대화 히스토리 [{"role": "student/ai", "content": "..."}]
            max_new_tokens: 최대 생성 토큰 수

        Returns:
            Dict: 생성된 응답
        """
        if not self.is_loaded:
            self.load_model()

        # 대화 히스토리를 프롬프트로 변환
        conversation = f"{self.system_prompt}\n\n"

        for msg in messages:
            role = msg.get("role", "student")
            content = msg.get("content", "")

            if role == "student":
                conversation += f"학생: {content}\n\n"
            else:
                conversation += f"AI: {content}\n\n"

        # 마지막이 학생 메시지면 AI 응답 생성
        if messages and messages[-1].get("role") == "student":
            conversation += "AI: [사고유도]"

        # 토큰화 및 생성
        inputs = self.tokenizer(
            conversation,
            return_tensors="pt",
            truncation=True,
            max_length=2048
        ).to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=0.7,
                do_sample=True,
                top_p=0.9,
                pad_token_id=self.tokenizer.eos_token_id
            )

        full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        ai_response = full_response.split("AI: ")[-1] if "AI: " in full_response else ""

        # 다음 학생 응답 이전까지만 추출
        if "학생:" in ai_response:
            ai_response = ai_response.split("학생:")[0].strip()

        return {
            "induction": self._extract_tag(ai_response, "사고유도"),
            "log": self._extract_tag(ai_response, "사고로그"),
            "full_response": ai_response,
            "conversation_length": len(messages) + 1
        }

    def save_thought_log(
        self,
        response: Dict,
        output_dir: str = "outputs/thought_logs"
    ) -> str:
        """
        사고로그 저장

        Args:
            response: generate_response 결과
            output_dir: 저장 디렉토리

        Returns:
            str: 저장된 파일 경로
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"thought_log_{timestamp}.json"
        filepath = output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(response, f, ensure_ascii=False, indent=2)

        return str(filepath)

    def batch_generate(
        self,
        inputs: List[str],
        contexts: Optional[List[str]] = None,
        output_path: Optional[str] = None
    ) -> List[Dict]:
        """
        배치 생성

        Args:
            inputs: 학생 입력 리스트
            contexts: 맥락 리스트 (선택)
            output_path: 결과 저장 경로 (선택)

        Returns:
            List[Dict]: 생성 결과 리스트
        """
        from tqdm import tqdm

        if not self.is_loaded:
            self.load_model()

        results = []
        contexts = contexts or [None] * len(inputs)

        for student_input, context in tqdm(zip(inputs, contexts), total=len(inputs), desc="생성 중"):
            result = self.generate_response(student_input, context)
            results.append(result)

        # 저장
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                for item in results:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')

            print(f"✅ 저장 완료: {output_path}")

        return results


# 직접 실행 시
if __name__ == "__main__":
    # 사용 예시
    inducer = ThoughtInducer(
        model_path="",  # TODO: 파인튜닝된 모델 경로
        base_model_name="google/gemma-3-9b-it"
    )

    # 테스트 (모델 로드 필요)
    # inducer.load_model()
    # result = inducer.generate_response(
    #     student_input="춘향전에서 이몽룡이 신분을 숨긴 이유가 뭔가요?",
    #     context="춘향전"
    # )
    # print(result)

    print("추론 엔진 준비 완료. model_path를 설정하고 사용하세요.")
