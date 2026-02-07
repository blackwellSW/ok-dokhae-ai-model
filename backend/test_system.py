"""
간단한 API 테스트 스크립트
백엔드 API 엔드포인트를 테스트합니다.
"""

import asyncio
import sys
import os

# app 모듈을 import하기 위한 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.thought_inducer import ThoughtInducer
from app.services.gemini_evaluator import GeminiEvaluator
from app.services.language_analyzer import LanguageAnalyzer
from app.services.integrated_evaluator import IntegratedEvaluator


async def test_thought_inducer():
    """사고유도 엔진 테스트"""
    print("=" * 60)
    print("1. 사고유도 엔진 테스트")
    print("=" * 60)
    
    inducer = ThoughtInducer()
    result = await inducer.generate_response(
        student_input="춘향전에서 이몽룡이 신분을 숨긴 이유가 뭔가요?",
        work_title="춘향전"
    )
    
    print("\n[사고유도]")
    print(result["induction"])
    print("\n[사고로그]")
    print(result["log"])
    print()


async def test_gemini_evaluator():
    """Gemini 평가 테스트"""
    print("=" * 60)
    print("2. Gemini 질적 평가 테스트")
    print("=" * 60)
    
    evaluator = GeminiEvaluator()
    student_answer = """
    이몽룡은 신분을 숨김으로써 춘향의 진심을 확인하고자 했습니다.
    당시 조선시대 신분제 사회에서 양반과 기생의 딸이라는 신분 차이는
    큰 장벽이었습니다. 만약 처음부터 신분을 밝혔다면, 춘향의 반응이
    진심인지 아니면 신분에 대한 경외심인지 구분하기 어려웠을 것입니다.
    """
    
    result = await evaluator.evaluate(student_answer)
    
    print("\n평가 결과:")
    print(f"- 추론 깊이: {result['추론_깊이']['점수']}점")
    print(f"  피드백: {result['추론_깊이']['피드백']}")
    print(f"- 비판적 사고: {result['비판적_사고']['점수']}점")
    print(f"  피드백: {result['비판적_사고']['피드백']}")
    print(f"- 문학적 이해: {result['문학적_이해']['점수']}점")
    print(f"  피드백: {result['문학적_이해']['피드백']}")
    print(f"\n평균: {result['평균']}점")
    print()


def test_language_analyzer():
    """언어 분석 테스트"""
    print("=" * 60)
    print("3. 언어 분석 정량 평가 테스트")
    print("=" * 60)
    
    analyzer = LanguageAnalyzer()
    student_answer = """
    이몽룡은 신분을 숨김으로써 춘향의 진심을 확인하고자 했습니다.
    당시 조선시대 신분제 사회에서 양반과 기생의 딸이라는 신분 차이는
    큰 장벽이었습니다. 만약 처음부터 신분을 밝혔다면, 춘향의 반응이
    진심인지 아니면 신분에 대한 경외심인지 구분하기 어려웠을 것입니다.
    """
    
    result = analyzer.analyze(student_answer)
    
    print("\n정량 분석 결과:")
    print(f"- 어휘 다양성: {result['어휘_다양성']['점수']} ({result['어휘_다양성']['등급']})")
    print(f"  해석: {result['어휘_다양성']['해석']}")
    print(f"- 핵심 개념어 사용: {result['핵심_개념어']['총_개념_사용']}개 ({result['핵심_개념어']['평가']})")
    print(f"  해석: {result['핵심_개념어']['해석']}")
    print(f"- 문장 복잡도: {result['문장_복잡도']['점수']} ({result['문장_복잡도']['등급']})")
    print(f"- 반복 패턴: {result['반복_패턴']['반복률']} ({result['반복_패턴']['평가']})")
    print(f"- 감정 톤: {result['감정_톤']['학습_태도']} ({result['감정_톤']['점수']})")
    print(f"  해석: {result['감정_톤']['해석']}")
    print()


async def test_integrated_evaluator():
    """통합 평가 테스트"""
    print("=" * 60)
    print("4. 통합 평가 시스템 테스트")
    print("=" * 60)
    
    evaluator = IntegratedEvaluator()
    student_answer = """
    이몽룡은 신분을 숨김으로써 춘향의 진심을 확인하고자 했습니다.
    당시 조선시대 신분제 사회에서 양반과 기생의 딸이라는 신분 차이는
    큰 장벽이었습니다. 만약 처음부터 신분을 밝혔다면, 춘향의 반응이
    진심인지 아니면 신분에 대한 경외심인지 구분하기 어려웠을 것입니다.
    """
    
    result = await evaluator.evaluate_comprehensive(student_answer)
    
    print("\n통합 평가 결과:")
    print(f"- 질적 점수: {result['통합_평가']['질적_점수']}점")
    print(f"- 정량 점수: {result['통합_평가']['정량_점수']}점")
    print(f"- 총점: {result['통합_평가']['총점']}점")
    print(f"- 등급: {result['통합_평가']['등급']}")
    
    print("\n개인 맞춤 피드백:")
    for feedback in result['개인_피드백']:
        print(f"  {feedback}")
    print()


async def main():
    """모든 테스트 실행"""
    print("\n🎓 고전문학 사고유도 AI 시스템 테스트\n")
    
    # 환경 변수 체크
    import os
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  경고: GEMINI_API_KEY가 설정되지 않았습니다.")
        print("   .env 파일을 생성하고 GEMINI_API_KEY를 설정해주세요.")
        print("   테스트를 계속하면 일부 기능이 작동하지 않을 수 있습니다.\n")
    
    try:
        # Test 1: 사고유도
        await test_thought_inducer()
        
        # Test 2: Gemini 평가
        await test_gemini_evaluator()
        
        # Test 3: 언어 분석
        test_language_analyzer()
        
        # Test 4: 통합 평가
        await test_integrated_evaluator()
        
        print("=" * 60)
        print("✅ 모든 테스트 완료!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # .env 파일 로드
    from dotenv import load_dotenv
    load_dotenv()
    
    # 테스트 실행
    asyncio.run(main())
