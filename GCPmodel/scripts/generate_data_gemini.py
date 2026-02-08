#!/usr/bin/env python3
"""
Gemini 2.5 Pro로 고전문학 Socratic dialogue 데이터 생성
GCP 크레딧 자동 사용
"""

import os
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.cloud import aiplatform
import vertexai
from vertexai.generative_models import GenerativeModel

# 서비스 계정 키 설정
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/choidamul/GCPmodel/.gcp-key.json"

# GCP 설정
PROJECT_ID = "knu-team-03"
LOCATION = "us-central1"

# Gemini 모델 초기화 (2.0 Flash - 안정적인 JSON 출력)
vertexai.init(project=PROJECT_ID, location=LOCATION)
model = GenerativeModel("gemini-2.0-flash-001")

# 고전문학 작품 목록 (100개)
CLASSICAL_WORKS = [
    # 고전소설 (30개)
    "춘향전", "홍길동전", "구운몽", "심청전", "흥부전", "박씨전", "장화홍련전", "운영전", "최척전", "사씨남정기",
    "창선감의록", "숙향전", "조웅전", "유충렬전", "소대성전", "임진록", "완월회맹연", "명주보월빙", "옥루몽", "옥단춘전",
    "배비장전", "양반전", "허생전", "호질", "민옹전", "우상전", "예덕선생전", "남염부주지", "전우치전", "장끼전",

    # 고전시가 (20개)
    "용비어천가", "악장가사", "정읍사", "처용가", "서동요", "제망매가", "찬기파랑가", "혜성가", "원왕생가", "모죽지랑가",
    "청산별곡", "서경별곡", "가시리", "동동", "이상곡", "정과정", "만전춘별사", "쌍화점", "정석가", "사모곡",

    # 시조 (20개)
    "오우가", "훈민가", "단심가", "한거십팔곡", "도산십이곡", "어부사시사", "속미인곡", "사미인곡", "면양정가", "성산별곡",
    "관동별곡", "사제곡", "누항사", "일동장유가", "견회요", "농가월령가", "규원가", "매화사", "북찬가", "독립군가",

    # 가사문학 (4개 + 기타)
    "상춘곡", "낙민가", "출새곡", "관동별곡", # 관동별곡 중복이나 리스트 유지

    # 한문학 (10개)
    "금오신화", "기재기이", "어우야담", "청구야담", "동패락송", "택리지", "임원경제지", "성호사설", "목민심서", "흠흠신서",

    # 판소리 (10개)
    "춘향가", "심청가", "흥보가", "수궁가", "적벽가", "변강쇠가", "배비장타령", "강릉매화타령", "무숙이타령", "장끼타령",

    # 현대 전환기 (10개)
    "혈의루", "자유종", "은세계", "치악산", "무정", "만세전", "빈처", "고목화", "B사감과 러브레터", "날개"
]

# 중복 제거 및 보정 (100개 근사치 맞춤)
CLASSICAL_WORKS = list(set(CLASSICAL_WORKS))

# 질문 유형 (10가지)
QUESTION_TYPES = [
    "등장인물의 심리 분석",
    "갈등 구조 파악",
    "시대적 배경과 사회상",
    "주제 의식 탐구",
    "표현 기법과 문체",
    "현대적 의미와 가치",
    "작품 구조와 전개",
    "상징과 비유 해석",
    "인물 간 관계 분석",
    "작품의 교훈과 메시지"
]

# Socratic dialogue 생성 프롬프트
PROMPT_TEMPLATE = """당신은 고전문학 교육 전문가이자 'Socratic Method'의 대가입니다.
학생들이 작품의 깊은 의미를 스스로 깨닫도록 유도하는 **Socratic dialogue 데이터**를 생성해주세요.

**작품**: {work}
**질문 유형**: {question_type}

### ✍️ 작성 가이드
1. **정답을 바로 알려주지 마세요.** (설명조 금지)
2. **꼬리에 꼬리를 무는 질문**으로 학생의 사고를 확장시키세요.
3. **핵심 질문 → 구체적 상황의 확인 → 모순의 지적 → 일반화/심화** 단계로 유도하세요.
4. **반어법, 가정법("만약 ~라면?")**을 적극 활용하여 학생이 당연하게 여기던 사실을 뒤집어 보게 하세요.

### ❌ 나쁜 예 (직접 답변)
이몽룡이 변사또가 된 것은 신분제도의 모순을 해결하기 위한 장치입니다.

### ✅ 좋은 예 (Socratic 질문)
"먼저 생각해봅시다. 이몽룡은 어떤 신분이었나요? 그리고 춘향은요? 
두 사람의 신분 차이가 그 당시 사회에서 왜 문제가 되었을까요?

당시 조선시대에는 양반과 기생이 자유롭게 결혼할 수 있었을까요? 
그렇다면 작가는 왜 하필 이몽룡을 변사또, 즉 권력을 가진 관리로 다시 등장시켰을까요?

이것을 통해 작가가 말하고 싶었던 것은 단순한 사랑 이야기일까요, 아니면 다른 무언가가 있을까요? 
개인의 사랑과 견고한 신분제도가 충돌할 때, 이 소설은 어떤 해결책을 제시하고 있나요?"

---

### 📝 생성 포맷 (JSON)

반드시 다음 JSON 형식으로만 출력하세요:

{{
  "instruction": "다음 지문을 읽고 질문에 답하세요. 학생의 사고를 유도하며 답변을 작성하세요.",
  "input": "[지문]\\n{{지문 내용 (200-300자)}}\\n\\n[질문]\\n{{사고 유도용 핵심 질문 (30-50자)}}",
  "output": "{{Socratic 답변 (500-800자): 질문 흐름으로 구성된 답변}}",
  "metadata": {{
    "work": "{work}",
    "question_type": "{question_type}",
    "dataset": "classical_socratic"
  }}
}}
"""

def generate_sample(work: str, question_type: str, retry: int = 3) -> dict:
    """Gemini로 1개 샘플 생성"""
    prompt = PROMPT_TEMPLATE.format(work=work, question_type=question_type)

    for attempt in range(retry):
        try:
            # Rate Limiting (Quota 초과 방지)
            time.sleep(0.3) 

            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.9,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 2048,
                    "response_mime_type": "application/json",
                }
            )

            # JSON 파싱
            text = response.text.strip()
            
            # JSON 클리닝
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]

            data = json.loads(text.strip())
            
            # 메타데이터 강제 주입 (모델이 실수할 경우 대비)
            if "metadata" not in data:
                data["metadata"] = {}
            data["metadata"]["work"] = work
            data["metadata"]["question_type"] = question_type
            data["metadata"]["dataset"] = "classical_socratic"
            
            return data

        except Exception as e:
            print(f"❌ 오류 [{work}] (시도 {attempt + 1}/{retry}): {e}")
            if attempt < retry - 1:
                time.sleep(2)
            else:
                return None

    return None

def generate_all_samples(total: int = 3000, workers: int = 5):
    """병렬로 모든 샘플 생성"""
    
    print("=" * 60)
    print("🚀 Gemini 1.5 Pro - Socratic Data Generation")
    print("=" * 60)
    print(f"목표: {total}개 샘플")
    print(f"작품 수: {len(CLASSICAL_WORKS)}개")
    print(f"질문 유형: {len(QUESTION_TYPES)}개")
    print("=" * 60)

    # 작품 × 질문 유형 조합 생성
    tasks = []
    
    # 1. 기본적으로 모든 작품과 유형을 한 번씩은 훑기 (100 * 10 = 1000개)
    # 2. 나머지는 랜덤하게 분포
    import random
    
    # 기본 조합
    base_combinations = []
    for work in CLASSICAL_WORKS:
        for q_type in QUESTION_TYPES:
            base_combinations.append((work, q_type))
            
    random.shuffle(base_combinations)
    
    # 목표 수량에 맞게 태스크 리스트 작성
    if total <= len(base_combinations):
        tasks = base_combinations[:total]
    else:
        # 일단 다 넣고
        tasks.extend(base_combinations)
        # 남은 만큼 랜덤 뽑기
        remaining = total - len(tasks)
        for _ in range(remaining):
            tasks.append((random.choice(CLASSICAL_WORKS), random.choice(QUESTION_TYPES)))
    
    # 셔플
    random.shuffle(tasks)

    # 병렬 생성
    results = []
    failed = 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(generate_sample, work, qt): (work, qt)
            for work, qt in tasks
        }

        for i, future in enumerate(as_completed(futures), 1):
            try:
                result = future.result()
                if result:
                    results.append(result)
                    print(f"✅ [{i}/{total}] {result['metadata']['work']} - {result['metadata']['question_type']}")
                else:
                    failed += 1
                    print(f"❌ [{i}/{total}] 생성 실패")

                if i % 50 == 0:
                    print(f"\n📊 진행률: {i}/{total} (성공: {len(results)}, 실패: {failed})\n")

            except Exception as e:
                failed += 1
                print(f"❌ [{i}/{total}] 예외: {e}")

    return results

def save_datasets(samples: list, output_dir: str = "data/augmented"):
    """Train/Valid 분할 및 저장"""

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 80/20 분할 (2400 / 600)
    import random
    random.shuffle(samples)
    
    split_ratio = 0.8
    split_idx = int(len(samples) * split_ratio)

    train_samples = samples[:split_idx]
    valid_samples = samples[split_idx:]

    train_path = f"{output_dir}/train_socratic.jsonl"
    valid_path = f"{output_dir}/valid_socratic.jsonl"

    with open(train_path, 'w', encoding='utf-8') as f:
        for sample in train_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')

    with open(valid_path, 'w', encoding='utf-8') as f:
        for sample in valid_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')

    print(f"\n💾 저장 완료!")
    print(f"   Train: {train_path} ({len(train_samples)}개)")
    print(f"   Valid: {valid_path} ({len(valid_samples)}개)")

    return train_path, valid_path

def upload_to_gcs(train_path: str, valid_path: str):
    """GCS 업로드"""
    try:
        from google.cloud import storage
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket("knu-team-03-data")

        blob_train = bucket.blob("classical-literature/gemma/train_socratic.jsonl")
        blob_train.upload_from_filename(train_path)
        print(f"☁️ GCS Upload: gs://knu-team-03-data/{blob_train.name}")

        blob_valid = bucket.blob("classical-literature/gemma/valid_socratic.jsonl")
        blob_valid.upload_from_filename(valid_path)
        print(f"☁️ GCS Upload: gs://knu-team-03-data/{blob_valid.name}")
        
    except Exception as e:
        print(f"⚠️ GCS 업로드 실패: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="테스트 실행 (5개만 생성)")
    args = parser.parse_args()
    
    target_count = 5 if args.test else 3000
    
    samples = generate_all_samples(total=target_count, workers=10)
    
    if samples:
        train_path, valid_path = save_datasets(samples)
        if not args.test:
            upload_to_gcs(train_path, valid_path)
