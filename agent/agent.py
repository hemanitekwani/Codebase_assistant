from functools import partial
from langgraph.graph import StateGraph , END
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from agent.state import AgentState
from agent.nodes import(
    rewrite_query,
    route_intent,
    vector_search,
    direct_search,
    graph_search,
    generate_res
)
from agent.edges import route_by_intent

import os

load_dotenv()

gemini_key = os.getenv('GOOGLE_API_KEY')


def build_agent(collection , llm = None):
    if llm is None:
        llm = ChatGoogleGenerativeAI(model= "gemini-2.5-flash" , google_api_key=gemini_key , temperature = 0)

    
    graph = StateGraph(AgentState)
    graph.add_node("rewrite_query" , partial(rewrite_query , llm = llm))
    graph.add_node("route_intent" , partial(route_intent , llm = llm , collection = collection))
    graph.add_node("vector_search" , partial(vector_search , collection = collection))
    graph.add_node("direct_search" , partial(direct_search , collection = collection))
    graph.add_node("graph_search" , partial(graph_search , collection = collection))
    graph.add_node("generate_response" , partial(generate_res))


    graph.set_entry_point("rewrite_query")
    graph.add_edge("rewrite_query" , "route_intent")


    graph.add_conditional_edges(
        "route_intent",
        route_by_intent,
        {
           "semantic_intent": "vector_search",
           "file_intent": "direct_search",
           "graph_intent": "graph_search"

        }
    )
    graph.add_edge("vector_search",   "generate_response")
    graph.add_edge("direct_search",    "generate_response")
    graph.add_edge("graph_search",     "generate_response")
    graph.add_edge("generate_response", END)

    return graph.compile()



