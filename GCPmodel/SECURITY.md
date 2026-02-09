# 보안 가이드

## 환경 변수 관리

### 프로덕션 (Cloud Run)

Cloud Run에서는 다음 환경변수만 설정:

```bash
USE_VERTEX_AI=true
FIREBASE_PROJECT_ID=knu-team-03
DATABASE_URL=sqlite+aiosqlite:////tmp/classical_literature.db
JWT_SECRET_KEY=<강력한-시크릿-키>
DOCUMENT_AI_PROCESSOR_ID=<프로세서-ID>
DOCUMENT_AI_LOCATION=asia-northeast1
```

### 로컬 개발

`.env` 파일 생성 (절대 커밋하지 말것!):

```bash
USE_VERTEX_AI=false
GEMINI_API_KEY=<개발용-API-키>
FIREBASE_PROJECT_ID=knu-team-03
JWT_SECRET_KEY=dev-secret-key
```

## 보안 원칙

1. **API 키는 절대 코드에 하드코딩하지 않기**
   - 모든 키는 환경변수로 관리
   - `.env` 파일은 `.gitignore`에 포함

2. **GCP 서비스 계정 키 관리**
   - `.gcp-key.json`은 로컬에만 보관
   - Cloud Run은 기본 서비스 계정 사용 (키 파일 불필요)

3. **Vertex AI 인증**
   - Cloud Run: 자동으로 기본 서비스 계정 사용
   - 로컬: `GOOGLE_APPLICATION_CREDENTIALS` 환경변수로 키 파일 지정

4. **JWT Secret**
   - 프로덕션: 강력한 랜덤 문자열 사용
   - 개발: 간단한 문자열 사용 가능

## 보안 체크리스트

- [ ] `.gcp-key.json`이 `.gitignore`에 포함되어 있는가?
- [ ] `.env` 파일이 `.gitignore`에 포함되어 있는가?
- [ ] Cloud Run 환경변수에 민감한 정보가 평문으로 노출되어 있지 않은가?
- [ ] JWT_SECRET_KEY가 프로덕션에서 강력한 값으로 설정되어 있는가?
- [ ] API 키가 코드에 하드코딩되어 있지 않은가?

## 노출된 API 키 발견 시

1. **즉시 해당 키 폐기**
   ```bash
   # Google Cloud Console > APIs & Services > Credentials
   # 해당 API 키를 찾아서 삭제
   ```

2. **새 키 발급 및 안전한 방법으로 저장**
   ```bash
   # Secret Manager 사용 권장
   gcloud secrets create gemini-api-key --data-file=-
   ```

3. **Git 히스토리에서 완전 제거** (필요시)
   ```bash
   git filter-branch --force --index-filter \
     'git rm --cached --ignore-unmatch .env' \
     --prune-empty --tag-name-filter cat -- --all
   ```

## 현재 보안 상태 (2026-02-09)

✅ **안전함:**
- GitHub에 민감한 정보 노출 없음
- Vertex AI는 GCP IAM으로 보호
- GEMINI_API_KEY를 Cloud Run에서 제거함

⚠️ **개선 권장:**
- JWT_SECRET_KEY를 더 강력한 값으로 변경
- Secret Manager 활성화 후 사용 검토
