from typing import TypedDict, Annotated, Dict, Any
from operator import add
from langchain_core.messages import AnyMessage


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add]

class StreamEvent(TypedDict):
    type: str
    data: Dict[str, Any]
    timestamp: str






    
