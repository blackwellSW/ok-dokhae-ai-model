#!/usr/bin/env python3
"""
평가 결과 시각화 스크립트

evaluate_with_gemini.py의 결과를 차트로 시각화
"""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')  # GUI 없이 실행
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np


# ============================================================
# 한글 폰트 설정
# ============================================================

def setup_korean_font():
    """한글 폰트 설정"""
    # macOS
    font_paths = [
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/Library/Fonts/NanumGothic.ttf",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    ]

    for path in font_paths:
        if Path(path).exists():
            fm.fontManager.addfont(path)
            font_name = fm.FontProperties(fname=path).get_name()
            plt.rcParams['font.family'] = font_name
            plt.rcParams['axes.unicode_minus'] = False
            return font_name

    # fallback
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['axes.unicode_minus'] = False
    return 'sans-serif'


# ============================================================
# 시각화 함수들
# ============================================================

def create_radar_chart(rubric_scores: dict, output_path: str):
    """루브릭 항목별 레이더 차트"""
    categories = list(rubric_scores.keys())
    scores = [rubric_scores[k]["avg"] for k in categories]
    max_scores = [rubric_scores[k]["max_possible"] for k in categories]

    # 비율로 변환 (0~1)
    normalized = [s / m if m > 0 else 0 for s, m in zip(scores, max_scores)]

    # 짧은 라벨
    short_labels = [c.replace("_", "\n") for c in categories]

    N = len(categories)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    normalized += normalized[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    ax.fill(angles, normalized, alpha=0.25, color='#2196F3')
    ax.plot(angles, normalized, 'o-', linewidth=2, color='#2196F3')

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(short_labels, size=10)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(['20%', '40%', '60%', '80%', '100%'], size=8)

    # 점수 표시
    for angle, score, max_s, norm in zip(angles[:-1], scores, max_scores, normalized[:-1]):
        ax.text(angle, norm + 0.08, f'{score}/{max_s}',
                ha='center', va='center', fontsize=9, fontweight='bold')

    ax.set_title('루브릭 항목별 평가 결과', size=14, fontweight='bold', pad=20)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  레이더 차트 저장: {output_path}")


def create_tag_usage_chart(tag_stats: dict, output_path: str):
    """태그 사용률 바 차트"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # 1. 태그 사용률 막대 차트
    ax1 = axes[0]
    labels = ['[사고유도]', '[사고로그]', '둘 다']
    values = [
        tag_stats['induction_tag_rate'],
        tag_stats['log_tag_rate'],
        tag_stats['both_tags_rate']
    ]
    colors = ['#4CAF50', '#2196F3', '#FF9800']

    bars = ax1.bar(labels, values, color=colors, width=0.5, edgecolor='white')

    for bar, val in zip(bars, values):
        ax1.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + 1,
                 f'{val:.1f}%', ha='center', va='bottom', fontweight='bold')

    ax1.set_ylabel('사용률 (%)')
    ax1.set_title('태그 사용률', fontweight='bold')
    ax1.set_ylim(0, 110)
    ax1.axhline(y=80, color='gray', linestyle='--', alpha=0.5, label='목표 (80%)')
    ax1.legend()

    # 2. 질문 수 + 평가자 모드
    ax2 = axes[1]

    metrics = ['평균 질문 수', '평가자 모드\n(잘못된 동작)']
    metric_values = [
        tag_stats['avg_question_count'],
        tag_stats['evaluator_mode_rate']
    ]
    metric_colors = ['#4CAF50' if tag_stats['avg_question_count'] >= 2 else '#F44336',
                     '#F44336' if tag_stats['evaluator_mode_rate'] > 0 else '#4CAF50']

    bars2 = ax2.bar(metrics, metric_values, color=metric_colors, width=0.4, edgecolor='white')

    for bar, val in zip(bars2, metric_values):
        label = f'{val:.1f}개' if 'question' in str(val) else f'{val:.1f}%'
        if isinstance(val, float) and val == tag_stats['avg_question_count']:
            label = f'{val:.1f}개'
        else:
            label = f'{val:.1f}%'
        ax2.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + 0.2,
                 label, ha='center', va='bottom', fontweight='bold')

    ax2.set_title('질문 생성 / 모드 분석', fontweight='bold')
    ax2.set_ylabel('값')

    plt.suptitle('사고유도 모델 태그 분석', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  태그 분석 차트 저장: {output_path}")


def create_individual_scores_chart(results: list, output_path: str):
    """개별 테스트 점수 차트"""
    test_names = []
    percentages = []
    colors = []

    for item in results:
        tc = item["test_case"]
        rubric = item.get("rubric_evaluation", {})
        pct = rubric.get("백분율", 0)

        test_names.append(tc["name"].replace("_", "\n"))
        percentages.append(pct)

        if pct >= 70:
            colors.append('#4CAF50')
        elif pct >= 50:
            colors.append('#FF9800')
        else:
            colors.append('#F44336')

    fig, ax = plt.subplots(figsize=(12, 6))

    bars = ax.barh(test_names, percentages, color=colors, edgecolor='white', height=0.6)

    for bar, pct in zip(bars, percentages):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2.,
                f'{pct:.0f}%', ha='left', va='center', fontweight='bold')

    ax.set_xlabel('점수 (%)')
    ax.set_title('개별 테스트 케이스 루브릭 점수', fontweight='bold', fontsize=13)
    ax.set_xlim(0, 110)
    ax.axvline(x=70, color='green', linestyle='--', alpha=0.5, label='양호 기준 (70%)')
    ax.axvline(x=50, color='orange', linestyle='--', alpha=0.5, label='최소 기준 (50%)')
    ax.legend(loc='lower right')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  개별 점수 차트 저장: {output_path}")


def create_rubric_breakdown_chart(results: list, output_path: str):
    """루브릭 항목별 스택 바 차트"""
    from scripts.evaluate_with_gemini import THOUGHT_INDUCER_RUBRIC

    rubric_keys = list(THOUGHT_INDUCER_RUBRIC.keys())
    test_names = [r["test_case"]["name"].replace("_", "\n") for r in results]

    # 항목별 점수 수집
    data = {key: [] for key in rubric_keys}
    for item in results:
        rubric = item.get("rubric_evaluation", {})
        for key in rubric_keys:
            score = rubric.get(key, {}).get("score", 0) if isinstance(rubric.get(key), dict) else 0
            data[key].append(score)

    fig, ax = plt.subplots(figsize=(14, 7))

    x = np.arange(len(test_names))
    width = 0.15
    colors = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#F44336']

    for i, (key, scores) in enumerate(data.items()):
        offset = (i - len(rubric_keys) / 2 + 0.5) * width
        bars = ax.bar(x + offset, scores, width, label=key.replace("_", " "),
                      color=colors[i % len(colors)], edgecolor='white')

    ax.set_xlabel('테스트 케이스')
    ax.set_ylabel('점수')
    ax.set_title('루브릭 항목별 점수 분해', fontweight='bold', fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels(test_names, fontsize=9)
    ax.legend(loc='upper right', fontsize=8)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  항목별 분해 차트 저장: {output_path}")


def create_before_after_chart(before_file: str, after_file: str, output_path: str):
    """이전 모델 vs 새 모델 비교 차트"""
    with open(before_file, 'r', encoding='utf-8') as f:
        before = json.load(f)
    with open(after_file, 'r', encoding='utf-8') as f:
        after = json.load(f)

    before_summary = before.get("summary", before)
    after_summary = after.get("summary", after)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # 1. 태그 사용률 비교
    ax1 = axes[0]
    labels = ['[사고유도]\n태그율', '[사고로그]\n태그율', '평가자\n모드']

    before_tags = before_summary.get("tag_analysis", {})
    after_tags = after_summary.get("tag_analysis", {})

    before_vals = [
        before_tags.get('induction_tag_rate', 0),
        before_tags.get('log_tag_rate', 0),
        before_tags.get('evaluator_mode_rate', 100)
    ]
    after_vals = [
        after_tags.get('induction_tag_rate', 0),
        after_tags.get('log_tag_rate', 0),
        after_tags.get('evaluator_mode_rate', 0)
    ]

    x = np.arange(len(labels))
    width = 0.35

    ax1.bar(x - width / 2, before_vals, width, label='이전 모델', color='#F44336', alpha=0.8)
    ax1.bar(x + width / 2, after_vals, width, label='새 모델', color='#4CAF50', alpha=0.8)

    ax1.set_ylabel('비율 (%)')
    ax1.set_title('태그 사용률 비교', fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.legend()
    ax1.set_ylim(0, 110)

    # 2. 전체 점수 비교
    ax2 = axes[1]

    before_overall = before_summary.get("overall", {})
    after_overall = after_summary.get("overall", {})

    metrics = ['평균 점수', '최고 점수']
    before_scores = [
        before_overall.get('avg_percentage', 0),
        before_overall.get('max_percentage', 0)
    ]
    after_scores = [
        after_overall.get('avg_percentage', 0),
        after_overall.get('max_percentage', 0)
    ]

    x2 = np.arange(len(metrics))
    ax2.bar(x2 - width / 2, before_scores, width, label='이전 모델', color='#F44336', alpha=0.8)
    ax2.bar(x2 + width / 2, after_scores, width, label='새 모델', color='#4CAF50', alpha=0.8)

    ax2.set_ylabel('점수 (%)')
    ax2.set_title('루브릭 점수 비교', fontweight='bold')
    ax2.set_xticks(x2)
    ax2.set_xticklabels(metrics)
    ax2.legend()
    ax2.set_ylim(0, 110)

    plt.suptitle('모델 성능 비교: Before vs After', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  비교 차트 저장: {output_path}")


# ============================================================
# 전체 시각화 실행
# ============================================================

def visualize_report(report_path: str, output_dir: str = None):
    """리포트 파일로부터 전체 시각화 생성"""
    setup_korean_font()

    with open(report_path, 'r', encoding='utf-8') as f:
        report = json.load(f)

    if output_dir is None:
        output_dir = str(Path(report_path).parent / "charts")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    summary = report["summary"]
    results = report["detailed_results"]

    print("\n" + "=" * 70)
    print("  평가 결과 시각화")
    print("=" * 70)

    # 1. 레이더 차트
    if summary.get("rubric_scores"):
        create_radar_chart(
            summary["rubric_scores"],
            f"{output_dir}/radar_rubric.png"
        )

    # 2. 태그 분석 차트
    if summary.get("tag_analysis"):
        create_tag_usage_chart(
            summary["tag_analysis"],
            f"{output_dir}/tag_analysis.png"
        )

    # 3. 개별 점수 차트
    if results:
        create_individual_scores_chart(
            results,
            f"{output_dir}/individual_scores.png"
        )

    # 4. 항목별 분해 차트
    if results:
        try:
            create_rubric_breakdown_chart(
                results,
                f"{output_dir}/rubric_breakdown.png"
            )
        except Exception as e:
            print(f"  항목별 분해 차트 생성 실패: {e}")

    print("\n" + "=" * 70)
    print(f"  시각화 완료! 저장 위치: {output_dir}")
    print("=" * 70)


# ============================================================
# 메인
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="평가 결과 시각화")

    parser.add_argument(
        "--report", type=str, required=True,
        help="평가 리포트 JSON 파일 경로"
    )
    parser.add_argument(
        "--output-dir", type=str, default="",
        help="차트 저장 디렉토리 (기본: 리포트와 같은 위치/charts)"
    )
    parser.add_argument(
        "--before", type=str, default="",
        help="이전 모델 리포트 (비교용)"
    )

    args = parser.parse_args()

    # 시각화
    visualize_report(
        report_path=args.report,
        output_dir=args.output_dir or None
    )

    # Before/After 비교
    if args.before and Path(args.before).exists():
        output_dir = args.output_dir or str(Path(args.report).parent / "charts")
        create_before_after_chart(
            before_file=args.before,
            after_file=args.report,
            output_path=f"{output_dir}/before_after_comparison.png"
        )


if __name__ == "__main__":
    main()
