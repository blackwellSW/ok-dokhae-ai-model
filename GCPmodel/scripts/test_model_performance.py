#!/usr/bin/env python3
"""
학습 완료된 모델 성능 테스트 스크립트
Vertex AI에서 학습된 모델의 추론 성능 및 품질 평가
"""

import argparse
import json
import time
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel


def initialize_vertex_ai(project_id: str, location: str = "us-central1"):
    """Vertex AI 초기화"""
    aiplatform.init(project=project_id, location=location)
    print(f"✅ Vertex AI 초기화 완료: {project_id} ({location})")


def get_deployed_model_endpoint(model_id: str, location: str = "us-central1") -> str:
    """배포된 모델 엔드포인트 조회"""
    # Vertex AI에서 모델 ID로 엔드포인트 찾기
    endpoints = aiplatform.Endpoint.list(
        filter=f'display_name="{model_id}"',
        order_by="create_time desc"
    )

    if endpoints:
        endpoint = endpoints[0]
        print(f"✅ 엔드포인트 찾음: {endpoint.resource_name}")
        return endpoint.resource_name
    else:
        print(f"⚠️ 배포된 엔드포인트를 찾을 수 없습니다: {model_id}")
        return None


def test_model_inference(
    model_id: str,
    project_id: str,
    location: str = "us-central1",
    test_prompts: List[Dict] = None
) -> List[Dict]:
    """
    모델 추론 테스트

    Args:
        model_id: 학습된 모델 ID (예: gemma3-classical-lit-20260205-221125)
        project_id: GCP 프로젝트 ID
        location: 리전
        test_prompts: 테스트용 프롬프트 리스트

    Returns:
        테스트 결과 리스트
    """
    print("\n" + "=" * 70)
    print("🧪 모델 추론 성능 테스트")
    print("=" * 70)
    print(f"모델 ID: {model_id}")
    print(f"프로젝트: {project_id}")
    print(f"리전: {location}")
    print("-" * 70)

    # 기본 테스트 프롬프트
    if test_prompts is None:
        test_prompts = [
            {
                "name": "춘향전_질문1",
                "context": "춘향전",
                "student_input": "춘향전에서 이몽룡이 신분을 숨긴 이유가 뭔가요?",
                "expected_tags": ["[사고유도]", "[사고로그]"]
            },
            {
                "name": "심청전_질문1",
                "context": "심청전",
                "student_input": "심청이는 왜 인당수에 몸을 던졌나요?",
                "expected_tags": ["[사고유도]", "[사고로그]"]
            },
            {
                "name": "흥부전_질문1",
                "context": "흥부전",
                "student_input": "흥부와 놀부의 차이점은 무엇인가요?",
                "expected_tags": ["[사고유도]", "[사고로그]"]
            },
            {
                "name": "표현_질문",
                "context": "고전문학",
                "student_input": "의인화 기법이 뭔가요?",
                "expected_tags": ["[사고유도]", "[사고로그]"]
            },
            {
                "name": "주제_질문",
                "context": "춘향전",
                "student_input": "춘향전의 주제가 뭐예요?",
                "expected_tags": ["[사고유도]", "[사고로그]"]
            }
        ]

    results = []

    # Vertex AI 초기화
    initialize_vertex_ai(project_id, location)

    # 모델 로드 (Vertex AI 튜닝된 모델 사용)
    try:
        # 튜닝된 Gemini 모델 사용
        model = GenerativeModel(f"publishers/google/models/{model_id}")
        print(f"✅ 모델 로드 완료: {model_id}\n")
    except Exception as e:
        print(f"❌ 모델 로드 실패: {e}")
        print("\n💡 대안: 직접 엔드포인트 URL을 사용하세요")
        return []

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

        # 추론 실행 (시간 측정)
        start_time = time.time()

        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": 512,
                    "temperature": 0.7,
                    "top_p": 0.9,
                }
            )

            inference_time = time.time() - start_time

            # 응답 텍스트 추출
            response_text = response.text if hasattr(response, 'text') else str(response)

            # 결과 분석
            result = analyze_response(
                test_case=test_case,
                response=response_text,
                inference_time=inference_time
            )

            results.append(result)

            # 결과 출력
            print_test_result(result)

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
    """프롬프트 구성"""
    system_prompt = """학생의 사고를 유도하며 고전문학을 가르치세요. [사고유도]와 [사고로그] 태그를 사용하세요.

[사고유도]: 학생이 스스로 생각할 수 있도록 단계적 질문을 제시합니다.
[사고로그]: 학생의 사고 과정을 관찰하고 기록합니다."""

    if context:
        return f"""{system_prompt}

[맥락]
{context}

학생: {student_input}

AI: [사고유도]"""
    else:
        return f"""{system_prompt}

학생: {student_input}

AI: [사고유도]"""


def analyze_response(test_case: Dict, response: str, inference_time: float) -> Dict:
    """응답 분석"""
    # 태그 존재 확인
    has_induction_tag = "[사고유도]" in response
    has_log_tag = "[사고로그]" in response

    # 태그 내용 추출
    induction_content = extract_tag_content(response, "사고유도")
    log_content = extract_tag_content(response, "사고로그")

    # 토큰 수 추정 (대략적)
    token_count = len(response.split())
    tokens_per_second = token_count / inference_time if inference_time > 0 else 0

    # 품질 점수 계산 (간단한 휴리스틱)
    quality_score = 0
    if has_induction_tag:
        quality_score += 30
    if has_log_tag:
        quality_score += 20
    if len(induction_content) > 50:
        quality_score += 25
    if "?" in induction_content:  # 질문 포함 여부
        quality_score += 15
    if len(log_content) > 20:
        quality_score += 10

    return {
        "test_name": test_case["name"],
        "status": "success",
        "inference_time": round(inference_time, 3),
        "token_count": token_count,
        "tokens_per_second": round(tokens_per_second, 2),
        "has_induction_tag": has_induction_tag,
        "has_log_tag": has_log_tag,
        "induction_length": len(induction_content),
        "log_length": len(log_content),
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
    print(f"📊 토큰 수: {result['token_count']} ({result['tokens_per_second']} tokens/sec)")
    print(f"✅ [사고유도] 태그: {'있음' if result['has_induction_tag'] else '없음'}")
    print(f"✅ [사고로그] 태그: {'있음' if result['has_log_tag'] else '없음'}")
    print(f"📝 사고유도 길이: {result['induction_length']} 자")
    print(f"📝 사고로그 길이: {result['log_length']} 자")
    print(f"⭐ 품질 점수: {result['quality_score']}/100")

    print(f"\n💬 응답 내용:")
    print("-" * 70)
    print(result['response'][:500])
    if len(result['response']) > 500:
        print("\n... (생략) ...")


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

    # 태그 사용률
    induction_tag_rate = sum(1 for r in successful_tests if r["has_induction_tag"]) / len(successful_tests) * 100
    log_tag_rate = sum(1 for r in successful_tests if r["has_log_tag"]) / len(successful_tests) * 100

    print(f"\n✅ 성공한 테스트: {len(successful_tests)}/{len(results)}")
    print(f"⏱️  평균 추론 시간: {avg_inference_time:.3f}초")
    print(f"📊 평균 처리 속도: {avg_tokens_per_sec:.2f} tokens/sec")
    print(f"⭐ 평균 품질 점수: {avg_quality_score:.1f}/100")
    print(f"✅ [사고유도] 태그 사용률: {induction_tag_rate:.1f}%")
    print(f"✅ [사고로그] 태그 사용률: {log_tag_rate:.1f}%")

    # 상세 결과 테이블
    print("\n" + "-" * 70)
    print("개별 테스트 결과:")
    print("-" * 70)
    print(f"{'테스트명':<20} {'시간(초)':<12} {'품질점수':<12} {'태그':<10}")
    print("-" * 70)

    for r in successful_tests:
        tags = ""
        if r["has_induction_tag"]:
            tags += "🟢"
        else:
            tags += "🔴"
        if r["has_log_tag"]:
            tags += "🟢"
        else:
            tags += "🔴"

        print(f"{r['test_name']:<20} {r['inference_time']:<12.3f} {r['quality_score']:<12} {tags:<10}")

    print("=" * 70)

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
    parser = argparse.ArgumentParser(description="학습된 모델 성능 테스트")

    parser.add_argument(
        "--model-id",
        type=str,
        default="gemma3-classical-lit-20260205-221125",
        help="학습된 모델 ID"
    )
    parser.add_argument(
        "--project-id",
        type=str,
        required=True,
        help="GCP 프로젝트 ID"
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
    results = test_model_inference(
        model_id=args.model_id,
        project_id=args.project_id,
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
