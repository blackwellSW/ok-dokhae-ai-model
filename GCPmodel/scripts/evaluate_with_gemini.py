#!/usr/bin/env python3
"""
Gemini를 활용한 Gemma 모델 응답 루브릭 평가 스크립트

흐름:
1. Gemma 모델 엔드포인트에 테스트 질문 전송
2. Gemma 응답을 Gemini가 루브릭 기반으로 평가
3. 평가 결과를 JSON + 시각화 리포트로 저장
"""

import argparse
import json
import os
import time
import re
import subprocess
import requests
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

import google.generativeai as genai


# ============================================================
# 루브릭 정의
# ============================================================

THOUGHT_INDUCER_RUBRIC = {
    "사고유도_태그_사용": {
        "description": "[사고유도] 태그가 적절하게 사용되었는가",
        "max_score": 20,
        "criteria": {
            "20": "[사고유도] 태그가 있고, 내용이 충실하며 단계적 질문이 포함됨",
            "15": "[사고유도] 태그가 있고, 질문이 있지만 단계성이 부족",
            "10": "[사고유도] 태그가 있지만 내용이 빈약",
            "5": "[사고유도] 태그가 없지만 유도 질문이 일부 존재",
            "0": "[사고유도] 태그도 없고 유도 질문도 없음"
        }
    },
    "사고로그_태그_사용": {
        "description": "[사고로그] 태그가 적절하게 사용되었는가",
        "max_score": 15,
        "criteria": {
            "15": "[사고로그] 태그가 있고, 심화 질문이나 관찰 내용이 풍부",
            "10": "[사고로그] 태그가 있고, 기본적인 심화 내용 포함",
            "5": "[사고로그] 태그가 있지만 내용이 빈약",
            "0": "[사고로그] 태그가 없음"
        }
    },
    "질문의_질": {
        "description": "학생의 사고를 유도하는 질문의 질적 수준",
        "max_score": 25,
        "criteria": {
            "25": "다층적이고 단계적인 질문 (기본→심화→통합). 열린 질문 3개 이상",
            "20": "단계적 질문이 있지만 일부 직접적 답변 포함. 열린 질문 2개 이상",
            "15": "기본적 질문은 있지만 단계성 부족",
            "10": "질문이 있지만 너무 직접적이거나 단순함",
            "5": "질문이 거의 없고 설명 위주",
            "0": "질문 없이 직접 답을 제공"
        }
    },
    "소크라틱_대화_적합성": {
        "description": "소크라틱 교수법에 얼마나 부합하는가",
        "max_score": 20,
        "criteria": {
            "20": "직접 답을 주지 않고 학생이 스스로 깨달을 수 있도록 완벽히 유도",
            "15": "대부분 유도하지만 일부 직접적 정보 제공",
            "10": "유도와 직접 설명이 혼합됨",
            "5": "직접 설명 위주, 유도 질문 부족",
            "0": "완전히 직접적 답변/평가 형식"
        }
    },
    "내용_정확성_적절성": {
        "description": "고전문학 내용에 대한 정확성과 적절성",
        "max_score": 20,
        "criteria": {
            "20": "내용이 정확하고, 맥락에 적합하며, 학생 수준에 맞게 조절됨",
            "15": "내용이 정확하지만 맥락 활용이 부족",
            "10": "대체로 정확하나 일부 부정확한 내용 포함",
            "5": "내용에 오류가 있거나 맥락과 맞지 않음",
            "0": "내용이 부정확하거나 관련 없음"
        }
    }
}


# ============================================================
# 테스트 케이스 정의
# ============================================================

DEFAULT_TEST_CASES = [
    {
        "name": "춘향전_신분",
        "context": "춘향전",
        "student_input": "춘향전에서 이몽룡이 신분을 숨긴 이유가 뭔가요?",
    },
    {
        "name": "심청전_효",
        "context": "심청전",
        "student_input": "심청이는 왜 인당수에 몸을 던졌나요?",
    },
    {
        "name": "흥부전_비교",
        "context": "흥부전",
        "student_input": "흥부와 놀부의 차이점은 무엇인가요?",
    },
    {
        "name": "의인화_기법",
        "context": "고전문학 표현기법",
        "student_input": "의인화 기법이 뭔가요? 예시를 들어주세요.",
    },
    {
        "name": "춘향전_주제",
        "context": "춘향전",
        "student_input": "춘향전의 주제가 뭐예요?",
    },
    {
        "name": "작품_비교",
        "context": "고전문학",
        "student_input": "춘향전과 심청전의 공통점과 차이점은 무엇인가요?",
    },
    {
        "name": "소나무_상징",
        "context": "고전시가",
        "student_input": "고전문학에서 소나무가 자주 등장하는 이유가 뭔가요?",
    },
    {
        "name": "판소리_특징",
        "context": "판소리",
        "student_input": "판소리의 특징이 뭐예요? 일반 노래와 뭐가 달라요?",
    },
]


# ============================================================
# Gemma 모델 호출
# ============================================================

def get_gemma_response(
    endpoint_id: str,
    project_number: str,
    student_input: str,
    context: str = "",
    location: str = "us-central1"
) -> Dict:
    """
    Gemma 튜닝 모델 엔드포인트 호출

    Returns:
        {"response": str, "inference_time": float, "tokens": dict}
    """
    access_token = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True, text=True
    ).stdout.strip()

    api_url = (
        f"https://{location}-aiplatform.googleapis.com/v1/"
        f"projects/{project_number}/locations/{location}/"
        f"endpoints/{endpoint_id}:predict"
    )

    # Gemma 학습 데이터와 동일한 프롬프트 형식
    prompt = f"""<start_of_turn>user
다음 지문을 읽고 질문에 답하세요. 학생의 사고를 유도하며 답변을 작성하세요.

[작품: {context}]
{student_input}<end_of_turn>
<start_of_turn>model
"""

    request_body = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "temperature": 0.7,
            "maxOutputTokens": 512,
            "topP": 0.9
        }
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    start_time = time.time()

    try:
        response = requests.post(
            api_url, json=request_body,
            headers=headers, timeout=60
        )
        inference_time = time.time() - start_time

        if response.status_code == 200:
            result = response.json()
            # Vertex AI predict 응답 형식
            predictions = result.get("predictions", [])
            response_text = predictions[0] if predictions else ""

            return {
                "response": response_text,
                "inference_time": round(inference_time, 3),
                "status": "success"
            }
        else:
            return {
                "response": "",
                "inference_time": round(inference_time, 3),
                "status": "error",
                "error": f"HTTP {response.status_code}: {response.text[:200]}"
            }

    except Exception as e:
        return {
            "response": "",
            "inference_time": 0,
            "status": "error",
            "error": str(e)
        }


# ============================================================
# Gemini 루브릭 평가
# ============================================================

class GeminiRubricEvaluator:
    """Gemini를 활용한 루브릭 기반 평가"""

    def __init__(self, api_key: str = None, model_name: str = "gemini-2.0-flash-exp"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY가 필요합니다.")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)
        self.rubric = THOUGHT_INDUCER_RUBRIC

    def evaluate_response(
        self,
        student_input: str,
        model_response: str,
        context: str = ""
    ) -> Dict:
        """
        Gemma 모델의 응답을 루브릭으로 평가

        Args:
            student_input: 학생 질문
            model_response: Gemma 모델의 응답
            context: 작품 맥락

        Returns:
            평가 결과 딕셔너리
        """
        rubric_text = self._format_rubric()

        prompt = f"""당신은 고전문학 AI 교육 시스템의 품질 평가 전문가입니다.
아래 루브릭을 사용하여 AI 모델의 응답을 엄격하게 평가하세요.

## 평가 루브릭
{rubric_text}

## 맥락
- 작품/주제: {context or "고전문학"}
- AI 모델의 역할: 사고유도 교사 (직접 답을 주지 않고 질문으로 유도)

## 학생 질문
{student_input}

## AI 모델 응답 (평가 대상)
{model_response}

## 평가 지침
1. 각 루브릭 항목별로 점수를 매기세요.
2. 반드시 아래 JSON 형식으로만 출력하세요.
3. 피드백은 한국어로 구체적으로 작성하세요.
4. 점수는 루브릭의 기준에 따라 정확히 부여하세요.

## 출력 형식 (JSON만 출력)
{{
  "사고유도_태그_사용": {{
    "score": 0,
    "feedback": "..."
  }},
  "사고로그_태그_사용": {{
    "score": 0,
    "feedback": "..."
  }},
  "질문의_질": {{
    "score": 0,
    "feedback": "..."
  }},
  "소크라틱_대화_적합성": {{
    "score": 0,
    "feedback": "..."
  }},
  "내용_정확성_적절성": {{
    "score": 0,
    "feedback": "..."
  }},
  "총평": "...",
  "강점": ["...", "..."],
  "개선점": ["...", "..."]
}}"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.2,
                    "max_output_tokens": 1024,
                }
            )

            evaluation = self._parse_json_response(response.text)

            # 총점 계산
            total_score = 0
            max_total = 0
            for key, rubric_item in self.rubric.items():
                item_eval = evaluation.get(key, {})
                score = item_eval.get("score", 0)
                total_score += score
                max_total += rubric_item["max_score"]

            evaluation["총점"] = total_score
            evaluation["만점"] = max_total
            evaluation["백분율"] = round(total_score / max_total * 100, 1) if max_total > 0 else 0

            return evaluation

        except Exception as e:
            print(f"  평가 오류: {e}")
            return self._fallback_evaluation(str(e))

    def _format_rubric(self) -> str:
        """루브릭을 프롬프트용 텍스트로 변환"""
        text = ""
        for key, item in self.rubric.items():
            text += f"\n### {key} (만점: {item['max_score']}점)\n"
            text += f"설명: {item['description']}\n"
            for score, desc in item["criteria"].items():
                text += f"  - {score}점: {desc}\n"
        return text

    def _parse_json_response(self, response_text: str) -> Dict:
        """Gemini 응답에서 JSON 추출"""
        json_text = response_text

        # ```json ... ``` 블록 추출
        if "```json" in json_text:
            json_text = json_text.split("```json")[1].split("```")[0]
        elif "```" in json_text:
            json_text = json_text.split("```")[1].split("```")[0]

        try:
            return json.loads(json_text.strip())
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 정규식으로 점수 추출
            return self._extract_scores_from_text(response_text)

    def _extract_scores_from_text(self, text: str) -> Dict:
        """텍스트에서 점수 추출 (fallback)"""
        result = {}
        for key in self.rubric:
            match = re.search(rf'"{key}".*?"score":\s*(\d+)', text, re.DOTALL)
            score = int(match.group(1)) if match else 0
            result[key] = {"score": score, "feedback": "JSON 파싱 실패로 자동 추출"}
        return result

    def _fallback_evaluation(self, error_msg: str) -> Dict:
        """평가 실패 시 폴백"""
        result = {}
        for key in self.rubric:
            result[key] = {"score": 0, "feedback": f"평가 실패: {error_msg}"}
        result["총점"] = 0
        result["만점"] = 100
        result["백분율"] = 0
        result["총평"] = f"평가 중 오류 발생: {error_msg}"
        return result


# ============================================================
# 기본 태그 분석 (Gemini 없이도 동작)
# ============================================================

def analyze_tags(response: str) -> Dict:
    """응답에서 태그 존재 여부 및 내용 분석"""
    has_induction = "[사고유도]" in response
    has_log = "[사고로그]" in response

    # 사고유도 내용 추출
    induction_content = ""
    if has_induction:
        match = re.search(r'\[사고유도\]\s*(.*?)(?=\[사고로그\]|$)', response, re.DOTALL)
        if match:
            induction_content = match.group(1).strip()

    # 사고로그 내용 추출
    log_content = ""
    if has_log:
        match = re.search(r'\[사고로그\]\s*(.*?)$', response, re.DOTALL)
        if match:
            log_content = match.group(1).strip()

    # 질문 수 카운트
    question_count = response.count("?") + response.count("까요")

    return {
        "has_induction_tag": has_induction,
        "has_log_tag": has_log,
        "has_both_tags": has_induction and has_log,
        "induction_length": len(induction_content),
        "log_length": len(log_content),
        "question_count": question_count,
        "induction_content": induction_content[:300],
        "log_content": log_content[:300],
        "is_evaluator_mode": any(
            keyword in response
            for keyword in ["전달하지 못하고", "부족하여", "평가를 받", "점수"]
        )
    }


# ============================================================
# 전체 평가 파이프라인
# ============================================================

def run_full_evaluation(
    endpoint_id: str,
    project_number: str,
    location: str = "us-central1",
    test_cases: List[Dict] = None,
    output_dir: str = "outputs/evaluation_reports",
    gemini_api_key: str = None,
    skip_gemma: bool = False,
    gemma_responses_file: str = None
) -> Dict:
    """
    전체 평가 파이프라인 실행

    Args:
        endpoint_id: Gemma 모델 엔드포인트 ID
        project_number: GCP 프로젝트 번호
        location: Vertex AI 리전
        test_cases: 테스트 케이스 리스트
        output_dir: 결과 저장 디렉토리
        gemini_api_key: Gemini API 키
        skip_gemma: Gemma 호출 건너뛰기 (이전 응답 사용)
        gemma_responses_file: 이전 Gemma 응답 파일

    Returns:
        전체 평가 결과
    """
    if test_cases is None:
        test_cases = DEFAULT_TEST_CASES

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("\n" + "=" * 70)
    print("  Gemma 모델 루브릭 평가 시스템")
    print("=" * 70)
    print(f"테스트 케이스: {len(test_cases)}개")
    print(f"결과 저장: {output_path}")
    print("=" * 70)

    # ---- 1단계: Gemma 응답 수집 ----
    print("\n[1/3] Gemma 모델 응답 수집")
    print("-" * 40)

    gemma_results = []

    if skip_gemma and gemma_responses_file:
        # 이전 응답 로드
        with open(gemma_responses_file, 'r', encoding='utf-8') as f:
            gemma_results = json.load(f)
        print(f"  이전 응답 로드: {len(gemma_results)}개")

    else:
        for i, tc in enumerate(test_cases, 1):
            print(f"\n  [{i}/{len(test_cases)}] {tc['name']}")
            print(f"  질문: {tc['student_input']}")

            result = get_gemma_response(
                endpoint_id=endpoint_id,
                project_number=project_number,
                student_input=tc["student_input"],
                context=tc.get("context", ""),
                location=location
            )

            gemma_results.append({
                "test_case": tc,
                "gemma_response": result
            })

            if result["status"] == "success":
                print(f"  응답 ({result['inference_time']}초): {result['response'][:80]}...")
            else:
                print(f"  오류: {result.get('error', 'Unknown')}")

            time.sleep(1)

        # Gemma 응답 저장
        gemma_file = output_path / f"gemma_responses_{timestamp}.json"
        with open(gemma_file, 'w', encoding='utf-8') as f:
            json.dump(gemma_results, f, ensure_ascii=False, indent=2)
        print(f"\n  Gemma 응답 저장: {gemma_file}")

    # ---- 2단계: 기본 태그 분석 ----
    print("\n[2/3] 태그 분석")
    print("-" * 40)

    for item in gemma_results:
        response_text = item["gemma_response"].get("response", "")
        item["tag_analysis"] = analyze_tags(response_text)

        tc_name = item["test_case"]["name"]
        tags = item["tag_analysis"]
        print(f"  {tc_name}: "
              f"[사고유도]={'O' if tags['has_induction_tag'] else 'X'} "
              f"[사고로그]={'O' if tags['has_log_tag'] else 'X'} "
              f"질문={tags['question_count']}개 "
              f"평가모드={'O' if tags['is_evaluator_mode'] else 'X'}")

    # ---- 3단계: Gemini 루브릭 평가 ----
    print("\n[3/3] Gemini 루브릭 평가")
    print("-" * 40)

    try:
        evaluator = GeminiRubricEvaluator(api_key=gemini_api_key)

        for i, item in enumerate(gemma_results, 1):
            tc = item["test_case"]
            response_text = item["gemma_response"].get("response", "")

            if not response_text:
                print(f"  [{i}] {tc['name']}: 응답 없음, 건너뜀")
                item["rubric_evaluation"] = evaluator._fallback_evaluation("응답 없음")
                continue

            print(f"  [{i}/{len(gemma_results)}] {tc['name']} 평가 중...")

            evaluation = evaluator.evaluate_response(
                student_input=tc["student_input"],
                model_response=response_text,
                context=tc.get("context", "")
            )

            item["rubric_evaluation"] = evaluation

            print(f"    총점: {evaluation.get('총점', 0)}/{evaluation.get('만점', 100)} "
                  f"({evaluation.get('백분율', 0)}%)")

            time.sleep(1)  # API rate limit

    except Exception as e:
        print(f"  Gemini 평가 실패: {e}")
        print("  기본 태그 분석 결과만 사용합니다.")
        for item in gemma_results:
            if "rubric_evaluation" not in item:
                item["rubric_evaluation"] = {"error": str(e)}

    # ---- 결과 종합 ----
    print("\n" + "=" * 70)
    print("  평가 결과 종합")
    print("=" * 70)

    summary = generate_summary(gemma_results)
    print_summary(summary)

    # ---- 결과 저장 ----
    full_report = {
        "timestamp": timestamp,
        "config": {
            "endpoint_id": endpoint_id,
            "project_number": project_number,
            "location": location,
            "test_case_count": len(test_cases)
        },
        "summary": summary,
        "detailed_results": gemma_results
    }

    # JSON 저장
    report_file = output_path / f"evaluation_report_{timestamp}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(full_report, f, ensure_ascii=False, indent=2)
    print(f"\n  JSON 리포트: {report_file}")

    # 마크다운 저장
    md_file = output_path / f"evaluation_report_{timestamp}.md"
    md_content = generate_markdown_report(full_report)
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"  Markdown 리포트: {md_file}")

    print("\n" + "=" * 70)
    print("  평가 완료!")
    print("=" * 70)

    return full_report


# ============================================================
# 결과 종합
# ============================================================

def generate_summary(results: List[Dict]) -> Dict:
    """평가 결과 종합 요약"""
    successful = [r for r in results if r["gemma_response"].get("status") == "success"]
    total = len(results)

    # 태그 분석 요약
    tag_stats = {
        "induction_tag_rate": sum(
            1 for r in successful if r["tag_analysis"]["has_induction_tag"]
        ) / len(successful) * 100 if successful else 0,
        "log_tag_rate": sum(
            1 for r in successful if r["tag_analysis"]["has_log_tag"]
        ) / len(successful) * 100 if successful else 0,
        "both_tags_rate": sum(
            1 for r in successful if r["tag_analysis"]["has_both_tags"]
        ) / len(successful) * 100 if successful else 0,
        "avg_question_count": sum(
            r["tag_analysis"]["question_count"] for r in successful
        ) / len(successful) if successful else 0,
        "evaluator_mode_rate": sum(
            1 for r in successful if r["tag_analysis"]["is_evaluator_mode"]
        ) / len(successful) * 100 if successful else 0,
    }

    # 루브릭 평가 요약
    rubric_scores = {}
    for key in THOUGHT_INDUCER_RUBRIC:
        scores = [
            r.get("rubric_evaluation", {}).get(key, {}).get("score", 0)
            for r in successful
            if isinstance(r.get("rubric_evaluation", {}).get(key), dict)
        ]
        if scores:
            rubric_scores[key] = {
                "avg": round(sum(scores) / len(scores), 1),
                "max": max(scores),
                "min": min(scores),
                "max_possible": THOUGHT_INDUCER_RUBRIC[key]["max_score"]
            }

    # 총점 요약
    total_scores = [
        r.get("rubric_evaluation", {}).get("총점", 0)
        for r in successful
        if "rubric_evaluation" in r and "총점" in r.get("rubric_evaluation", {})
    ]

    percentages = [
        r.get("rubric_evaluation", {}).get("백분율", 0)
        for r in successful
        if "rubric_evaluation" in r and "백분율" in r.get("rubric_evaluation", {})
    ]

    # 추론 시간 요약
    inference_times = [
        r["gemma_response"]["inference_time"]
        for r in successful
    ]

    return {
        "total_tests": total,
        "successful_tests": len(successful),
        "failed_tests": total - len(successful),
        "tag_analysis": tag_stats,
        "rubric_scores": rubric_scores,
        "overall": {
            "avg_total_score": round(sum(total_scores) / len(total_scores), 1) if total_scores else 0,
            "avg_percentage": round(sum(percentages) / len(percentages), 1) if percentages else 0,
            "max_percentage": round(max(percentages), 1) if percentages else 0,
            "min_percentage": round(min(percentages), 1) if percentages else 0,
        },
        "performance": {
            "avg_inference_time": round(sum(inference_times) / len(inference_times), 3) if inference_times else 0,
        }
    }


def print_summary(summary: Dict):
    """요약 출력"""
    tags = summary["tag_analysis"]
    overall = summary["overall"]

    print(f"\n  테스트: {summary['successful_tests']}/{summary['total_tests']} 성공")
    print(f"\n  --- 태그 분석 ---")
    print(f"  [사고유도] 태그율: {tags['induction_tag_rate']:.1f}%")
    print(f"  [사고로그] 태그율: {tags['log_tag_rate']:.1f}%")
    print(f"  둘 다 있음: {tags['both_tags_rate']:.1f}%")
    print(f"  평균 질문 수: {tags['avg_question_count']:.1f}개")
    print(f"  평가자 모드: {tags['evaluator_mode_rate']:.1f}%")

    print(f"\n  --- 루브릭 평가 ---")
    for key, scores in summary.get("rubric_scores", {}).items():
        print(f"  {key}: 평균 {scores['avg']}/{scores['max_possible']} "
              f"(최고: {scores['max']}, 최저: {scores['min']})")

    print(f"\n  --- 종합 ---")
    print(f"  평균 점수: {overall['avg_percentage']:.1f}%")
    print(f"  최고: {overall['max_percentage']:.1f}% / 최저: {overall['min_percentage']:.1f}%")
    print(f"  평균 추론 시간: {summary['performance']['avg_inference_time']}초")


# ============================================================
# 마크다운 리포트 생성
# ============================================================

def generate_markdown_report(report: Dict) -> str:
    """마크다운 형식 리포트 생성"""
    summary = report["summary"]
    tags = summary["tag_analysis"]
    overall = summary["overall"]

    md = f"""# Gemma 사고유도 모델 평가 리포트

**평가 일시**: {report['timestamp']}
**엔드포인트**: {report['config']['endpoint_id']}
**테스트 수**: {summary['total_tests']}개

---

## 1. 종합 결과

| 지표 | 값 |
|------|-----|
| 평균 점수 | **{overall['avg_percentage']:.1f}%** |
| 최고 점수 | {overall['max_percentage']:.1f}% |
| 최저 점수 | {overall['min_percentage']:.1f}% |
| 성공률 | {summary['successful_tests']}/{summary['total_tests']} |

## 2. 태그 사용 분석

| 태그 | 사용률 |
|------|--------|
| [사고유도] | {tags['induction_tag_rate']:.1f}% |
| [사고로그] | {tags['log_tag_rate']:.1f}% |
| 둘 다 있음 | {tags['both_tags_rate']:.1f}% |
| 평균 질문 수 | {tags['avg_question_count']:.1f}개 |
| 평가자 모드 (잘못된 동작) | {tags['evaluator_mode_rate']:.1f}% |

## 3. 루브릭 항목별 점수

| 항목 | 평균 | 만점 | 최고 | 최저 |
|------|------|------|------|------|
"""

    for key, scores in summary.get("rubric_scores", {}).items():
        md += f"| {key} | {scores['avg']} | {scores['max_possible']} | {scores['max']} | {scores['min']} |\n"

    md += f"""
## 4. 개별 테스트 결과

"""

    for i, item in enumerate(report.get("detailed_results", []), 1):
        tc = item["test_case"]
        response = item["gemma_response"].get("response", "응답 없음")
        tag_info = item.get("tag_analysis", {})
        rubric = item.get("rubric_evaluation", {})

        md += f"""### 테스트 {i}: {tc['name']}

**질문**: {tc['student_input']}
**맥락**: {tc.get('context', 'N/A')}
**점수**: {rubric.get('백분율', 0)}% ({rubric.get('총점', 0)}/{rubric.get('만점', 100)})

**태그**: [사고유도]={'O' if tag_info.get('has_induction_tag') else 'X'} | [사고로그]={'O' if tag_info.get('has_log_tag') else 'X'} | 질문 {tag_info.get('question_count', 0)}개

<details>
<summary>모델 응답 보기</summary>

```
{response[:500]}
```

</details>

<details>
<summary>루브릭 평가 상세</summary>

"""
        for key in THOUGHT_INDUCER_RUBRIC:
            item_eval = rubric.get(key, {})
            if isinstance(item_eval, dict):
                md += f"- **{key}**: {item_eval.get('score', 0)}점 - {item_eval.get('feedback', 'N/A')}\n"

        if rubric.get("총평"):
            md += f"\n**총평**: {rubric['총평']}\n"

        md += """
</details>

---

"""

    md += f"""
## 5. 평가 기준 (루브릭)

"""

    for key, item in THOUGHT_INDUCER_RUBRIC.items():
        md += f"### {key} (만점: {item['max_score']}점)\n\n"
        md += f"{item['description']}\n\n"
        for score, desc in item["criteria"].items():
            md += f"- **{score}점**: {desc}\n"
        md += "\n"

    return md


# ============================================================
# 메인
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Gemini 루브릭 평가 시스템")

    parser.add_argument(
        "--endpoint-id", type=str, default="",
        help="Gemma 모델 엔드포인트 ID"
    )
    parser.add_argument(
        "--project-number", type=str, default="84537953160",
        help="GCP 프로젝트 번호"
    )
    parser.add_argument(
        "--location", type=str, default="us-central1",
        help="Vertex AI 리전"
    )
    parser.add_argument(
        "--gemini-api-key", type=str, default="",
        help="Gemini API 키 (없으면 환경변수 GEMINI_API_KEY)"
    )
    parser.add_argument(
        "--output-dir", type=str, default="outputs/evaluation_reports",
        help="결과 저장 디렉토리"
    )
    parser.add_argument(
        "--test-cases", type=str, default="",
        help="커스텀 테스트 케이스 JSON 파일"
    )
    parser.add_argument(
        "--skip-gemma", action="store_true",
        help="Gemma 호출 건너뛰기 (이전 응답 사용)"
    )
    parser.add_argument(
        "--gemma-responses", type=str, default="",
        help="이전 Gemma 응답 파일 (--skip-gemma와 함께 사용)"
    )

    args = parser.parse_args()

    # 테스트 케이스 로드
    test_cases = None
    if args.test_cases and Path(args.test_cases).exists():
        with open(args.test_cases, 'r', encoding='utf-8') as f:
            test_cases = json.load(f)

    # 평가 실행
    run_full_evaluation(
        endpoint_id=args.endpoint_id,
        project_number=args.project_number,
        location=args.location,
        test_cases=test_cases,
        output_dir=args.output_dir,
        gemini_api_key=args.gemini_api_key or None,
        skip_gemma=args.skip_gemma,
        gemma_responses_file=args.gemma_responses or None
    )


if __name__ == "__main__":
    main()
