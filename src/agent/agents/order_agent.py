class OrderAgent:
    def __init__(self, tools):
        self.tools = tools

    def run(self, message, tool_name, intent=None):
        result = self.tools.run_core_tool(message, intent)
        return result, [{"name": tool_name, "params": result.get("params", {})}]
