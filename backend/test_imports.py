"""
백엔드 실행 가능성 테스트
"""

print("=" * 60)
print("🧪 백엔드 실행 가능성 테스트")
print("=" * 60)

# 1. 기본 import 테스트
print("\n1. 기본 모듈 import 테스트...")
try:
    from fastapi import FastAPI
    print("✅ FastAPI")
except ImportError as e:
    print(f"❌ FastAPI: {e}")

try:
    from pydantic import BaseModel
    print("✅ Pydantic")
except ImportError as e:
    print(f"❌ Pydantic: {e}")

try:
    from sqlalchemy.ext.asyncio import create_async_engine
    print("✅ SQLAlchemy (async)")
except ImportError as e:
    print(f"❌ SQLAlchemy: {e}")

try:
    from jose import jwt
    print("✅ python-jose (JWT)")
except ImportError as e:
    print(f"❌ python-jose: {e}")

try:
    from passlib.context import CryptContext
    print("✅ passlib")
except ImportError as e:
    print(f"❌ passlib: {e}")

try:
    import google.generativeai as genai
    print("✅ google-generativeai")
except ImportError as e:
    print(f"❌ google-generativeai: {e}")

# 2. 앱 모듈 구조 테스트
print("\n2. 앱 모듈 구조 테스트...")
try:
    from app.core.config import get_settings
    print("✅ app.core.config")
except Exception as e:
    print(f"❌ app.core.config: {e}")

try:
    from app.db.database import Base
    print("✅ app.db.database")
except Exception as e:
    print(f"❌ app.db.database: {e}")

try:
    from app.db.models import User
    print("✅ app.db.models")
except Exception as e:
    print(f"❌ app.db.models: {e}")

try:
    from app.core.auth import get_password_hash
    print("✅ app.core.auth")
except Exception as e:
    print(f"❌ app.core.auth: {e}")

try:
    from app.api.auth import router as auth_router
    print("✅ app.api.auth")
except Exception as e:
    print(f"❌ app.api.auth: {e}")

try:
    from app.api.chat_learning import router as chat_router
    print("✅ app.api.chat_learning")
except Exception as e:
    print(f"❌ app.api.chat_learning: {e}")

# 3. 메인 앱 테스트
print("\n3. 메인 애플리케이션 import 테스트...")
try:
    from app.main import app
    print("✅ app.main")
    print(f"   버전: {app.version}")
    print(f"   제목: {app.title}")
except Exception as e:
    print(f"❌ app.main: {e}")

print("\n" + "=" * 60)
print("테스트 완료!")
print("=" * 60)

# 요약
print("\n📋 요약:")
print("- 모든 ✅가 표시되면 백엔드가 정상적으로 실행 가능합니다")
print("- ❌가 있다면 해당 패키지를 설치해야 합니다:")
print("  pip install -r requirements.txt")
print("\n실행 방법:")
print("  python -m uvicorn app.main:app --reload --port 8000")
