import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator,List,TypedDict,Dict , Any , Optional
from dataclasses import asdict

from groq import AsyncGroq

from agent.state import Message , AgentState , ToolResult,StreamEvent

from tools.definitions import TOOL_REGISTRY , get_tool_definitions , validate_tool_list

from tools.tools_implementation import CodebaseTools
import re
import os
from dotenv import load_dotenv


load_dotenv()

logger = logging.getLogger(__name__)


class CodebaseAgent:
    def __init__(self, session_id:str , model:str ="llama-3.3-70b-versatile" , repo_path:str='.',vector_db=None):
        self.model = model
        self.conversation_history: List[Message] = []
        self.max_history=50
        self.system_prompt = self._build_system_prompt()
 
        self.client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
        self.session_id = session_id
        self.tools = CodebaseTools(collection = vector_db , session_id = self.session_id)




    def _build_system_prompt(self)->str:
        """Build comprehensive system prompt"""
        return """You are an expert codebase assistant. Your role is to help developers understand, navigate, and work with their codebases efficiently.
 
        ## Capabilities
        You have access to specialized tools for:
        - **Code Search**: Semantic, keyword search across the codebase
        - **File Operations**: Find files, read content, list directories
        - **Code Analysis**: Analyze functions, classes, dependencies
        - **Git Integration**: Get history, blame information
        
 
        ## Your Approach
        1. **Understand the Context**: Ask clarifying questions if needed
        2. **Use the Right Tool**: Choose the most efficient tool for the task
        3. **Show Your Thinking**: Explain what you're looking for and why
        4. **Provide Context**: Include relevant code snippets in responses
        5. **Be Accurate**: Use exact file paths and line numbers
        6. **Handle Edge Cases**: Gracefully handle missing files or errors
 
        ## Behavior Guidelines
        - Always verify tool results before providing final answers
        - If a tool fails, try alternative approaches
        - Provide file paths relative to repo root
        - Include line numbers for code references
        - Explain complex code structures in simple terms
        - Chain tools together when needed to answer complex questions
 
        ## Response Format
        When providing code examples:
        ```language
        code here
        ```
 
        When referencing files:
         `file_path/to/file.py:line_number`
 
        When summarizing findings:
        - Start with the main answer
        - Provide relevant code context
        - Link related files or functions
        - Suggest next steps if applicable 
        
        CRITICAL RULE: When calling a function, you MUST ONLY use the exact parameters defined in the schema. Do not hallucinate or invent new parameters. Ensure integers are integers, not strings."
        """
    

    def add_messages(self, role:str , content:str , tool_calls:List[Dict]=None,tool_results:List[ToolResult] = None):
        msg = Message(
            role = role,
            content = content,
            toolcalls = tool_calls or [],
            tool_result = tool_results or []
        )

        self.conversation_history.append(msg)

        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]


    def _format_messages_for_groq(self) -> list:
        
        clean_messages = []

        strict_prompt = self.system_prompt + "\n\nCRITICAL RULE: When calling a function, you MUST ONLY use the exact parameters defined in the schema. Do not hallucinate or invent new parameters. Ensure integers are integers, not strings."
        
        clean_messages.append({"role": "system", "content": strict_prompt})
        
        for msg in self.conversation_history:

            if hasattr(msg ,"role"):
               role = msg.role
               content = getattr(msg,"content","")

            elif hasattr(msg , "type"):
                role = "assistant" if msg.type == "ai" else "user"
                content = getattr(msg, "content", "")
            elif isinstance(msg, dict):
                role = msg.get("role")
                content = msg.get("content", "")
            else:
                continue

            if not isinstance(content , str):
                content = str(content) if content is not None else ""



        
            if role in ["user", "assistant", "system","ai"]:
                mapped_role = "assistant" if role == "ai" else role
                clean_messages.append({
                    "role": mapped_role,
                    "content": content
                })
                
        return clean_messages
    

    async def stream_response(self, query: str) -> AsyncGenerator[StreamEvent, None]:
        self.add_messages("user", query)

        yield{
           "type": "thinking",
           "data": {"thought": "Analyzing your query and determining the best approach..."},
           "timestamp": datetime.now().isoformat()
        }
        
        message = self._format_messages_for_groq()

        try:
            tool_def = get_tool_definitions()

            kwargs = {
                "model":self.model,
                "messages":message,
                "stream":False,
                "parallel_tool_calls":False,
                "temperature":0.0
            }

            if tool_def:
                kwargs["tools"] = tool_def

                kwargs["tool_choice"] = "auto"
                print(f"[AGENT] Firing payload to Groq Cloud WITH {len(tool_def)} TOOLS ACTIVE...")
            
            else:
                print(f"[AGENT] WARNING: tool_defs is empty! Tools are NOT active.")

            response = await self.client.chat.completions.create(**kwargs)
            
            if response is None:
                raise ValueError("Groq returned an empty response.")

            
            response_message = response.choices[0].message

            full_response = response_message.content or ""

            if full_response:
                yield {
                    "type": "text",
                    "data": {"text":full_response},
                    "timestamp":datetime.now().isoformat()
                }
            
            
            current_tool_calls = []

            if getattr(response_message , 'tool_calls',None):
                for tool_call in response_message.tool_calls:
                    t_name = tool_call.function.name
                    t_args_str = tool_call.function.arguments

                    print(f"\n[TOOL DETECTED]: AI is calling '{t_name}'")
                    print(f"[TOOL ARGS]: {t_args_str}")

                    t_args = {}

                    if t_args_str:
                        try:
                            t_args = json.loads(t_args_str)

                        except Exception:
                            t_args = {}

                    current_tool_calls.append({
                        "function": {
                            "name": t_name,
                            "arguments": t_args
                        }
                    })

                    yield{
                        "type": "tool_call",
                        "data": {
                            "tool_name": t_name,
                            "input": t_args
                        },
                        "timestamp": datetime.now()
                    }
            if current_tool_calls:
                self.add_messages("assistant", full_response, tool_calls=current_tool_calls)
                tool_result_list = []

                for tc in current_tool_calls:
                    func = tc.get('function', {})
                    name = func.get('name')
                    args = func.get('arguments', {})

                    if not name:
                        continue

                    result_data = await self._execute_tool(name, args)

                    yield{
                        "type": "tool_result",
                        "data": result_data,
                        "timestamp": datetime.now()
                    } 

                    tool_result_list.append(ToolResult(
                        tool_name=name, 
                        success=result_data.get("success", False),
                        output=result_data
                    ))

                self.add_messages("user", "Tool execution completed", tool_results=tool_result_list)
                
                async for next_event in self.stream_response("Review the execution payload and formulate your descriptive codebase summary response based exactly on these outputs."):
                    yield next_event
                            
            else:   
                self.add_messages("assistant", full_response)
                yield{
                    "type": "end",
                    "data": {"answer": full_response},
                    "timestamp": datetime.now()
                }
        except Exception as e:
            import traceback
           
            print("AI HALLUCINATION CAUGHT")
            
            
            if hasattr(e, 'body') and isinstance(e.body, dict):
                typo = e.body.get('error', {}).get('failed_generation', str(e.body))
                print(f"WHAT THE AI TYPED:\n{typo}")

                match = re.search(r'<function=([a-zA-Z0-9_]+)[^>\{]*(\{.*\})', typo)

                if match:
                    t_name = match.group(1)
                    t_args_str = match.group(2)

                    print(f"🩹 SELF-HEALING: Successfully recovered tool '{t_name}'!")
                    try:
                        t_args = json.loads(t_args_str)

                        yield {
                            "type": "tool_call",
                            "data": {
                                "tool_name": t_name,
                                "input": t_args
                            },
                            "timestamp": datetime.now().isoformat()
                        }

                        result_data = await self._execute_tool(t_name, t_args)

                        yield {
                            "type": "tool_result",
                            "data": result_data,
                            "timestamp": datetime.now().isoformat()
                        }

                        self.add_messages(
                            "assistant",
                            "Executed recovered tool.",
                            tool_calls=[{"function": {"name": t_name, "arguments": t_args}}]
                        )

                        self.add_messages(
                            "user",
                            "Tool execution completed",
                            tool_results=[ToolResult(tool_name=t_name, success=result_data.get("success", False), output=result_data)]
                        )

                        async for next_event in self.stream_response("Review the execution payload and formulate your final descriptive response."):
                            yield next_event

                        return
                    
                    except Exception as e:
                        print(f" Failed to auto-heal JSON:")

                    

            else:
                print(f"RAW ERROR:\n{traceback.format_exc()}")
                
            
            yield {
                "type": "error",
                "data": {"error": "The AI generated malformed tool JSON. Check the terminal!"},
                "timestamp": datetime.now().isoformat()
            }
            return
            
                # if t_calls:
                #     for i, tc in enumerate(t_calls):
                #         func = tc.get('function', {}) if isinstance(tc, dict) else getattr(tc, 'function', None)
                #         if func:
                #             idx = tc.get('index', i) if isinstance(tc, dict) else getattr(tc, 'index', i)
                #             if idx not in compiled_tool_calls:
                #                 compiled_tool_calls[idx] = {"name": None, "arguments": ""}
                            
                #             n = func.get('name') if isinstance(func, dict) else getattr(func, 'name', None)
                #             a = func.get('arguments') if isinstance(func, dict) else getattr(func, 'arguments', None)
                            
                #             if n:
                #                 compiled_tool_calls[idx]["name"] = n
                #             if a:
                #                 if isinstance(a, str):
                #                     compiled_tool_calls[idx]["arguments"] += a
                #                 elif isinstance(a, dict):
                #                     compiled_tool_calls[idx]["arguments"] = a

            # current_tool_calls = []
            # for idx, tool_data in compiled_tool_calls.items():
            #     t_name = tool_data.get("name")
            #     t_args = tool_data.get("arguments", "")
                
            #     if t_name:
            #         if isinstance(t_args, str) and t_args.strip():
            #             try:
            #                 t_args = json.loads(t_args)
            #             except Exception:
            #                 t_args = {}
            #         elif not isinstance(t_args, dict):
            #             t_args = {}
                        
            #         current_tool_calls.append({
            #             "function": {
            #                 "name": t_name,
            #                 "arguments": t_args
            #             }
            #         })

            #         yield{
            #             "type": "tool_call",
            #             "data": {
            #                 "tool_name": t_name,
            #                 "input": t_args
            #             },
            #             "timestamp": datetime.now()
            #         }
            
        #     if current_tool_calls:
        #         self.add_messages("assistant", full_response, tool_calls=current_tool_calls)
        #         tool_result_list = []

        #         for tc in current_tool_calls:
        #             func = tc.get('function', {})
        #             name = func.get('name')
        #             args = func.get('arguments', {})

        #             if not name:
        #                 continue

        #             result_data = await self._execute_tool(name, args)

        #             yield{
        #                 "type": "tool_result",
        #                 "data": result_data,
        #                 "timestamp": datetime.now()
        #             } 

        #             tool_result_list.append(ToolResult(
        #                 tool_name=name, 
        #                 success=result_data.get("success", False),
        #                 output=result_data
        #             ))

        #         self.add_messages("user", "Tool execution completed", tool_results=tool_result_list)
                
        #         async for next_event in self.stream_response("Review the execution payload and formulate your descriptive codebase summary response based exactly on these outputs."):
        #             yield next_event
                            
        #     else:   
        #         self.add_messages("assistant", full_response)
        #         yield{
        #             "type": "end",
        #             "data": {"answer": full_response},
        #             "timestamp": datetime.now()
        #         }
        # except Exception as e:
        #     import traceback
           
        #     print("AI HALLUCINATION CAUGHT")
            
            
        #     if hasattr(e, 'body') and isinstance(e.body, dict):
        #         typo = e.body.get('error', {}).get('failed_generation', str(e.body))
        #         print(f"WHAT THE AI TYPED:\n{typo}")

        #     else:
        #         print(f"RAW ERROR:\n{traceback.format_exc()}")
                
            
        #     yield {
        #         "type": "error",
        #         "data": {"error": "The AI generated malformed tool JSON. Check the terminal!"},
        #         "timestamp": datetime.now().isoformat()
        #     }
        #     return

    async def _execute_tool(self , tool_name , tool_input):
        valid , message = validate_tool_list(tool_name , tool_input)

        if not valid:
            return {"success":False , "error":message }
        
        tool_handler = {
            "search_code":self.tools.search_code,
            "find_file":self.tools.find_file,
            "get_file_content":self.tools.get_file_content,
            "list_directory":self.tools.list_directory,
            "analyze_function": self.tools.analyze_function,
            "analyze_class": self.tools.analyze_class,
            "get_dependencies": self.tools.get_dependencies,
            "get_git_log": self.tools.get_git_log,
            "get_git_blame": self.tools.get_git_blame
        }

        handler = tool_handler.get(tool_name)

        if not handler:
            return {"success": False , "error": f"Tool {tool_name} not Found"}
        
        try:
            return await handler(**tool_input)

        except Exception as e:
            return {"success":False , "error":str(e)}
        


    def get_serialized_history(self)->List[Dict[str , Any]]:
        return [
            {
                "role":msg.role,
                "content":msg.content,
                "timestamp":datetime.now(),
                "tool_calls":getattr(msg, 'toolcalls', []),
                "tool_result":[asdict(r) for r in msg.tool_results]  
            }
            for msg in self.conversation_history
        ]
                      

    











                








        
    








    






