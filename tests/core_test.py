import sys
import os
import warnings

# Kss 및 기타 라이브러리 경고/로그 숨기기
os.environ["KSS_VERBOSE"] = "0"
warnings.filterwarnings("ignore")

# 패키지 경로 설정
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from backend.logic.analyzer import LogicAnalyzer
    from backend.logic.generator import QuestionGenerator
except ImportError:
    print("오류: 프로젝트 폴더 구조를 확인해주세요.")
    sys.exit(1)

def main():
    analyzer = LogicAnalyzer()
    generator = QuestionGenerator()
    
    # 텍스트 정의
    text = """산업혁명은 생산 방식의 변화를 통해 사회 구조 전반에 큰 영향을 미쳤다. 이로 인해 도시화가 가속되었으며 노동 계층이 새롭게 형성되었다."""

    # 1. 분석 (불필요한 로그 생략을 위해 stdout 잠시 차단하거나 로직만 수행)
    nodes = analyzer.analyze(text)
    
    # 2. 가장 중요한 핵심 문장 하나만 선정 (보통 첫 문장 혹은 가장 강한 Role)
    key_nodes = [n for n in nodes if n['is_key_node']]
    target = key_nodes[0] if key_nodes else nodes[0]

    # 3. 질문 생성
    question = generator.generate(target)

    # 4. 결과 출력 (군더더기 없이 출력)
    print("\n" + "="*40)
    print(f"■ 핵심 문장: {target['text']}")
    print(f"▶ AI 질문  : {question}")
    print("="*40 + "\n")

if __name__ == "__main__":
    # Kss가 내부적으로 print를 사용하므로, 실행 시 실시간으로 발생하는 잡음을 막기 위해 로직 실행
    # (일부 로그는 환경변수로 제어되지 않을 수 있으나 최대한 억제됨)
    main()
