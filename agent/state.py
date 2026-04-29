from typing import TypedDict , Annotated , List , Optional
import operator


class AgentState(TypedDict):
    user_id: str
    session_id: str

    query: str
    repo_url: str
    

    rewritten_query: str

    intent: str
    target_file: Optional[str]

    
    retrieved_docs: List[dict]

    answer: str

    steps: Annotated[List[str] , operator.add]

    recent_context:str
    
