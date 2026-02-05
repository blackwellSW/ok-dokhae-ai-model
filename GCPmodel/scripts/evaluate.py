#!/usr/bin/env python3
"""
평가 실행 스크립트
학생 입력에 대해 사고유도 + 평가 수행
"""

import argparse
import json
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.integration.pipeline import IntegratedPipeline


def main():
    parser = argparse.ArgumentParser(description="사고유도 AI 평가")

    # 입력 모드
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="대화형 모드 실행"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="",
        help="단일 입력 텍스트"
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default="",
        help="입력 파일 (JSONL)"
    )
    parser.add_argument(
        "--context",
        type=str,
        default="",
        help="맥락 (작품명 등)"
    )

    # 모델/설정
    parser.add_argument(
        "--model-path",
        type=str,
        default="",
        help="파인튜닝된 모델 경로"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/evaluation_config.yaml",
        help="평가 설정 파일"
    )

    # 출력
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="결과 저장 경로"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "markdown", "both"],
        default="both",
        help="출력 형식"
    )

    args = parser.parse_args()

    # 파이프라인 초기화
    print("🔧 파이프라인 초기화 중...")
    pipeline = IntegratedPipeline(
        model_path=args.model_path,
        config_path=args.config
    )

    # 대화형 모드
    if args.interactive:
        run_interactive(pipeline)
        return

    # 단일 입력
    if args.input:
        result = pipeline.process(
            student_input=args.input,
            context=args.context if args.context else None
        )
        print_result(result, args.format)

        if args.output:
            save_result(result, args.output, args.format, pipeline)
        return

    # 파일 입력
    if args.input_file:
        run_batch(pipeline, args.input_file, args.output, args.format)
        return

    # 사용법 출력
    print("=" * 60)
    print("📊 사고유도 AI 평가 시스템")
    print("=" * 60)
    print("\n사용법:")
    print("\n1. 대화형 모드:")
    print("   python scripts/evaluate.py --interactive")
    print("\n2. 단일 입력:")
    print("   python scripts/evaluate.py --input '춘향전에서...' --context '춘향전'")
    print("\n3. 배치 처리:")
    print("   python scripts/evaluate.py --input-file inputs.jsonl --output results.jsonl")
    print("\n옵션:")
    print("   --model-path: 파인튜닝된 모델 경로")
    print("   --format: 출력 형식 (json, markdown, both)")
    print("=" * 60)


def run_interactive(pipeline):
    """대화형 모드 실행"""
    print("\n" + "=" * 60)
    print("💬 대화형 모드 (종료: 'quit' 또는 'exit')")
    print("=" * 60)

    context = input("\n📚 맥락 입력 (작품명, 없으면 Enter): ").strip() or None

    while True:
        print("\n" + "-" * 40)
        student_input = input("👤 학생: ").strip()

        if student_input.lower() in ['quit', 'exit', 'q']:
            print("\n👋 종료합니다.")
            break

        if not student_input:
            continue

        print("\n⏳ 처리 중...")
        result = pipeline.process(
            student_input=student_input,
            context=context,
            save_result=True
        )

        # 사고유도 응답 출력
        print("\n" + "=" * 40)
        print("🤖 AI 사고유도:")
        print("-" * 40)
        print(result.get('사고유도_응답', ''))

        # 평가 결과 요약
        integrated = result.get('통합_평가', {})
        print("\n📊 평가 결과:")
        print(f"   등급: {integrated.get('등급', 'N/A')}")
        print(f"   총점: {integrated.get('총점', 0)}/100")

        # 피드백
        feedback = result.get('개인_피드백', [])
        if feedback:
            print("\n💡 피드백:")
            for fb in feedback[:3]:  # 상위 3개만
                print(f"   {fb}")


def run_batch(pipeline, input_file, output_path, format_type):
    """배치 처리 실행"""
    print(f"\n📄 입력 파일: {input_file}")

    # 입력 로드
    inputs = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                inputs.append(json.loads(line))

    print(f"   {len(inputs)}개 항목 로드")

    # 처리
    results = pipeline.batch_process(inputs, output_path)

    print(f"\n✅ 배치 처리 완료: {len(results)}개")

    if output_path:
        print(f"📁 결과 저장: {output_path}")


def print_result(result, format_type):
    """결과 출력"""
    if format_type in ['json', 'both']:
        print("\n📋 JSON 결과:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if format_type in ['markdown', 'both']:
        print("\n📝 요약:")
        print(f"   사고유도: {result.get('사고유도_응답', '')[:100]}...")
        integrated = result.get('통합_평가', {})
        print(f"   등급: {integrated.get('등급', 'N/A')}")
        print(f"   총점: {integrated.get('총점', 0)}")


def save_result(result, output_path, format_type, pipeline):
    """결과 저장"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if format_type in ['json', 'both']:
        json_path = output_path.with_suffix('.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"💾 JSON 저장: {json_path}")

    if format_type in ['markdown', 'both']:
        md_path = output_path.with_suffix('.md')
        report = pipeline.generate_student_report(result)
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"💾 Markdown 저장: {md_path}")


if __name__ == "__main__":
    main()
