from src.agent.agents.llm_intent import LlmIntentClassifier
from src.core.config import settings
from src.core.text_parser import detect_intent


class IntentAgent:
    def __init__(self, llm_classifier=None):
        self.llm_classifier = llm_classifier

    def run(self, message):
        intent = detect_intent(message)
        if intent.get("name") != "unknown":
            return intent
        if not settings.llm_intent_enabled or not settings.llm_api_key_present:
            return intent

        classifier = self.llm_classifier or LlmIntentClassifier()
        llm_intent = classifier.classify(message)
        return llm_intent or intent
