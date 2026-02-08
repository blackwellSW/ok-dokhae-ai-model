#!/usr/bin/env python3
"""
태그된 소크라틱 데이터를 Gemini SFT 형식으로 변환
Vertex AI Gemini 튜닝에 사용할 JSONL 생성
"""

import json
from pathlib import Path
from tqdm import tqdm


def convert_to_gemini_format(input_path: str, output_path: str):
    """
    소크라틱 데이터를 Gemini contents 형식으로 변환

    Gemini 튜닝 형식:
    {
        "contents": [
            {"role": "user", "parts": [{"text": "..."}]},
            {"role": "model", "parts": [{"text": "..."}]}
        ]
    }
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*70}")
    print(f"📝 Gemini 튜닝 형식으로 변환: {input_path.name}")
    print(f"{'='*70}")

    system_instruction = """[시스템 역할]
당신은 '사고유도 교사(Thought-Inducing Tutor)'입니다.
학생의 질문에 직접 답을 주지 않고, [사고유도]와 [사고로그] 태그를 사용하여
학생이 스스로 생각하고 답을 찾을 수 있도록 단계적 질문을 제시합니다.

[사고유도]: 학생이 스스로 생각할 수 있도록 단계적 질문을 제시합니다.
[사고로그]: 학생의 사고 과정을 관찰하고 분석한 내용을 기록합니다."""

    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    print(f"입력 샘플 수: {len(lines)}")

    converted_count = 0
    skipped_count = 0

    with open(output_path, 'w', encoding='utf-8') as f:
        for line in tqdm(lines, desc="변환 중"):
            if not line.strip():
                continue

            try:
                item = json.loads(line)

                instruction = item.get('instruction', '')
                input_text = item.get('input', '')
                output_text = item.get('output', '')

                # 태그가 없는 데이터는 건너뛰기
                if '[사고유도]' not in output_text and '[사고로그]' not in output_text:
                    skipped_count += 1
                    continue

                # user 메시지 구성
                user_text = f"{system_instruction}\n\n{input_text}"

                # Gemini contents 형식
                gemini_item = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": user_text}]
                        },
                        {
                            "role": "model",
                            "parts": [{"text": output_text}]
                        }
                    ]
                }

                f.write(json.dumps(gemini_item, ensure_ascii=False) + '\n')
                converted_count += 1

            except Exception as e:
                print(f"\n❌ 변환 실패: {e}")
                skipped_count += 1

    print(f"\n{'='*70}")
    print(f"✅ 변환 완료!")
    print(f"   변환 성공: {converted_count}")
    print(f"   건너뛴 샘플: {skipped_count}")
    print(f"   저장 위치: {output_path}")
    print(f"{'='*70}")

    return converted_count


def validate_gemini_format(output_path: str, sample_size: int = 3):
    """변환된 데이터 검증"""
    print(f"\n{'='*70}")
    print(f"🔍 Gemini 형식 검증: {Path(output_path).name}")
    print(f"{'='*70}")

    with open(output_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    total = len(lines)
    valid_count = 0

    for line in lines:
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            contents = item.get('contents', [])
            if len(contents) == 2:
                user_msg = contents[0]
                model_msg = contents[1]
                if (user_msg.get('role') == 'user' and
                    model_msg.get('role') == 'model' and
                    len(user_msg.get('parts', [])) > 0 and
                    len(model_msg.get('parts', [])) > 0):
                    valid_count += 1
        except:
            pass

    print(f"\n📊 검증 결과:")
    print(f"   총 샘플 수: {total}")
    print(f"   유효한 샘플: {valid_count} ({valid_count/total*100:.1f}%)")

    # 샘플 출력
    print(f"\n📝 샘플 미리보기:")
    for i, line in enumerate(lines[:sample_size]):
        try:
            item = json.loads(line)
            user_text = item['contents'][0]['parts'][0]['text']
            model_text = item['contents'][1]['parts'][0]['text']

            print(f"\n[샘플 {i+1}]")
            print(f"User (처음 200자): {user_text[:200]}...")
            print(f"Model (처음 300자): {model_text[:300]}...")
            print("-" * 70)
        except:
            pass


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Gemini 튜닝 형식 변환")

    parser.add_argument("--train-input", type=str, default="data/final/train_tagged.jsonl")
    parser.add_argument("--valid-input", type=str, default="data/final/valid_tagged.jsonl")
    parser.add_argument("--train-output", type=str, default="data/final/gemini_train_tagged.jsonl")
    parser.add_argument("--valid-output", type=str, default="data/final/gemini_valid_tagged.jsonl")

    args = parser.parse_args()

    # Train 데이터 변환
    train_count = convert_to_gemini_format(args.train_input, args.train_output)

    # Valid 데이터 변환
    valid_count = convert_to_gemini_format(args.valid_input, args.valid_output)

    # 검증
    if train_count > 0:
        validate_gemini_format(args.train_output)
    if valid_count > 0:
        validate_gemini_format(args.valid_output)

    print(f"\n{'='*70}")
    print(f"📊 최종 요약")
    print(f"{'='*70}")
    print(f"   Train: {train_count}개")
    print(f"   Valid: {valid_count}개")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
