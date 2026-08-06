import importlib

from langchain_core.messages import HumanMessage


def test_workflow_returns_friendly_message_when_llm_fails(monkeypatch):
    graph = importlib.import_module("src.orchestrator.graph")

    class FailingLLM:
        def __init__(self, *args, **kwargs):
            pass

        def bind_tools(self, mcp_tools):
            return self

        def invoke(self, messages):
            raise RuntimeError("quota exceeded")

    monkeypatch.setattr(graph, "ChatGroq", FailingLLM)

    app = graph.build_workflow([])
    result = app.invoke({"messages": [HumanMessage(content="hello")]})

    assert result["messages"][-1].content.startswith("I couldn't process")
    assert "quota exceeded" in result["messages"][-1].content
