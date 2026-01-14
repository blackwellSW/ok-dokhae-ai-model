# ok-dokhae

## git clone 이후 해야할 작업
- 가상 환경 설치(선택) -> requirements 설치가 부담되면 나중에 지우기 편하도록 가상환경 사용 가능
- pip install -r requirements.txt
- 데이터 샘플 생성 : python backend/fetch_data.py - 생성 결과는 samples.json 파일
- 데모 실행 : python backend/run_demo.py
- 스모크 테스트 : python tests/core_test.py

## Team Work Guide (역할 분담)
- 본 프로젝트는 baseline 파이프라인을 유지한 채, 각자 독립적인 실험을 진행하는 구조로 운영 
- `main` 브랜치는 항상 실행 가능한 상태를 유지하며, 모든 실험은 **feature 브랜치**에서 진행

### Branch Rule
- main: baseline 고정 (직접 수정 금지)
- feature 브랜치에서 실험 후 PR

예시:
- feature/question-generation
- feature/logic-nodes
- feature/evaluation
- feature/preprocessing

### A. 질문 생성 개선 (Question Gene빈
**담당 파일**
- `backend/logic/generator.py`

**목표**
- 현재 단순 템플릿 기반 질문을
- 논리 구조에 더 밀접한 질문으로 개선

**예시 작업**
- 질문 물
**담당 파일**
- `backend/fetch_data.py`
- (선택) `notebooks/01_data_sanity.ipynb`

**목표**
- 입력 텍스트 품질 및 샘플 데이터 구성 개선

**예시 작업**
- 문장 분리/정규화 개선
- 데이터셋 추가 또는 샘플 선별 기준 수정
- 데이터 분포 및 품질 분석

## Notes
- `backend/logic/` 하위 파일들이 **코어 파이프라인**입니다.
- 실험 결과는 Notion 등에 간단히 기록해주세요.
- `__pycache__`, 가상환경, 대용량 데이터는 Git에 포함하지 않습니다.
