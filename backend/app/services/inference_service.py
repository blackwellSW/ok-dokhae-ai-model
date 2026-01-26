import logging
import importlib
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class InferenceService:
    _analyzer = None
    _evaluator = None
    _generator = None
    
    @classmethod
    def load_models(cls):
        """Lazy loading of heavy AI models"""
        if cls._analyzer and cls._evaluator and cls._generator:
            return

        logger.info("🧠 Loading AI Models for InferenceService...")
        try:
            # Dynamic import to avoid circular dependencies and load time overhead
            from app.models.analyzer import LogicAnalyzer
            from app.models.evaluator import Evaluator
            from app.models.generator import QuestionGenerator
            
            cls._analyzer = LogicAnalyzer()
            cls._evaluator = Evaluator()
            cls._generator = QuestionGenerator()
            logger.info("✅ AI Models loaded successfully.")
        except ImportError as e:
            logger.error(f"❌ Failed to import model classes: {e}")
            raise e
        except Exception as e:
            logger.error(f"❌ Failed to load AI models: {e}")
            raise e

    def analyze_text(self, text: str) -> dict:
        self.load_models()
        return self._analyzer.analyze(text)

    def evaluate_answer(self, user_answer: str, reference_text: str) -> dict:
        self.load_models()
        return self._evaluator.evaluate_answer(user_answer, reference_text)

    def generate_question(self, node: dict) -> str:
        self.load_models()
        return self._generator.generate(node)

    def generate_feedback(self, evaluation: dict, original_question: str = None, node: dict = None) -> str:
        self.load_models()
        return self._generator.generate_feedback_question(evaluation, original_question, node)
