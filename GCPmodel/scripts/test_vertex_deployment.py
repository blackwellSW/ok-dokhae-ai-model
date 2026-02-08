#!/usr/bin/env python3
"""
배포된 Gemma 2 9B vLLM 엔드포인트 테스트
직접 REST API를 사용하여 인증 문제 우회
"""

import json
import subprocess
import requests


def get_access_token():
    """gcloud에서 액세스 토큰 가져오기"""
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "print-access-token"],
            stderr=subprocess.PIPE
        ).decode("utf-8").strip()
        return token
    except subprocess.CalledProcessError as e:
        print(f"❌ 토큰 획득 실패: {e}")
        print(f"stderr: {e.stderr.decode('utf-8')}")
        return None


def test_vllm_endpoint(
    endpoint_id: str,
    project: str = "knu-team-03",
    region: str = "us-central1"
):
    """vLLM 엔드포인트 테스트"""

    print("=" * 70)
    print("🚀 Gemma 2 9B + vLLM + LoRA 엔드포인트 테스트")
    print("=" * 70)
    print(f"Project: {project}")
    print(f"Region: {region}")
    print(f"Endpoint ID: {endpoint_id}")
    print("=" * 70)

    # 액세스 토큰 획득
    token = get_access_token()
    if not token:
        print("⚠️ 먼저 'gcloud auth login'을 실행하세요")
        return

    # API URL
    url = f"https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}/endpoints/{endpoint_id}:rawPredict"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 고전 문학 관련 테스트 케이스
    test_cases = [
        {
            "name": "춘향전 - 주인공 질문",
            "question": "춘향전의 주인공은 누구인가요?",
            "context": "춘향전"
        },
        {
            "name": "춘향전 - 이몽룡 신분",
            "question": "이몽룡이 신분을 숨긴 이유가 뭔가요?",
            "context": "춘향전"
        },
        {
            "name": "심청전 - 인당수",
            "question": "심청이는 왜 인당수에 몸을 던졌나요?",
            "context": "심청전"
        },
        {
            "name": "흥부전 - 형제 비교",
            "question": "흥부와 놀부의 차이점은 무엇인가요?",
            "context": "흥부전"
        },
        {
            "name": "일반 한국어 능력",
            "question": "조선시대 과거제도에 대해 설명해주세요",
            "context": "한국사"
        }
    ]

    success_count = 0
    total = len(test_cases)

    for i, tc in enumerate(test_cases, 1):
        print(f"\n{'=' * 70}")
        print(f"[테스트 {i}/{total}] {tc['name']}")
        print("=" * 70)
        print(f"📚 문맥: {tc['context']}")
        print(f"💬 질문: {tc['question']}")
        print("-" * 70)

        # vLLM OpenAI-compatible API 포맷 (system role 미지원)
        # LoRA 어댑터를 사용하려면 model을 "classical-lit"로 지정
        user_prompt = f"당신은 {tc['context']} 전문가입니다. 학생의 질문에 친절하고 교육적으로 답변해주세요.\n\n질문: {tc['question']}\n\n답변:"

        payload = {
            "model": "classical-lit",  # vLLM --lora-modules에서 정의한 이름
            "messages": [
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            "max_tokens": 256,
            "temperature": 0.7,
            "top_p": 0.9
        }

        try:
            # API 호출
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=60
            )

            # 응답 확인
            if response.status_code == 200:
                result = response.json()

                # vLLM은 OpenAI 포맷으로 응답
                choices = result.get("choices", [])
                if choices:
                    answer = choices[0].get("message", {}).get("content", "")
                    usage = result.get("usage", {})

                    print(f"\n🤖 응답:")
                    print(f"{answer}")
                    print(f"\n📊 토큰 사용:")
                    print(f"  - 입력: {usage.get('prompt_tokens', 'N/A')}")
                    print(f"  - 출력: {usage.get('completion_tokens', 'N/A')}")
                    print(f"  - 총: {usage.get('total_tokens', 'N/A')}")

                    success_count += 1
                else:
                    print(f"⚠️ 응답 데이터 없음")
                    print(f"Raw response: {json.dumps(result, indent=2, ensure_ascii=False)}")
            else:
                print(f"❌ HTTP {response.status_code}")
                print(f"Response: {response.text}")

        except requests.exceptions.Timeout:
            print(f"⏱️ 타임아웃 (60초 초과)")
        except Exception as e:
            print(f"❌ 오류: {e}")

    # 최종 결과
    print(f"\n{'=' * 70}")
    print(f"✅ 테스트 완료: {success_count}/{total} 성공")
    print("=" * 70)

    if success_count == total:
        print("\n🎉 모든 테스트가 성공적으로 완료되었습니다!")
        print("✨ LoRA 어댑터가 정상 작동하고 있습니다!")
    elif success_count > 0:
        print(f"\n⚠️ 일부 테스트 실패 ({total - success_count}개)")
    else:
        print("\n❌ 모든 테스트 실패")


if __name__ == "__main__":
    # deployment_info.json에서 정보 로드
    import os

    deployment_info_path = "/Users/choidamul/GCPmodel/deployment_info.json"

    if os.path.exists(deployment_info_path):
        with open(deployment_info_path) as f:
            info = json.load(f)

        test_vllm_endpoint(
            endpoint_id=info["endpoint_id"],
            project=info["project_id"],
            region=info["region"]
        )
    else:
        print("❌ deployment_info.json 파일을 찾을 수 없습니다")
