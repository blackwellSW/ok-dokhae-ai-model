#!/usr/bin/env python3
"""
Gemma 3 파인튜닝 실행 스크립트
"""

import argparse
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.model.trainer import GemmaTrainer, TrainingConfig


def main():
    parser = argparse.ArgumentParser(description="Gemma 3 파인튜닝")

    # 데이터 경로
    parser.add_argument(
        "--train-data",
        type=str,
        default="",
        help="학습 데이터 경로 (JSONL)"
    )
    parser.add_argument(
        "--valid-data",
        type=str,
        default="",
        help="검증 데이터 경로 (JSONL)"
    )

    # 모델 설정
    parser.add_argument(
        "--model-name",
        type=str,
        default="google/gemma-3-9b-it",
        help="베이스 모델 이름"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="models/gemma_finetuned",
        help="모델 저장 경로"
    )

    # 학습 설정
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="학습 에폭 수"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=4,
        help="배치 사이즈"
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=2e-4,
        help="학습률"
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=1024,
        help="최대 시퀀스 길이"
    )

    # LoRA 설정
    parser.add_argument(
        "--lora-r",
        type=int,
        default=16,
        help="LoRA rank"
    )
    parser.add_argument(
        "--lora-alpha",
        type=int,
        default=32,
        help="LoRA alpha"
    )

    # 기타
    parser.add_argument(
        "--config",
        type=str,
        default="",
        help="YAML 설정 파일 경로 (설정 파일 사용 시)"
    )
    parser.add_argument(
        "--resume",
        type=str,
        default="",
        help="체크포인트에서 재시작"
    )

    args = parser.parse_args()

    # 설정 파일 또는 커맨드라인 인자 사용
    if args.config:
        print(f"📄 설정 파일 사용: {args.config}")
        trainer = GemmaTrainer.from_yaml(args.config)
    else:
        config = TrainingConfig(
            model_name=args.model_name,
            train_data_path=args.train_data,
            valid_data_path=args.valid_data,
            output_dir=args.output_dir,
            num_train_epochs=args.epochs,
            per_device_train_batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            max_length=args.max_length,
            lora_r=args.lora_r,
            lora_alpha=args.lora_alpha
        )
        trainer = GemmaTrainer(config)

    # 데이터 경로 확인
    if not trainer.config.train_data_path:
        print("=" * 60)
        print("⚠️ 학습 데이터 경로가 설정되지 않았습니다!")
        print("=" * 60)
        print("\n다음 방법 중 하나를 사용하세요:\n")
        print("1. 커맨드라인 인자:")
        print("   python scripts/train.py --train-data data/processed/train.jsonl\n")
        print("2. 설정 파일:")
        print("   python scripts/train.py --config configs/training_config.yaml")
        print("   (training_config.yaml에서 data.train_data_path 설정)\n")
        print("3. 데이터 준비:")
        print("   - AI HUB에서 고전문학 데이터 다운로드")
        print("   - python scripts/preprocess.py 실행")
        print("=" * 60)
        return

    # 학습 실행
    print("=" * 60)
    print("🚀 Gemma 3 파인튜닝 시작")
    print("=" * 60)
    print(f"   모델: {trainer.config.model_name}")
    print(f"   학습 데이터: {trainer.config.train_data_path}")
    print(f"   출력 경로: {trainer.config.output_dir}")
    print(f"   에폭: {trainer.config.num_train_epochs}")
    print(f"   배치 사이즈: {trainer.config.per_device_train_batch_size}")
    print(f"   학습률: {trainer.config.learning_rate}")
    print("=" * 60)

    model_path = trainer.train(
        resume_from_checkpoint=args.resume if args.resume else None
    )

    if model_path:
        print("=" * 60)
        print(f"✅ 학습 완료!")
        print(f"   모델 저장 위치: {model_path}")
        print("=" * 60)


if __name__ == "__main__":
    main()
