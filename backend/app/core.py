import sys
import os

# 패키지 경로를 추가하여 어디서든 실행 가능하게 함
# 패키지 경로를 추가하여 어디서든 실행 가능하게 함
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.logic.analyzer import LogicAnalyzer
from app.logic.evaluator import Evaluator
from app.logic.generator import QuestionGenerator
from app.logic.session import SessionManager

class OkDokHaeCore:
    """
    옥독해의 핵심 파이프라인을 관리하는 통합 클래스입니다.
    웹 서버(FastAPI) 없이 로직만 수행합니다.
    """
    def __init__(self):
        self.analyzer = LogicAnalyzer()
        self.evaluator = Evaluator()
        self.generator = QuestionGenerator()
        self.session_manager = SessionManager()

    def process_text(self, text: str):
        """
        텍스트를 분석하고 세션을 시작합니다.
        """
        nodes = self.analyzer.analyze(text)
        session_id = self.session_manager.create_session(nodes)
        session = self.session_manager.get_session(session_id)
        
        target_node = session["key_nodes"][session["current_node_idx"]]
        question = self.generator.generate(target_node)
        
        return {
            "session_id": session_id,
            "question": question,
            "target_node": target_node
        }

    def process_answer(self, session_id: str, answer: str):
        """
        사용자 답변을 평가하고 다음 단계를 결정합니다.
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            return {"error": "세션을 찾을 수 없습니다."}

        target_node = session["key_nodes"][session["current_node_idx"]]
        evaluation = self.evaluator.evaluate_answer(answer, target_node["text"])
        
        result = {
            "is_passed": evaluation["is_passed"],
            "feedback": evaluation["feedback"],
            "next_question": None,
            "completed": False
        }

        if evaluation["is_passed"]:
            has_next = self.session_manager.move_to_next_node(session_id)
            if has_next:
                new_target = session["key_nodes"][session["current_node_idx"]]
                result["next_question"] = self.generator.generate(new_target, session["history"])
            else:
                result["completed"] = True
                result["next_question"] = "모든 분석을 마쳤습니다."
        else:
            result["next_question"] = self.generator.generate_feedback_question(evaluation)

        self.session_manager.update_session(session_id, answer)
        return result

if __name__ == "__main__":
    # 간단한 터미널 실행 예시
    core = OkDokHaeCore()
    test_text = "산업혁명은 생산 방식의 변화를 통해 사회 구조 전반에 큰 영향을 미쳤다."
    print("분석 결과:", core.process_text(test_text))
