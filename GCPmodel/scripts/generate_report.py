#!/usr/bin/env python3
"""
평가 결과 리포트 생성 스크립트
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.integration.pipeline import IntegratedPipeline


def main():
    parser = argparse.ArgumentParser(description="평가 리포트 생성")

    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="평가 결과 파일 (JSON 또는 JSONL)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs/reports",
        help="리포트 출력 디렉토리"
    )
    parser.add_argument(
        "--type",
        type=str,
        choices=["student", "teacher", "both"],
        default="both",
        help="리포트 유형"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["markdown", "html"],
        default="markdown",
        help="출력 형식"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("📊 리포트 생성")
    print("=" * 60)

    # 평가 결과 로드
    input_path = Path(args.input)
    results = load_results(input_path)

    if not results:
        print("⚠️ 평가 결과를 불러올 수 없습니다.")
        return

    print(f"   {len(results)}개 평가 결과 로드")

    # 출력 디렉토리 생성
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 파이프라인 (리포트 생성용)
    pipeline = IntegratedPipeline()

    # 리포트 생성
    for i, result in enumerate(results):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"report_{i+1:03d}_{timestamp}"

        if args.type in ["student", "both"]:
            student_report = pipeline.generate_student_report(result)
            save_report(student_report, output_dir / f"{base_name}_student", args.format)

        if args.type in ["teacher", "both"]:
            teacher_report = pipeline.generate_teacher_report(result)
            save_report(teacher_report, output_dir / f"{base_name}_teacher", args.format)

    # 통계 요약 리포트 생성
    if len(results) > 1:
        summary = generate_summary_report(results)
        save_report(summary, output_dir / f"summary_{timestamp}", args.format)

    print(f"\n✅ 리포트 생성 완료!")
    print(f"📁 출력 디렉토리: {output_dir}")


def load_results(input_path: Path) -> list:
    """평가 결과 로드"""
    results = []

    if input_path.suffix == '.json':
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                results = data
            else:
                results = [data]

    elif input_path.suffix == '.jsonl':
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))

    return results


def save_report(content: str, output_path: Path, format_type: str):
    """리포트 저장"""
    if format_type == "markdown":
        path = output_path.with_suffix('.md')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    elif format_type == "html":
        path = output_path.with_suffix('.html')
        html_content = markdown_to_html(content)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html_content)

    print(f"   📄 {path.name}")


def markdown_to_html(markdown_content: str) -> str:
    """마크다운을 HTML로 변환"""
    try:
        import markdown
        html_body = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code'])
    except ImportError:
        # markdown 패키지 없으면 기본 변환
        html_body = f"<pre>{markdown_content}</pre>"

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>평가 리포트</title>
    <style>
        body {{
            font-family: 'Noto Sans KR', sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }}
        h1, h2, h3 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        code {{ background-color: #f4f4f4; padding: 2px 5px; }}
        pre {{ background-color: #f4f4f4; padding: 10px; overflow-x: auto; }}
    </style>
</head>
<body>
{html_body}
</body>
</html>"""


def generate_summary_report(results: list) -> str:
    """통계 요약 리포트 생성"""
    report = "# 📊 평가 통계 요약\n\n"
    report += f"**총 평가 건수**: {len(results)}건\n\n"

    # 등급 분포
    grades = {}
    total_scores = []
    qual_scores = []
    quan_scores = []

    for result in results:
        integrated = result.get('통합_평가', {})
        grade = integrated.get('등급', 'N/A')
        grades[grade] = grades.get(grade, 0) + 1

        if integrated.get('총점'):
            total_scores.append(integrated['총점'])
        if integrated.get('질적_점수'):
            qual_scores.append(integrated['질적_점수'])
        if integrated.get('정량_점수'):
            quan_scores.append(integrated['정량_점수'])

    report += "## 등급 분포\n\n"
    report += "| 등급 | 인원 | 비율 |\n"
    report += "|------|------|------|\n"
    for grade in ['A+', 'A', 'B+', 'B', 'C+', 'C']:
        count = grades.get(grade, 0)
        ratio = count / len(results) * 100 if results else 0
        report += f"| {grade} | {count} | {ratio:.1f}% |\n"

    # 점수 통계
    if total_scores:
        report += "\n## 점수 통계\n\n"
        report += f"- **평균 총점**: {sum(total_scores)/len(total_scores):.1f}\n"
        report += f"- **최고점**: {max(total_scores):.1f}\n"
        report += f"- **최저점**: {min(total_scores):.1f}\n"

        if qual_scores:
            report += f"- **평균 질적 점수**: {sum(qual_scores)/len(qual_scores):.1f}/70\n"
        if quan_scores:
            report += f"- **평균 정량 점수**: {sum(quan_scores)/len(quan_scores):.1f}/30\n"

    report += f"\n---\n생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

    return report


if __name__ == "__main__":
    main()
