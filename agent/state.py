from typing import TypedDict , Annotated , List , Optional, Dict , Any
from dataclasses import dataclass , field
from datetime import datetime
import operator


@dataclass
class ToolResult:
    tool_name:str
    success:bool
    output:Any
    error:Optional[str] = None
    execution_time_ms:float = 0.0


@dataclass
class Message:
    role:str
    content:str
    timestamp:datetime = field(default_factory=datetime.now)
    toolcalls:List[Dict[str,Any]] = field(default_factory=list)
    tool_result:List[Dict[str,Any]] = field(default_factory=list)



    
class AgentState(TypedDict):
    user_id: str
    session_id: str
    timestamp:str

    query: str
    repo_url: str
    

    rewritten_query: str
    confidence:float
 
    plan:List[dict]
    tool_calls_made:Annotated[List[dict] , operator.add]

    retrieved_docs:Annotated[List[dict],operator.add]
    file_matches:List[str]

    active_tools:List[Dict]
    tool_results:Annotated[List[ToolResult] , operator.add]

    conversation_history:List[Message]
    recent_context:str
    context_summary:str

    thoughts:Annotated[list[str] , operator.add]
    steps_taken:Annotated[list[str] , operator.add]
    
    response:str
    confidence_score:str
    sources:List[str]

    token_used:int
    execution_time_ms:float
    error:Optional[str]


class StreamEvent(TypedDict):
    type:str
    data:Dict[str,Any]
    timestamp:datetime


class ToolCallInput(TypedDict):
    tool_name:str
    arguments:Dict[str,Any]


class ToolDefinition(TypedDict):
    name:str
    description:str
    category:str
    input_schema:Dict[str,Any]
    required_field:List[str]
    handler:callable
    requires_context:List[str]
    async_compatible:bool













    
