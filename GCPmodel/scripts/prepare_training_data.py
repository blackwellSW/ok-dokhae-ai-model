#!/usr/bin/env python3
"""
Q&A 형식 데이터를 학습용 형식으로 변환
"""

import json
import argparse
from pathlib import Path


def convert_qa_to_training(input_path: str, output_path: str):
    """
    Q&A 형식을 instruction-tuning 형식으로 변환

    Args:
        input_path: 입력 JSONL 파일 (Q&A 형식)
        output_path: 출력 JSONL 파일 (학습용 형식)
    """
    converted = []

    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue

            item = json.loads(line)

            # instruction-tuning 형식으로 변환
            converted_item = {
                "instruction": "다음 지문을 읽고 질문에 답하세요. 학생의 사고를 유도하며 답변을 작성하세요.",
                "input": f"[지문]\n{item.get('passage', '')}\n\n[질문]\n{item.get('question', '')}",
                "output": item.get('answer', ''),
                "metadata": {
                    "id": item.get('id', ''),
                    "source": item.get('source', ''),
                    "dataset": item.get('dataset', 'train')
                }
            }

            converted.append(converted_item)

    # 저장
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        for item in converted:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print(f"✅ 변환 완료: {len(converted)}개")
    print(f"   출력: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Q&A 데이터를 학습용 형식으로 변환")

    parser.add_argument("--input", type=str, required=True, help="입력 파일 경로")
    parser.add_argument("--output", type=str, required=True, help="출력 파일 경로")

    args = parser.parse_args()

    convert_qa_to_training(args.input, args.output)


if __name__ == "__main__":
    main()
