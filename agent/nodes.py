from agent.state import AgentState
from retrieval.vector_retrieval import vector_retrieval
from retrieval.direct_retrieval import FileMatch
from llm.generator import Generate_response
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from router.intent_router import IntentRouter


ambigous_words = { "it", "that", "this", "they", "them",
    "the function", "the file", "the class",
    "more", "also", "same", "further", "explain more","these"}


def get_needs_history(query):
    return any(m in query.lower().split() for m in ambigous_words)


## Node a
def rewrite_query(state:AgentState , llm)-> AgentState:
    recent_context = ""


    query = state['query']
    
    if get_needs_history(query):
        recent_context = state.get('recent_context' , "")
        print("Using History")

    else:
        print("Independent Query")



    prompt = ChatPromptTemplate.from_messages([
        ("system", """Rewrite the question for code search.
If conversation history is provided, use it to resolve
references like 'it', 'that', 'this file'.
If no history or self-contained query, just improve the query.
Return ONLY the rewritten query."""),
        ("human", "History:\n{recent_context}\n\nQuestion: {query}")
    ])
   

    result = (prompt | llm).invoke({
            "query" : query,
            "recent_context": recent_context
           
    })
    rewritten = result.content.strip()
    print(f"Rewritten Query: {rewritten}")

    return  {
        **state, "rewritten_query": rewritten , "steps" : ["rewrite_query"]
    }

## Node b

def route_intent(state: AgentState , llm , collection) -> AgentState:
    router =  IntentRouter(llm , collection)

    result = router.route(state['query'] , state['repo_url'])


    return {**state , "intent": result["intent"] , "target_file" : result.get("target_file") , "steps": ["route_intent"]}



## Node c
def vector_search(state: AgentState , collection) -> AgentState:
    retriever = vector_retrieval(collection)
    
    docs = retriever.retrieve(
        query = state['rewritten_query'],
        repo_url = state['repo_url'],
        top_k = 5)
    
    return {**state , "retrieved_docs": docs ,  "steps":["vector_search"]}

## Node d
def direct_search(state: AgentState , collection) -> AgentState:
    direct_retreiver = FileMatch(collection)

    docs = direct_retreiver.retrieve(
        query = state['rewritten_query'],
        repo_url = state['repo_url']
    )

    if not docs:
        return vector_search(state , collection)
    
    return {**state , "retrieved_docs":docs , "steps": ["direct_search"]}

# Node e
def graph_search(state: AgentState , collection) -> AgentState:
    retriever = vector_retrieval(collection)

    docs = retriever.retrieve(
        query = state['rewritten_query'],
        repo_url = state['repo_url'],
        top_k = 5,
        mode = "graph"
    )

    if not docs:
        return vector_search(state , collection)
    
    return {**state , "retrieved_docs":docs , "steps": ["graph_search"]}
    

## Node f
def generate_res(state: AgentState):
    genr = Generate_response()
    
    context = "\n\n".join([
        f"File: {Path(d['metadata'].get('source' , 'unknown')).name}\n{d['page_content']}"

        for d in state["retrieved_docs"]
    ])
    response = genr.generate(
       state['rewritten_query'],
       context
    )

    return {**state , "answer":response, "steps":["generate_answer"]}



