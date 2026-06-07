class CatalogAgent:
    def __init__(self, tools):
        self.tools = tools

    def search(self, message, tool_name="search_catalog_tool", intent=None):
        result = self.tools.run_core_tool(message, intent)
        return result, [{"name": tool_name, "params": result.get("params", {})}]
