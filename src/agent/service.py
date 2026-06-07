from src.agent.graph import AgentGraph


class AgentService:
    def __init__(self, graph=None):
        self.graph = graph or AgentGraph()

    def chat(self, message, history=None, session_id=None):
        return self.graph.invoke(message, history or [], session_id=session_id)
