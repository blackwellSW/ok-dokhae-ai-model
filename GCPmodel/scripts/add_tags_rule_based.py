#!/usr/bin/env python3
"""
규칙 기반으로 [사고유도]/[사고로그] 태그 추가
소크라틱 대화의 구조를 분석해서 자동으로 태그 삽입
"""

import json
import re
from pathlib import Path
from typing import Dict
from tqdm import tqdm


class RuleBasedTagger:
    """규칙 기반 태그 추가"""

    def __init__(self):
        # 질문 패턴 (사고유도에 해당)
        self.question_patterns = [
            r'\?',  # 물음표
            r'~을까요',
            r'~인가요',
            r'~할까요',
            r'생각해.*봅시다',
            r'고려해.*봅시다',
            r'주목해.*봅시다',
            r'어떤.*까요',
            r'무엇.*까요',
            r'왜.*까요',
        ]

        # 관찰/분석 패턴 (사고로그에 해당)
        self.observation_patterns = [
            r'보여주고 있습니다',
            r'이해.*있습니다',
            r'알.*있.*니다',
            r'드러.*니다',
            r'주목.*점',
            r'시작입니다',
            r'좋은.*니다',
            r'연결.*니다',
        ]

    def split_into_induction_and_log(self, text: str) -> tuple:
        """
        소크라틱 대화를 사고유도와 사고로그로 분리

        전략:
        - 앞부분 70%: 사고유도 (질문이 많은 부분)
        - 뒷부분 30%: 사고로그 (관찰/분석 부분)

        Args:
            text: 원본 소크라틱 대화

        Returns:
            (사고유도 부분, 사고로그 부분)
        """
        # 문단 단위로 분리
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        if len(paragraphs) == 0:
            return (text, "학생의 사고 과정을 관찰하고 있습니다.")

        # 전체 길이의 70%를 사고유도로
        split_point = max(1, int(len(paragraphs) * 0.7))

        induction_parts = paragraphs[:split_point]
        log_parts = paragraphs[split_point:]

        # 사고로그가 비어있으면 마지막 문단을 분석으로 변환
        if not log_parts:
            if induction_parts:
                last_para = induction_parts[-1]
                # 질문이 많으면 사고로그 생성
                if '?' in last_para or '까요' in last_para:
                    log_parts = ["위의 질문들을 통해 학생이 스스로 깊이 생각하고 논리적으로 분석할 수 있도록 유도하고 있습니다."]
                else:
                    log_parts = [last_para]
                    induction_parts = induction_parts[:-1]

        return ('\n\n'.join(induction_parts), '\n\n'.join(log_parts))

    def add_tags(self, text: str) -> str:
        """
        소크라틱 대화에 태그 추가

        Args:
            text: 원본 소크라틱 대화

        Returns:
            태그가 추가된 텍스트
        """
        # 이미 태그가 있으면 그대로 반환
        if '[사고유도]' in text and '[사고로그]' in text:
            return text

        # 사고유도와 사고로그로 분리
        induction, log = self.split_into_induction_and_log(text)

        # 태그 추가
        tagged_text = ""

        if induction:
            tagged_text += "[사고유도]\n" + induction

        if log:
            if tagged_text:
                tagged_text += "\n\n"
            tagged_text += "[사고로그]\n" + log

        # 둘 다 비어있으면 원본 반환 (전체를 사고유도로)
        if not tagged_text.strip():
            tagged_text = "[사고유도]\n" + text + "\n\n[사고로그]\n학생의 사고 과정을 관찰 중입니다."

        return tagged_text

    def convert_dataset(
        self,
        input_path: str,
        output_path: str,
        max_samples: int = None
    ):
        """
        전체 데이터셋 변환

        Args:
            input_path: 입력 JSONL 파일
            output_path: 출력 JSONL 파일
            max_samples: 최대 샘플 수
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*70}")
        print(f"📝 규칙 기반 태그 추가: {input_path.name}")
        print(f"{'='*70}")

        # 입력 데이터 로드
        with open(input_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if max_samples:
            lines = lines[:max_samples]

        print(f"총 샘플 수: {len(lines)}")

        # 변환
        converted_count = 0
        error_count = 0

        with open(output_path, 'w', encoding='utf-8') as f:
            for i, line in enumerate(tqdm(lines, desc="태그 추가 중")):
                if not line.strip():
                    continue

                try:
                    item = json.loads(line)
                    original_output = item.get('output', '')

                    # 태그 추가
                    tagged_output = self.add_tags(original_output)

                    # 새 아이템 생성
                    new_item = item.copy()
                    new_item['output'] = tagged_output

                    # 저장
                    f.write(json.dumps(new_item, ensure_ascii=False) + '\n')
                    converted_count += 1

                except Exception as e:
                    print(f"\n❌ 라인 {i} 처리 실패: {e}")
                    error_count += 1
                    f.write(line)

        print(f"\n{'='*70}")
        print(f"✅ 변환 완료!")
        print(f"   성공: {converted_count}")
        print(f"   실패: {error_count}")
        print(f"   저장 위치: {output_path}")
        print(f"{'='*70}")

    def validate_output(self, output_path: str, sample_size: int = 5):
        """변환된 데이터 검증"""
        print(f"\n{'='*70}")
        print(f"🔍 데이터 검증: {Path(output_path).name}")
        print(f"{'='*70}")

        with open(output_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total = len(lines)
        has_induction = 0
        has_log = 0
        has_both = 0

        for line in lines:
            if not line.strip():
                continue

            try:
                item = json.loads(line)
                output = item.get('output', '')

                has_ind = '[사고유도]' in output
                has_l = '[사고로그]' in output

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
        print(f"   [사고유도] 태그: {has_induction} ({has_induction/total*100:.1f}%)")
        print(f"   [사고로그] 태그: {has_log} ({has_log/total*100:.1f}%)")
        print(f"   둘 다 있음: {has_both} ({has_both/total*100:.1f}%)")

        # 샘플 출력
        print(f"\n📝 샘플 미리보기:")
        print("-" * 70)

        for i, line in enumerate(lines[:sample_size]):
            if not line.strip():
                continue

            try:
                item = json.loads(line)
                output = item.get('output', '')

                print(f"\n[샘플 {i+1}]")
                print(f"Input: {item.get('input', '')[:60]}...")
                print(f"\nOutput:")
                print(output[:600])
                print("-" * 70)

            except:
                pass


def main():
    import argparse

    parser = argparse.ArgumentParser(description="규칙 기반으로 태그 추가")

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
        help="최대 변환 샘플 수"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="검증만 수행"
    )

    args = parser.parse_args()

    tagger = RuleBasedTagger()

    if not args.validate_only:
        # 변환 실행
        tagger.convert_dataset(
            input_path=args.input,
            output_path=args.output,
            max_samples=args.max_samples
        )

    # 검증
    if Path(args.output).exists():
        tagger.validate_output(args.output, sample_size=5)


if __name__ == "__main__":
    main()
