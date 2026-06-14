import os
import logging
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, List
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage,BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from agent.state import AgentState, StreamEvent
from tools.tools_implementation import get_agent_tools # <--- Uses the factory we built!

logger = logging.getLogger(__name__)

load_dotenv()


class CodebaseAgent:
    def __init__(self, session_id: str, user_id:str , model: str = "llama-3.3-70b-versatile", repo_path: str = '.', vector_db=None,max_iterations=15):
        self.session_id = session_id
        self.model = model
        self.vector_db = vector_db
        self.user_id = user_id
        self.conversation=self.vector_db['chat_history']

        self.max_iterations=max_iterations
        
        self.tools = get_agent_tools(self.session_id, self.user_id ,self.vector_db)
        
        self.llm = ChatGroq(
            model=self.model,
            temperature=0.0,
            api_key=os.environ.get("GROQ_API_KEY"),
            max_retries=2
        )
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        workflow = StateGraph(AgentState)
        
        workflow.add_node("agent", self.call_model)
        workflow.add_node("tools", ToolNode(self.tools)) 


        workflow.add_edge(START, "agent")

        workflow.add_conditional_edges("agent", tools_condition) # Auto-routes to 'tools' or 'END' natively!
        
        workflow.add_edge("tools","agent")

        
        self.graph = workflow.compile()
        self.conversation_history:List[BaseMessage] = [] ## LONG TERM MEMORY FOR QA

    def _build_system_prompt(self) -> str:
        return """You are a senior codebase assistant. 
                Instructions:
                1. Use the provided tools to search the repository.
                2. When a tool returns the information you need, your search is complete.
                3. Do not call any further tools once you have the answer.
                4. Generate your final response to the user immediately.
               """
        

    def load_history_from_db(self,limit=10):
        docs = list(
            self.conversation.find({"session_id":self.session_id}).sort("timestamp",-1).limit(limit * 2)
        )

        docs.reverse()

        messages = []

        for doc in docs:
            if doc["role"] == "user":
                messages.append(HumanMessage(content=doc["query"]))
            
            elif doc["role"] == "assistant":
                messages.append(AIMessage(content=doc["content"]))


        return messages
    # async def reasoning_node(self,state):
    #     messages=state["messages"]

    #     prompt = """
    #             You are evaluating tool outputs.
    #             Decide:
    #                - Do we need more tool calls?
    #                - Or can we answer now?
                   
    #             Reply ONLY:
                
    #             STATUS: CONTINUE

    #             or

    #             STATUS: END
                
    #             """

    #     response=await self.llm.ainvoke([
    #         SystemMessage(content=prompt),
    #         *messages
    #     ])

    #     return {
    #         "messages":[response]
    #     }

    async def call_model(self, state: AgentState):
        messages = state["messages"]


        sys_prompt = SystemMessage(content=self._build_system_prompt())
        
        response = await self.llm_with_tools.ainvoke([sys_prompt] + messages)
        return {"messages": [response]}
    

    # def _should_continue(self,state):
    #     messages = state["messages"]

    #     last_message = messages[-1]

    #     text = str(last_message.content).lower()

    #     if "continue" in text:
    #         return "agent"
        
    #     return "final"
     
    # async def generate_final_answer(self,state:AgentState):
    #     messages = state["messages"]

    #     clean_messages = [m for m in messages if not (isinstance(m, AIMessage) and "STATUS: END" in str(m.content))]

    #     prompt = """
    #             You are generating the final response to the user.
    #             Use:
    #                - tool outputs
    #                - retrieved code
    #                - repository findings
 
    #             Generate:
    #                - concise
    #                - accurate
    #                - developer-friendly answer

    #             Include:
    #               - exact file paths
    #               - relevant snippets
    #               - explanations
    #             """

    #     response = await self.llm.ainvoke([
    #             SystemMessage(content=prompt),
    #             *clean_messages
    #     ])

    #     return {
    #         "messages":[response]
    #     } 
        

    async def stream_response(self, query: str) -> AsyncGenerator[StreamEvent, None]:
        """Streams the LangGraph execution back to the FastAPI frontend."""
        MAX_HISTORY = 15

        yield {
            "type": "thinking",
            "data": {"thought": "Analyzing your query and determining the best approach...","session_id":self.session_id},
            "timestamp": datetime.now().isoformat()
        }
        logger.info( f"[SESSION:{self.session_id}] Query={query}")

        execution_messages = self.load_history_from_db(limit=10)

        execution_messages.append(HumanMessage(content=query))

        final_answer = ""
        
        try:
            config = {"recursion_limit": self.max_iterations} 
            
            async for event in self.graph.astream({"messages": execution_messages}, config=config, stream_mode="updates"):
                
                if "agent" in event:
                    msg = event["agent"]["messages"][0]
                    # self.conversation_history.append(msg)

                    # if len(self.conversation_history) > MAX_HISTORY:
                    #     self.conversation_history=self.conversation_history[-MAX_HISTORY:]
                    
                    if msg.tool_calls:
                        for tc in msg.tool_calls:
                            yield {
                                "type": "tool_call",
                                "data": {"tool_name": tc["name"], "input": tc["args"],"session_id":self.session_id},
                                "timestamp": datetime.now().isoformat()
                            }
                            
                    elif msg.content and not msg.tool_calls:

                        final_answer = msg.content

                        yield {
                            "type": "text",
                            "data": {"text": msg.content},
                            "timestamp": datetime.now().isoformat()
                        }
                        yield {
                            "type": "end",
                            "data": {"answer": msg.content},
                            "timestamp": datetime.now().isoformat()
                        }
                        
                elif "tools" in event:
                    tool_messages = event["tools"]["messages"]


                    for t_msg in tool_messages:

                        logger.info(f"[SESSION:{self.session_id}] Tool={t_msg.name} | Output={str(t_msg.content)[:150]}")

                        yield {
                            "type": "tool_result",
                            "data": {"tool_name":t_msg.name, "success": True, "output": t_msg.content,"session_id":self.session_id},
                            "timestamp": datetime.now().isoformat()
                        }
                        

                # elif "reasoning" in event:
                #     messages = event["reasoning"]["messages"]

                #     last_message = messages[-1]

                #     self.conversation_history.append(AIMessage(content=f"Reasoning summary: {last_message.content[:150]}"))

                #     logger.info(f"[SESSION:{self.session_id}] Reasoning={last_message.content[:100]}")

                #     yield {
                #         "type":"reasoning",
                #         "data":{
                #             "analysis": last_message.content[:300],
                #             "session_id": self.session_id
                #         },
                #         "timestamp":datetime.now().isoformat()
                #     }

                # elif "final" in event:
                #     msg = event["final"]["messages"][0]

                #     final_answer = msg.content

                #     yield {
                #         "type":"text",
                #         "data":{"text":msg.content},
                #         "timestamp": datetime.now().isoformat()
                #     }
            if final_answer:
                self.conversation.insert_one({
                    "session_id": self.session_id,
                    "user_id": self.user_id,
                    "role": "user",
                    "query": query,
                    "content": query,
                    "timestamp": datetime.utcnow()
                })
                self.conversation.insert_one(
                    {
                        "session_id":self.session_id,
                        "user_id":self.user_id,
                        "role":"assistant",
                        "query":query,
                        "content":final_answer,
                        "timestamp":datetime.now()                    }
                )

                if len(self.conversation_history) > MAX_HISTORY:
                    self.conversation_history=self.conversation_history[-MAX_HISTORY:]

                

        except Exception as e:
            yield {
                "type": "error",
                "data": {"error": f"Agent stopped: {str(e)}"},
                "timestamp": datetime.now().isoformat()
            }

    def get_serialized_history(self) -> List[Dict[str, Any]]:
        serialized = []
        for msg in self.conversation_history:
            role = "user" if isinstance(msg, HumanMessage) else "assistant" if isinstance(msg, AIMessage) else "tool"
            serialized.append({
                "role": role,
                "content": str(msg.content),
                "timestamp": datetime.now().isoformat()
            })
        return serialized





                








        
    








    






