from src.core.engine import run_text_to_api


class BurgerPrintsTools:
    def run_core_tool(self, message, intent=None):
        return run_text_to_api(message, intent_override=intent)
