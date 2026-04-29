from agent.state import AgentState


def route_by_intent(state: AgentState) -> str:
    intent = state['intent']
    print(f"LLm Identified Intent {intent}")

    return intent
    

    
    