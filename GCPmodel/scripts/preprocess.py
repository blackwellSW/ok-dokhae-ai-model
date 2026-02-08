#!/usr/bin/env python3
"""
데이터 전처리 실행 스크립트
"""

import argparse
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.preprocessor import DataPreprocessor
from src.data.converter import SocraticConverter


def main():
    parser = argparse.ArgumentParser(description="데이터 전처리")

    parser.add_argument(
        "--config",
        type=str,
        default="configs/training_config.yaml",
        help="설정 파일 경로"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/processed",
        help="출력 디렉토리"
    )
    parser.add_argument(
        "--create-templates",
        action="store_true",
        help="수동 작성용 템플릿 생성"
    )
    parser.add_argument(
        "--template-count",
        type=int,
        default=50,
        help="템플릿 샘플 개수"
    )
    parser.add_argument(
        "--convert-socratic",
        action="store_true",
        help="소크라틱 대화로 자동 변환"
    )
    parser.add_argument(
        "--api-type",
        type=str,
        choices=["openai", "gemini"],
        default="gemini",
        help="변환에 사용할 API"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("📚 데이터 전처리 시작")
    print("=" * 60)

    # 1. 기본 전처리
    preprocessor = DataPreprocessor(config_path=args.config)
    train_data, valid_data = preprocessor.preprocess_pipeline()

    if not train_data:
        print("\n⚠️ 데이터를 불러올 수 없습니다.")
        print("다음 단계를 확인해주세요:")
        print("1. AI HUB에서 고전문학 데이터 다운로드")
        print("2. configs/training_config.yaml에서 데이터 경로 설정")
        print("3. src/data/preprocessor.py의 load_classics_data() 구현")
        return

    # 2. 수동 작성 템플릿 생성
    if args.create_templates:
        print("\n📝 수동 작성 템플릿 생성 중...")
        converter = SocraticConverter()
        converter.create_manual_template(
            train_data,
            f"{args.output_dir}/manual_template.json",
            num_samples=args.template_count
        )
        print(f"   템플릿 생성 완료: {args.output_dir}/manual_template.json")
        print("   이 파일을 열어서 [사고유도]와 [사고로그] 내용을 작성해주세요.")

    # 3. 소크라틱 대화 자동 변환
    if args.convert_socratic:
        print(f"\n🔄 소크라틱 대화 변환 중 ({args.api_type} API 사용)...")
        converter = SocraticConverter(api_type=args.api_type)

        converted = converter.batch_convert(
            train_data,
            f"{args.output_dir}/train.jsonl"
        )

        if valid_data:
            converter.batch_convert(
                valid_data,
                f"{args.output_dir}/valid.jsonl"
            )

    print("\n" + "=" * 60)
    print("✅ 전처리 완료!")
    print("=" * 60)
    print(f"\n📁 출력 디렉토리: {args.output_dir}")
    print("\n다음 단계:")
    print("1. 수동 작성 템플릿 완성 (--create-templates 사용한 경우)")
    print("2. 데이터 품질 검토")
    print("3. python scripts/train.py 실행")


if __name__ == "__main__":
    main()
