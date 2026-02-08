#!/usr/bin/env python3
"""엔드포인트 빠른 테스트 (인증 문제 우회)"""

import subprocess
import requests
import json

# 모든 계정 시도
accounts = [
    "edu_153@iceu.kr",
    "inhalchigim123@gmail.com",
    "84537953160-compute@developer.gserviceaccount.com"
]

endpoint_id = "2283851677146546176"
project = "knu-team-03"
region = "us-central1"

print("=" * 70)
print("🔍 엔드포인트 접근 테스트")
print("=" * 70)

for account in accounts:
    print(f"\n계정: {account}")

    # 계정 전환
    subprocess.run(["gcloud", "config", "set", "account", account],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 토큰 획득 시도
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "print-access-token"],
            stderr=subprocess.PIPE
        ).decode("utf-8").strip()

        print(f"  ✅ 토큰 획득 성공: {token[:20]}...")

        # API 호출 테스트
        url = f"https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}/endpoints/{endpoint_id}:rawPredict"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "classical-lit",
            "messages": [{"role": "user", "content": "춘향전이 뭐야?"}],
            "max_tokens": 50,
            "temperature": 0.7
        }

        response = requests.post(url, headers=headers, json=payload, timeout=10)

        if response.status_code == 200:
            print(f"  🎉 API 호출 성공!")
            result = response.json()
            answer = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"  응답: {answer[:100]}...")
            print(f"\n  ✨ 이 계정을 사용하세요: {account}")
            break
        else:
            print(f"  ❌ HTTP {response.status_code}")
            print(f"  {response.text[:200]}")

    except subprocess.CalledProcessError as e:
        print(f"  ❌ 토큰 획득 실패")
        print(f"  {e.stderr.decode('utf-8')[:200] if e.stderr else ''}")
    except Exception as e:
        print(f"  ❌ 오류: {e}")

print("\n" + "=" * 70)
