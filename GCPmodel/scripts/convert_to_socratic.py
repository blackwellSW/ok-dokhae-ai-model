#!/usr/bin/env python3
"""
데이터를 소크라틱 대화 형식으로 변환하는 스크립트
"""

import argparse
import json
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.converter import SocraticConverter


def load_jsonl(file_path: str):
    """JSONL 파일 로드"""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def main():
    parser = argparse.ArgumentParser(description="소크라틱 대화 변환")

    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="입력 파일 경로 (JSONL)"
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="출력 파일 경로 (JSONL)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default="",
        help="Gemini API 키 (환경변수 우선)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="변환할 데이터 개수 (0=전체)"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="이미 변환된 데이터 스킵"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("📝 소크라틱 대화 변환")
    print("=" * 60)

    # 입력 데이터 로드
    print(f"\n📂 입력 파일: {args.input}")
    data = load_jsonl(args.input)
    print(f"   총 {len(data)}개 데이터 로드")

    # 제한 적용
    if args.limit > 0:
        data = data[:args.limit]
        print(f"   변환 대상: {len(data)}개 (제한 적용)")

    # 변환기 초기화
    print(f"\n🔧 Gemini API 클라이언트 초기화...")
    converter = SocraticConverter(
        api_key=args.api_key if args.api_key else None,
        api_type="gemini"
    )

    if not converter.client:
        print("\n⚠️ Gemini API 키가 설정되지 않았습니다!")
        print("\n다음 방법 중 하나를 사용하세요:")
        print("1. 환경변수: export GEMINI_API_KEY='your-api-key'")
        print("2. 커맨드라인: --api-key 'your-api-key'")
        print("\nAPI 키는 다음에서 발급:")
        print("https://console.cloud.google.com/apis/credentials")
        return

    print("✅ API 클라이언트 준비 완료")

    # 배치 변환 실행
    print(f"\n🔄 변환 시작...")
    print(f"   출력: {args.output}")

    converted_data = converter.batch_convert(
        data_list=data,
        output_path=args.output,
        skip_existing=args.skip_existing
    )

    # 결과 요약
    print("\n" + "=" * 60)
    print("✅ 변환 완료!")
    print("=" * 60)
    print(f"   총 변환: {len(converted_data)}개")
    print(f"   출력 파일: {args.output}")
    print("\n다음 단계:")
    print("1. 변환된 데이터 품질 확인")
    print("2. GCP Cloud Storage에 업로드")
    print("3. Vertex AI 학습 실행")


if __name__ == "__main__":
    main()
