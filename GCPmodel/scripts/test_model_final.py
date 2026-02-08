#!/usr/bin/env python3
"""
튜닝된 모델 최종 성능 테스트
REST API를 통한 직접 호출
"""

import argparse
import json
import time
import requests
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import subprocess


def get_access_token() -> str:
    """GCP Access Token 획득"""
    result = subprocess.run(
        ["gcloud", "auth", "application-default", "print-access-token"],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


def test_tuned_model(
    endpoint_id: str,
    project_number: str,
    location: str = "us-central1",
    test_prompts: List[Dict] = None
) -> List[Dict]:
    """
    튜닝된 모델로 추론 테스트

    Args:
        endpoint_id: 엔드포인트 ID
        project_number: GCP 프로젝트 번호
        location: 리전
        test_prompts: 테스트용 프롬프트 리스트

    Returns:
        테스트 결과 리스트
    """
    print("\n" + "=" * 70)
    print("🧪 튜닝된 모델 최종 성능 테스트")
    print("=" * 70)
    print(f"엔드포인트 ID: {endpoint_id}")
    print(f"프로젝트 번호: {project_number}")
    print(f"리전: {location}")
    print("-" * 70)

    # 기본 테스트 프롬프트
    if test_prompts is None:
        test_prompts = [
            {
                "name": "춘향전_질문1",
                "student_input": "춘향전에서 이몽룡이 신분을 숨긴 이유가 뭔가요?",
                "context": "춘향전"
            },
            {
                "name": "심청전_질문1",
                "student_input": "심청이는 왜 인당수에 몸을 던졌나요?",
                "context": "심청전"
            },
            {
                "name": "흥부전_질문1",
                "student_input": "흥부와 놀부의 차이점은 무엇인가요?",
                "context": "흥부전"
            },
            {
                "name": "표현_질문",
                "student_input": "의인화 기법이 뭔가요?",
                "context": "고전문학"
            },
            {
                "name": "주제_질문",
                "student_input": "춘향전의 주제가 뭐예요?",
                "context": "춘향전"
            },
            {
                "name": "비교_질문",
                "student_input": "춘향전과 심청전의 공통점과 차이점은 무엇인가요?",
                "context": "고전문학"
            }
        ]

    results = []

    # Access Token 획득
    print("🔑 Access Token 획득 중...")
    access_token = get_access_token()
    print("✅ Access Token 획득 완료\n")

    # API 엔드포인트
    api_url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_number}/locations/{location}/endpoints/{endpoint_id}:generateContent"

    # 각 테스트 프롬프트에 대해 추론 실행
    for i, test_case in enumerate(test_prompts, 1):
        print(f"\n{'='*70}")
        print(f"테스트 케이스 {i}/{len(test_prompts)}: {test_case['name']}")
        print(f"{'='*70}")
        print(f"맥락: {test_case['context']}")
        print(f"질문: {test_case['student_input']}")
        print("-" * 70)

        # 프롬프트 구성
        prompt = construct_prompt(test_case['student_input'], test_case['context'])

        # 요청 본문
        request_body = {
            "contents": {
                "role": "user",
                "parts": {
                    "text": prompt
                }
            },
            "generation_config": {
                "temperature": 0.7,
                "maxOutputTokens": 512,
                "topP": 0.9
            }
        }

        # 헤더
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # 추론 실행 (시간 측정)
        start_time = time.time()

        try:
            response = requests.post(api_url, json=request_body, headers=headers, timeout=30)
            inference_time = time.time() - start_time

            if response.status_code == 200:
                response_json = response.json()

                # 응답 텍스트 추출
                response_text = ""
                if "candidates" in response_json and len(response_json["candidates"]) > 0:
                    candidate = response_json["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        parts = candidate["content"]["parts"]
                        if len(parts) > 0 and "text" in parts[0]:
                            response_text = parts[0]["text"]

                # 메타데이터 추출
                usage_metadata = response_json.get("usageMetadata", {})
                prompt_tokens = usage_metadata.get("promptTokenCount", 0)
                output_tokens = usage_metadata.get("candidatesTokenCount", 0)
                total_tokens = usage_metadata.get("totalTokenCount", 0)

                # 결과 분석
                result = analyze_response(
                    test_case=test_case,
                    response=response_text,
                    inference_time=inference_time,
                    prompt_tokens=prompt_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens
                )

                results.append(result)

                # 결과 출력
                print_test_result(result)

            else:
                print(f"❌ API 호출 실패: {response.status_code}")
                print(f"   에러: {response.text}")
                results.append({
                    "test_name": test_case['name'],
                    "status": "failed",
                    "error": f"HTTP {response.status_code}: {response.text}"
                })

        except Exception as e:
            print(f"❌ 추론 실패: {e}")
            results.append({
                "test_name": test_case['name'],
                "status": "failed",
                "error": str(e)
            })

        print("-" * 70)
        time.sleep(1)  # API 레이트 리밋 방지

    return results


def construct_prompt(student_input: str, context: str = None) -> str:
    """프롬프트 구성 - 데이터셋과 동일한 형식"""
    # 학습 데이터와 동일한 형식으로 프롬프트 작성
    if context:
        return f"""[작품: {context}]
학생: {student_input}

교사: """
    else:
        return f"""학생: {student_input}

교사: """


def analyze_response(
    test_case: Dict,
    response: str,
    inference_time: float,
    prompt_tokens: int,
    output_tokens: int,
    total_tokens: int
) -> Dict:
    """응답 분석"""
    # 태그 존재 확인
    has_induction_tag = "[사고유도]" in response
    has_log_tag = "[사고로그]" in response

    # 태그 내용 추출
    induction_content = extract_tag_content(response, "사고유도")
    log_content = extract_tag_content(response, "사고로그")

    # 토큰 처리 속도
    tokens_per_second = output_tokens / inference_time if inference_time > 0 else 0

    # 품질 점수 계산
    quality_score = 0

    # 1. 태그 사용 (50점)
    if has_induction_tag:
        quality_score += 30
    if has_log_tag:
        quality_score += 20

    # 2. 내용 충실도 (30점)
    if len(induction_content) > 50:
        quality_score += 15
    if len(log_content) > 20:
        quality_score += 15

    # 3. 질문 포함 여부 (사고유도) (20점)
    question_count = induction_content.count("?")
    if question_count >= 1:
        quality_score += 10
    if question_count >= 2:
        quality_score += 10

    return {
        "test_name": test_case["name"],
        "status": "success",
        "inference_time": round(inference_time, 3),
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "tokens_per_second": round(tokens_per_second, 2),
        "has_induction_tag": has_induction_tag,
        "has_log_tag": has_log_tag,
        "induction_length": len(induction_content),
        "log_length": len(log_content),
        "question_count": question_count,
        "quality_score": quality_score,
        "response": response,
        "induction_content": induction_content,
        "log_content": log_content
    }


def extract_tag_content(text: str, tag: str) -> str:
    """태그 내용 추출"""
    import re
    pattern = rf"\[{tag}\]\s*(.*?)(?=\[|$)"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""


def print_test_result(result: Dict):
    """테스트 결과 출력"""
    if result["status"] == "failed":
        print(f"❌ 실패: {result.get('error', 'Unknown error')}")
        return

    print(f"⏱️  추론 시간: {result['inference_time']}초")
    print(f"📊 토큰: {result['prompt_tokens']} (입력) + {result['output_tokens']} (출력) = {result['total_tokens']}")
    print(f"🚀 처리 속도: {result['tokens_per_second']} tokens/sec")
    print(f"✅ [사고유도] 태그: {'✓' if result['has_induction_tag'] else '✗'}")
    print(f"✅ [사고로그] 태그: {'✓' if result['has_log_tag'] else '✗'}")
    print(f"📝 사고유도 길이: {result['induction_length']} 자 (질문 {result['question_count']}개)")
    print(f"📝 사고로그 길이: {result['log_length']} 자")
    print(f"⭐ 품질 점수: {result['quality_score']}/100")

    print(f"\n💬 응답 내용:")
    print("-" * 70)
    print(result['response'])
    print("-" * 70)


def generate_performance_report(results: List[Dict], output_path: str = None):
    """성능 리포트 생성"""
    print("\n" + "=" * 70)
    print("📊 전체 성능 요약")
    print("=" * 70)

    # 성공한 테스트만 집계
    successful_tests = [r for r in results if r.get("status") == "success"]

    if not successful_tests:
        print("❌ 성공한 테스트가 없습니다.")
        return

    # 평균 메트릭 계산
    avg_inference_time = sum(r["inference_time"] for r in successful_tests) / len(successful_tests)
    avg_tokens_per_sec = sum(r["tokens_per_second"] for r in successful_tests) / len(successful_tests)
    avg_quality_score = sum(r["quality_score"] for r in successful_tests) / len(successful_tests)
    avg_prompt_tokens = sum(r["prompt_tokens"] for r in successful_tests) / len(successful_tests)
    avg_output_tokens = sum(r["output_tokens"] for r in successful_tests) / len(successful_tests)

    # 태그 사용률
    induction_tag_rate = sum(1 for r in successful_tests if r["has_induction_tag"]) / len(successful_tests) * 100
    log_tag_rate = sum(1 for r in successful_tests if r["has_log_tag"]) / len(successful_tests) * 100

    print(f"\n✅ 성공한 테스트: {len(successful_tests)}/{len(results)}")
    print(f"⏱️  평균 추론 시간: {avg_inference_time:.3f}초")
    print(f"📊 평균 토큰: {avg_prompt_tokens:.0f} (입력) + {avg_output_tokens:.0f} (출력)")
    print(f"🚀 평균 처리 속도: {avg_tokens_per_sec:.2f} tokens/sec")
    print(f"⭐ 평균 품질 점수: {avg_quality_score:.1f}/100")
    print(f"✅ [사고유도] 태그 사용률: {induction_tag_rate:.1f}%")
    print(f"✅ [사고로그] 태그 사용률: {log_tag_rate:.1f}%")

    # 상세 결과 테이블
    print("\n" + "-" * 90)
    print("개별 테스트 결과:")
    print("-" * 90)
    print(f"{'테스트명':<25} {'시간(초)':<10} {'품질':<10} {'사고유도':<10} {'사고로그':<10}")
    print("-" * 90)

    for r in successful_tests:
        print(f"{r['test_name']:<25} {r['inference_time']:<10.3f} {r['quality_score']:<10} "
              f"{'✓' if r['has_induction_tag'] else '✗':<10} {'✓' if r['has_log_tag'] else '✗':<10}")

    print("=" * 90)

    # 결과 저장
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": len(results),
                "successful_tests": len(successful_tests),
                "failed_tests": len(results) - len(successful_tests),
                "avg_inference_time": round(avg_inference_time, 3),
                "avg_prompt_tokens": round(avg_prompt_tokens, 1),
                "avg_output_tokens": round(avg_output_tokens, 1),
                "avg_tokens_per_second": round(avg_tokens_per_sec, 2),
                "avg_quality_score": round(avg_quality_score, 1),
                "induction_tag_rate": round(induction_tag_rate, 1),
                "log_tag_rate": round(log_tag_rate, 1)
            },
            "detailed_results": results
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n💾 리포트 저장 완료: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="튜닝된 모델 성능 테스트")

    parser.add_argument(
        "--endpoint-id",
        type=str,
        default="479737813919596544",
        help="엔드포인트 ID"
    )
    parser.add_argument(
        "--project-number",
        type=str,
        default="84537953160",
        help="GCP 프로젝트 번호"
    )
    parser.add_argument(
        "--location",
        type=str,
        default="us-central1",
        help="Vertex AI 리전"
    )
    parser.add_argument(
        "--test-prompts",
        type=str,
        default="",
        help="커스텀 테스트 프롬프트 파일 (JSON)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="outputs/performance_test_results.json",
        help="결과 저장 경로"
    )

    args = parser.parse_args()

    # 커스텀 프롬프트 로드
    test_prompts = None
    if args.test_prompts and Path(args.test_prompts).exists():
        with open(args.test_prompts, 'r', encoding='utf-8') as f:
            test_prompts = json.load(f)

    # 성능 테스트 실행
    results = test_tuned_model(
        endpoint_id=args.endpoint_id,
        project_number=args.project_number,
        location=args.location,
        test_prompts=test_prompts
    )

    # 리포트 생성
    if results:
        generate_performance_report(results, args.output)
    else:
        print("\n❌ 테스트 결과가 없습니다.")


if __name__ == "__main__":
    main()
