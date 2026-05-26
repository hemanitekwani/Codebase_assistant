import os 
import subprocess
import json
from typing import Dict,Any,List,Tuple,Optional
import asyncio
from datetime import datetime
import time
import logging
from pathlib import Path
import ast
from retrieval.vector_retrieval import vector_retrieval
from retrieval.direct_retrieval import FileMatch
import fnmatch
from pymongo import MongoClient
import re
import httpx
import tempfile
import subprocess



logger = logging.getLogger(__name__)


class CodebaseTools:
    def __init__(self, collection,session_id):
        self.collection = collection
        

        self.vector_retriever = vector_retrieval(self.collection)
        self.direct_retriever = FileMatch(self.collection)
        self.session_id = session_id

    async def _semantic_search(self,query:str,language:Optional[str] , top_k:int = 5):
        docs = self.vector_retriever.retrieve(
            query = query,
            session_id=self.session_id,
            top_k = top_k
        )

        return self._format_docs(docs)
    

    async def _keyword_search(self, query:str , language:Optional[str] , top_k:int)->List[Dict[str,Any]]:
        try:
            matches=[]

            lang_map= {
                "python": ['.py'],
                "javascript": ['.js' ,'.jsx'],
                "typescript":['.ts' ,'.tsx'],
                "java":['.java'],
                "cpp":['.cpp','.hpp','.cc','.cxx','.h'],
                "go": [".go"],
                "rust": [".rs"],
                "html": [".html", ".htm"],
                "css": [".css"],
                "json": [".json"],
                "yaml": [".yaml", ".yml"],
                "markdown": [".md"]
                
            }
            allowed_ext = None

            if language:
                allowed_ext=lang_map.get(language.lower())

                if not allowed_ext:
                    allowed_ext=[f".{language.lstrip('.').lower()}"]

            query_lower = query.lower()
            client = MongoClient(os.getenv("mongo_client"))
            raw_files_collection = client["codebase"]["raw_repo_files"]


            cursor = raw_files_collection.find({"session_id":self.session_id})

            
            for doc in cursor:
                file_path = doc.get("file_path",{})
                content = doc.get("content" , {})


                if allowed_ext:
                    _ , ext = os.path.splitext(file_path)

                    if ext.lower() not in allowed_ext:
                        continue

                lines = content.splitlines()
                for line_idx,line in enumerate(lines):
                    if query_lower in line.lower():
                        matches.append({
                            "file":file_path,
                            "line_number":line_idx+1,
                            "content":line.rstrip('\r\n'),
                            "match_type":"keyword"
                        })

                        if len(matches) >= top_k:
                            return matches

       
            return matches[:top_k]
        
        except Exception as e:
            print(f"Error in keyword search: {str(e)}")
            return []


    async def _graph_search(self,query:str , language , top_k) -> str:
        docs = self.vector_retriever.retrieve(
            query=query,
            session_id=self.session_id,
            top_k=5,
            mode="graph"
        )

        if not docs:
            return "No graph relationship found"
        
        return self._format_docs(docs)

    
    def _format_docs(self,docs):
        if not docs:
            return "No result."
        
        return "\n\n".join([
            f"File: {Path(d['metadata'].get('source','unknown')).name}\n{d['page_content']}"
            for d in docs
        ])


    async def search_code(self, query:str , language:Optional[str] = None , top_k:int = 5 , search_type:str = 'semantic')-> Dict[str , Any]:
        start_time = time.time()

        try:
            if search_type == 'semantic' and self.collection is not None:
                results = await self._semantic_search(query , language, top_k)

            elif search_type == 'keyword' and self.collection is not None:
                results = await self._keyword_search(query,language , top_k)


            # elif search_type == 'graph' and self.collection:
            #     results = await self._graph_search(query,language , top_k)


            else:
                results = []


            execution_time = (time.time() - start_time) * 1000

            return {
                "success":True,
                "results": results,
                "count": len(results),
                "execution_time_ms": execution_time,
                "search_type":search_type
            }
        
        except Exception as e:
            logger.error(f"Error in search_code: {str(e)}")

            return {
                "success":False,             
                "error": str(e),
                "execution_time_ms": execution_time,
            }
        

        
    async def find_file(self,pattern:str , file_type:Optional[str] = None , max_results:int = 20) -> Dict[str , Any]:
        start_time = time.time()

        try:
            matched_file = []

            ext = f".{file_type.lstrip('.')}" if file_type else None

            has_wildcard = any(char in pattern for char in ['*','?','['])
            
            client = MongoClient(os.getenv("mongo_client"))
            raw_files_collection = client["codebase"]["raw_repo_files"]

            cursor = raw_files_collection.find(
                {"session_id": str(self.session_id)},
                {"file_path": 1, "_id": 0}
            )

            for doc in cursor:
                file_path = doc.get('file_path', {})

                if not file_path:
                    continue

                file_name = os.path.basename(file_path)

                if ext:
                    _, current_ext = os.path.splitext(file_name)
                    if current_ext.lower() != ext:
                        continue

                if has_wildcard:
                    if fnmatch.fnmatch(file_name.lower(), pattern.lower()):
                        matched_file.append(file_path)


                else:
                    if pattern.lower() in file_name.lower():
                        matched_file.append(file_path)


                if len(matched_file) >= max_results:
                    break



            return{
                "success":True,
                "files":matched_file,
                "count":len(matched_file),
                "execution_time_ms": (time.time() - start_time)*1000
            }


        except Exception as e:
            return{
                "success":False,
                "error":str(e),
                "execution_time_ms":(time.time() - start_time)* 1000

            }

    async def get_file_content(self, file_path:str , start_line:Optional[int] = None, end_line:Optional[int] = None) -> Dict[str, Any]:
        start_time = time.time()

        try:
            client = MongoClient(os.getenv("mongo_client"))
            raw_files_collection = client["codebase"]["raw_repo_files"]

            document = raw_files_collection.find_one({
                "session_id": str(self.session_id),
                "file_path":file_path
            })

            if not document:
                return {
                    "success":False,
                    "error":f"File '{file_path} not found",
                    "execution_time_ms":(time.time() - start_time) * 1000
                }
            
            full_text = document["content"]
            lines = full_text.splitlines(keepends=True)
            
            if start_line and end_line:
                start_idx = max(0 , start_line - 1)
                lines = lines[start_line-1:end_line]


            content = ''.join(lines)

            return {
                "success": True,
                "content":content,
                "line_count":len(lines),
                "file_path": file_path,
                "execution_time_ms": (time.time() - start_time) * 1000
            }
        
        except Exception as e:
            logger.error(f"Error in get_file_content: {str(e)}")

            return {
                "success": False,
                "error": str(e),
                "execution_time_ms": (time.time() - start_time) * 1000
            }
        

    async def analyze_function(self, function_name: str, file_path: Optional[str] = None, include_calls: bool = False, include_dependencies: bool = True) -> Dict[str, Any]:
        start_time = time.time()

        try:
            target_file_path = None
            target_content = None
            found_line_no = -1

            client = MongoClient(os.getenv("mongo_client"))
            raw_files_collection = client["codebase"]["raw_repo_files"]


            
            if file_path:
                doc = raw_files_collection.find_one({"session_id":str(self.session_id) , "file_path":file_path})
                
                if doc:
                    target_file_path = file_path
                    target_content = doc.get("content","")




            if not target_content:
                cursor = raw_files_collection.find({"session_id": str(self.session_id)})
                
                for doc in cursor:
                    content = doc.get("content","")
                    current_path = doc.get("file_path","")

                    pattern = re.compile(
                        rf"\b(?:def|function|func|fn|fun)\s+{re.escape(function_name)}\b|\b{re.escape(function_name)}\s*\(", 
                        re.IGNORECASE
                    )
                    lines = content.splitlines()

                    for i , line in enumerate(lines):
                        if pattern.search(line):
                            target_file_path = current_path
                            target_content = content
                            found_line_no = i+1
                            break
        

            if not target_content:
                return {"success": False, "error": f"Function '{function_name}' not found in any supported code files."}
            
            analysis = {
                "name": function_name,
                "file": str(target_file_path)
            }

            _,ext = os.path.splitext(target_file_path)

            if ext.lower() == '.py':

                try:                   
                    tree = ast.parse(target_content)

                    func_def = next((node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == function_name), None)

                    if func_def:
                        analysis["line_number"] = func_def.lineno
                        analysis["end_line"] = func_def.end_lineno
                        analysis["args"] = [arg.arg for arg in func_def.args.args]
                        analysis['returns'] = ast.unparse(func_def.returns) if func_def.returns else None
                        analysis['docstring'] = ast.get_docstring(func_def)
                        analysis['decorators'] = [ast.unparse(d) for d in func_def.decorator_list]
                    else:
                        analysis["warning"] = "AST could not locate function structure"
                        analysis["line_number"] = found_line_no

                except SyntaxError:
                    analysis["warning"] = "Syntax error in Python file, Could not parse AST"
                    analysis["line_number"] = found_line_no
            else:
                analysis["line_number"] = found_line_no
                analysis["warning"] = f"Deep AST parsing is only supported for Python. Showing basic text match for {target_file.suffix} file."

                try:
                    lines = target_content.splitlines(keepends=True)
                    start = max(0, found_line_no - 1)
                    analysis['code_preview'] = "".join(lines[start:start + 100])
                except Exception:
                    pass

            return {
                "success": True,
                "analysis": analysis,
                "execution_time_ms": (time.time() - start_time) * 1000
            }  

        except Exception as e:
            return {
                "success": False,
                "error": f"Error analyzing function: {str(e)}",
                "execution_time_ms": (time.time() - start_time) * 1000
            }

        
    async def get_git_log(self , file_path:Optional[str] = None , limit:int = 10 , format:str = "summary")->Dict[str, Any]:
        start_time = time.time()

        try:
            doc = self.collection.find_one({"session_id":str(self.session_id)})

            if not doc or "metadata" not in doc or "repo_url" not in doc["metadata"]:
                return {"success": False, "error": "Could not find a valid GitHub repo_url for this session in the database."}
            

            repo_url = doc["metadata"]["repo_url"]

            clean_url = repo_url.rstrip(".git").rstrip("/")
            parts = clean_url.split("github.com/")[-1].split("/")

            if len(parts) < 2:
                return {"success": False, "error": f"Invalid GitHub URL format: {repo_url}"}
            
            owner, repo = parts[0], parts[1]


            api_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
            params = {"per_page": limit}


            if file_path:
                params["path"] = file_path
            

            headers = {"Accept": "application/vnd.github.v3+json"}


            async with httpx.AsyncClient() as client:
                response = await client.get(api_url , params=params,headers=headers)


            if response.status_code == 403:
                return {"success":False ,"error":"GitHub API rate limit exceeded (60 requests/hr for unauthenticated users)."}

            elif response.status_code != 200:
                return {"success":False ,"error":"GitHub API error ({response.status_code}):{response.text}"}
            
            commits = response.json()

            log_summary = ""


            for c in commits:
                sha = c["sha"][:7]
                author = c["commit"]["author"]["name"]
                message = c["commit"]["message"].split('\n')[0]
                date = c["commit"]["author"]["date"]
                log_summary += f"[{sha}] {date} - {author} : {message}\n"



            return {
                "success":True,
                "log": log_summary if log_summary else "No commits found",
                "execution_time_ms":(time.time() - start_time) * 1000
            }
        
        except Exception as e:
            logger.error(f"Error in get_git_log: {str(e)}")

            return {
                "success":False,
                "error":str(e),
                "execution_time_ms":(time.time() - start_time) * 1000

            }
        
    async def list_directory(
            self, directory_path:str , recursive:bool = False , filter_pattern:Optional[str] = None
    )-> Dict[str, Any]:
        start_time = time.time()
        
        try:
            client = MongoClient(os.getenv("mongo_client"))
            raw_files_collection = client["codebase"]["raw_repo_files"]


            cursor = raw_files_collection.find({"session_id":str(self.session_id)} , {"file_path":1 , "_id":0})
            
            all_files = [doc.get("file_path" , "") for doc in cursor if doc.get("file_path")]

            items = []

            dir_path_clean = directory_path.rstrip("./\\")

            for file_path in all_files:

                if dir_path_clean and not file_path.startswith(dir_path_clean):
                    continue
                
                
                if not recursive:
                    if dir_path_clean:
                        remainder = file_path[len(dir_path_clean):].lstrip('/')

                        if '/' in remainder:
                            continue

                    else:
                        if '/' in file_path:
                            continue
                

                if filter_pattern:
                    file_name = os.path.basename(file_path)

                    if filter_pattern not in file_name:continue

                items.append(file_path)

                
            if len(items) > 300:
                items = items[:300]
                warning = "Truncated results to 300 items to protect LLM context window."
            
            else:
                warning = None

            return {
                "success":True,
                "items":items,
                "count": len(items),
                "warning":warning,
                "execution_time_ms": (time.time() - start_time) * 1000

            }
        
        except Exception as e:
            logger.error(f"Error in list_directory: {str(e)}")

            return {
                "success": False,
                "error":str(e),
                "execution_time_ms":(time.time() - start_time) * 1000
            }
        

    async def analyze_class(self, class_name: str, file_path: Optional[str] = None, include_methods: bool = True, include_usage: bool = False)-> Dict[str, Any]:
        start_time = time.time()

        try:
            import ast
            target_file_path = None
            target_file = None
            found_line_num = -1

            client = MongoClient(os.getenv("mongo_client"))
            raw_files_collection = client["codebase"]["raw_repo_files"]

            if file_path:
                doc = raw_files_collection.find({"session_id":str(self.session_id)}) 

                if doc:
                    target_file_path = file_path
                    target_content = doc.get("content")


            if not target_content:
                cursor = raw_files_collection.find({"session_id":str(self.session_id)}) 

                pattern = re.compile(rf"\b(?:class|struct|interface)\s+{re.escape(class_name)}\b", re.IGNORECASE)

                for doc in cursor:
                    content = doc.get("content","")
                    current_path = doc.get("file_path","")

                    lines = content.splitlines()

                    for i , line in enumerate(lines):
                        if pattern.search(line):
                            target_file_path = current_path
                            target_content = content
                            found_line_num = i + 1
                            break

                    if target_content:
                        break

            if not target_content:
                return {"success":False , "error":f"Class '{class_name}' not found in any indexed code file"}

            analysis = {
                "name":class_name,
                "file":target_file_path
            }

            _ , ext = os.path.splitext(target_file_path)


            if ext.lower() == '.py':
                try:
                    tree = ast.parse(target_content)

                    class_def = next((node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and node.name == class_name), None)

                    if class_def:
                        analysis["line_number"] = class_def.lineno
                        analysis["bases"] = [ast.unparse(base) for base in class_def.bases]
                        analysis['docstring'] = ast.get_docstring(class_def)

                        if include_methods:
                            methods = []
                            for node in class_def.body:
                                if isinstance(node , ast.FunctionDef):
                                    methods.append({
                                        "name":node.name,
                                        "args":[arg.arg for arg in node.args.args],
                                        "docstring": ast.get_docstring(node)
                                    })

                            analysis["methods"] = methods

                    else:
                        analysis["warning"] = "AST Could not locate class Structure"
                        analysis['line_number'] = found_line_num

                except SyntaxError:
                    analysis["warning"] = "Syntax error in python file, Could not parse AST"
                    analysis['line_number'] = found_line_num

            else:
                analysis['line_number'] = found_line_num
                analysis['warning'] = f"Deep AST parsing is only supported for Python. Showing basic text match for {ext} file."

                try:
                    lines = target_content.splitlines(keepends=True)
                    start = max(0 , found_line_num-1)

                    analysis["code_preview"] = "".join(lines[start:start + 100])

                except Exception:
                    pass

            return {
                "success": True,
                "analysis": analysis,
                "execution_time_ms": (time.time() - start_time) * 1000
            }
        
        except Exception as e:
            return {"success": False, "error": f"Error analyzing class: {str(e)}"}



        
    async def get_dependencies(self, file_path: str, depth: int = 1) -> Dict[str, Any]:
        start_time = time.time()
        try:
            import ast
            import os
            import re
            from pymongo import MongoClient

            # 1. Connect straight to the raw files
            client = MongoClient(os.getenv("mongo_client"))
            raw_files_collection = client["codebase"]["raw_repo_files"]
            
            # 2. Use our fuzzy path regex to find the exact file
            clean_path = file_path.lstrip('/')
            pattern = re.compile(rf"{re.escape(clean_path)}$", re.IGNORECASE)
            
            doc = raw_files_collection.find_one({
                "session_id": str(self.session_id), 
                "file_path": pattern
            })
            
            if not doc or not doc.get("content"):
                return {
                    "success": False, 
                    "error": f"File '{file_path}' not found. HINT: Use list_directory to check the exact path."
                }

            # 3. Deterministic AST Parsing
            content = doc.get("content", "")
            try:
                tree = ast.parse(content)
            except SyntaxError:
                return {"success": False, "error": "AST parsing failed. Ensure the file is valid Python code."}

            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            return {
                "success": True,
                "source": "ast_parsing",
                "exact_file_found": doc.get("file_path"),
                "imports": imports,
                "execution_time_ms": (time.time() - start_time) * 1000
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
        
        
    async def get_git_blame(self, file_path:str , start_line:int , end_line:int) -> Dict[str, Any]:
        start_time = time.time()

        try:
            doc = self.collection.find_one({"session_id": str(self.session_id)})

            if not doc or "metadata" not in doc or "repo_url" not in doc["metadata"]:
                return {"success": False, "error": "Could not find a valid GitHub repo_url for this session in the database."}
        
            
            repo_url = doc["metadata"]["repo_url"]

            with tempfile.TemporaryDirectory() as temp_dir:
                clone_cmd = ["git", "clone", "--filter=blob:none", repo_url, temp_dir]

                clone_result = subprocess.run(clone_cmd, capture_output=True, text=True)

                if clone_result.returncode != 0:
                    return {"success": False, "error": f"Failed to clone temporary repo: {clone_result.stderr.strip()}"}

                blame_cmd = [
                    "git", "-C", temp_dir, "blame",
                    f"-L{start_line},{end_line}", file_path
                ]

                result = subprocess.run(blame_cmd, capture_output=True, text=True, timeout=15, encoding='utf-8', errors='ignore')

                if result.returncode != 0:
                    # Check if it failed because the file path is slightly different in the repo
                    return {
                        "success": False,
                        "error": f"Git blame failed. Ensure the file '{file_path}' exists in the repository. Error: {result.stderr.strip()}"
                    }

                return {
                    "success": True,
                    "blame_data": result.stdout,
                    "execution_time_ms": (time.time() - start_time) * 1000
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Git blame timeout after 15 seconds."
            }
        except Exception as e:
            return {
                "success":False,
                "error":str
            }






            if not full_path.exists():
                return {"success":False,"error":f"File '{file_path}' does not exists."}
            

            cmd = [
                "git" , "-C" , str(self.repo_path) , "blame",
                f"-L{start_line},{end_line}" , file_path
            ]

            result = subprocess.run(cmd , capture_output= True, text = True , timeout = 10,encoding='utf-8',errors='ignore')


            if result.returncode != 0:
                return {
                    "success":False,
                    "errors":f"Git blame failed: {result.stderr.strip()}"
                }

            return {
                "success": True,
                "blame_data": result.stdout,
                "execution_time_ms":(time.time() - start_time) * 1000
            }
        
        except FileNotFoundError:
            return {
                "success":False,
                "error":"Git executable not found. Ensure Git is installed and in your system PATH"
            }
        

        except subprocess.TimeoutExpired:
            return {
                "success":False,
                "error":"Git blame timeout after 10 seconds"
            }
        except Exception as e:
            return {
                "success":False,
                "error": str(e)
            }

        
        

    




                





        






            
            





