from typing import Annotated, Sequence
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """
    מבנה ה-State של הגרף השומר את היסטוריית ההודעות.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]