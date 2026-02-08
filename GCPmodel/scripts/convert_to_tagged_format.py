#!/usr/bin/env python3
"""
소크라틱 데이터를 [사고유도]/[사고로그] 태그 형식으로 변환
Gemini API를 사용해서 자동 변환
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, List
from tqdm import tqdm
import google.generativeai as genai


class TaggedFormatConverter:
    """태그 형식으로 데이터 변환"""

    def __init__(self, api_key: str = None):
        """
        Args:
            api_key: Gemini API 키
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

        self.conversion_prompt_template = """다음 소크라틱 대화를 [사고유도]와 [사고로그] 태그 형식으로 변환하세요.

**중요**: 반드시 아래 형식을 따라주세요:

[사고유도]
학생이 스스로 생각하도록 유도하는 질문들을 작성합니다.
- 단계적으로 생각하도록 돕는 질문
- "~을까요?", "~인가요?" 형태의 열린 질문
- 학생의 사고 과정을 자극하는 내용

[사고로그]
학생의 사고 과정을 관찰하고 분석한 내용을 작성합니다.
- 학생이 어떤 부분을 이해했는지
- 어떤 개념을 연결하고 있는지
- 다음 단계로 나아가기 위해 필요한 것

---

**원본 소크라틱 대화:**
{original_output}

---

**변환 결과 (아래 형식으로만 출력):**
[사고유도]
(여기에 사고유도 내용)

[사고로그]
(여기에 사고로그 내용)
"""

    def convert_single_item(self, item: Dict) -> Dict:
        """
        단일 데이터 아이템을 태그 형식으로 변환

        Args:
            item: 원본 데이터 (instruction, input, output, metadata)

        Returns:
            변환된 데이터
        """
        original_output = item.get("output", "")

        # 이미 태그가 있으면 그대로 반환
        if "[사고유도]" in original_output and "[사고로그]" in original_output:
            return item

        # 변환 프롬프트 생성
        prompt = self.conversion_prompt_template.format(
            original_output=original_output
        )

        try:
            # Gemini API 호출
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.3,  # 일관성을 위해 낮은 온도
                    "max_output_tokens": 1024,
                }
            )

            converted_output = response.text

            # 태그 검증
            if "[사고유도]" not in converted_output or "[사고로그]" not in converted_output:
                print(f"⚠️ 태그가 누락됨. 원본 유지")
                return item

            # 새 아이템 생성
            new_item = item.copy()
            new_item["output"] = converted_output

            return new_item

        except Exception as e:
            print(f"❌ 변환 실패: {e}")
            return item

    def convert_dataset(
        self,
        input_path: str,
        output_path: str,
        max_samples: int = None,
        start_from: int = 0
    ):
        """
        전체 데이터셋 변환

        Args:
            input_path: 입력 JSONL 파일 경로
            output_path: 출력 JSONL 파일 경로
            max_samples: 최대 샘플 수 (None이면 전체)
            start_from: 시작 인덱스 (중단된 작업 재개용)
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*70}")
        print(f"📝 데이터셋 변환: {input_path.name}")
        print(f"{'='*70}")

        # 입력 데이터 로드
        with open(input_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total_lines = len(lines)
        if max_samples:
            lines = lines[:max_samples]

        print(f"총 샘플 수: {len(lines)}")
        print(f"시작 인덱스: {start_from}")

        # 이미 변환된 데이터가 있으면 로드
        already_converted = []
        if output_path.exists() and start_from > 0:
            with open(output_path, 'r', encoding='utf-8') as f:
                already_converted = [line for line in f]
            print(f"이미 변환된 샘플: {len(already_converted)}")

        # 변환 모드 선택
        mode = "append" if already_converted else "write"

        # 변환 실행
        converted_count = 0
        error_count = 0

        with open(output_path, 'a' if mode == "append" else 'w', encoding='utf-8') as f:
            # 이미 변환된 데이터 유지
            if mode == "write" and already_converted:
                for line in already_converted:
                    f.write(line)

            for i, line in enumerate(tqdm(lines[start_from:], desc="변환 중")):
                if not line.strip():
                    continue

                try:
                    item = json.loads(line)

                    # 변환
                    converted_item = self.convert_single_item(item)

                    # 저장
                    f.write(json.dumps(converted_item, ensure_ascii=False) + '\n')
                    f.flush()  # 중단되어도 저장되도록

                    converted_count += 1

                    # API 레이트 리밋 방지
                    time.sleep(0.5)

                except Exception as e:
                    print(f"\n❌ 라인 {start_from + i} 처리 실패: {e}")
                    error_count += 1
                    # 원본 그대로 저장
                    f.write(line)

        print(f"\n{'='*70}")
        print(f"✅ 변환 완료!")
        print(f"   성공: {converted_count}")
        print(f"   실패: {error_count}")
        print(f"   저장 위치: {output_path}")
        print(f"{'='*70}")

    def validate_output(self, output_path: str, sample_size: int = 10):
        """
        변환된 데이터 검증

        Args:
            output_path: 변환된 파일 경로
            sample_size: 검증할 샘플 수
        """
        print(f"\n{'='*70}")
        print(f"🔍 데이터 검증: {Path(output_path).name}")
        print(f"{'='*70}")

        with open(output_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total = len(lines)
        has_induction = 0
        has_log = 0
        has_both = 0

        # 전체 통계
        for line in lines:
            if not line.strip():
                continue

            try:
                item = json.loads(line)
                output = item.get("output", "")

                has_ind = "[사고유도]" in output
                has_l = "[사고로그]" in output

                if has_ind:
                    has_induction += 1
                if has_l:
                    has_log += 1
                if has_ind and has_l:
                    has_both += 1

            except:
                pass

        print(f"\n📊 전체 통계:")
        print(f"   총 샘플 수: {total}")
        print(f"   [사고유도] 태그 있음: {has_induction} ({has_induction/total*100:.1f}%)")
        print(f"   [사고로그] 태그 있음: {has_log} ({has_log/total*100:.1f}%)")
        print(f"   둘 다 있음: {has_both} ({has_both/total*100:.1f}%)")

        # 샘플 출력
        print(f"\n📝 샘플 {sample_size}개 미리보기:")
        print("-" * 70)

        import random
        sample_indices = random.sample(range(len(lines)), min(sample_size, len(lines)))

        for idx in sample_indices[:3]:  # 처음 3개만 자세히 출력
            line = lines[idx]
            if not line.strip():
                continue

            try:
                item = json.loads(line)
                output = item.get("output", "")

                print(f"\n[샘플 {idx+1}]")
                print(f"Input: {item.get('input', '')[:80]}...")
                print(f"\nOutput (첫 500자):")
                print(output[:500])
                print("-" * 70)

            except:
                pass


def main():
    import argparse

    parser = argparse.ArgumentParser(description="소크라틱 데이터를 태그 형식으로 변환")

    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="입력 JSONL 파일"
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="출력 JSONL 파일"
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="최대 변환 샘플 수 (테스트용)"
    )
    parser.add_argument(
        "--start-from",
        type=int,
        default=0,
        help="시작 인덱스 (중단된 작업 재개용)"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="변환 없이 검증만 수행"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default="",
        help="Gemini API 키"
    )

    args = parser.parse_args()

    # API 키 설정
    api_key = args.api_key or os.getenv("GEMINI_API_KEY")

    if not api_key and not args.validate_only:
        print("❌ GEMINI_API_KEY가 필요합니다.")
        print("   export GEMINI_API_KEY='your-api-key'")
        return

    # 변환기 초기화
    if not args.validate_only:
        converter = TaggedFormatConverter(api_key=api_key)

        # 변환 실행
        converter.convert_dataset(
            input_path=args.input,
            output_path=args.output,
            max_samples=args.max_samples,
            start_from=args.start_from
        )

    # 검증
    if Path(args.output).exists():
        converter = TaggedFormatConverter(api_key=api_key) if not args.validate_only else None
        if converter:
            converter.validate_output(args.output, sample_size=10)


if __name__ == "__main__":
    main()
