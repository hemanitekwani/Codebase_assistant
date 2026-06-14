import os 
import subprocess
import json
from typing import Dict, Any, List, Tuple, Optional,Callable
import asyncio
from datetime import datetime
import time
import logging
from pathlib import Path
import ast
import fnmatch
from pymongo import MongoClient
import re
import httpx
import tempfile
from functools import lru_cache
from typing import Union


from retrieval.vector_retrieval import vector_retrieval
from retrieval.direct_retrieval import FileMatch

from dotenv import load_dotenv
from langchain_core.tools import BaseTool , tool

load_dotenv()


logger = logging.getLogger(__name__)

client = MongoClient(os.getenv("mongo_client"))
repo_cache = {}

def get_agent_tools(session_id: str, user_id:str, collection=None) -> list:
    raw_files_collection = client["codebase"]["raw_repo_files"]
    v_retriever = vector_retrieval(collection) if collection is not None else None

    def _format_docs(docs):
        if not docs:
            return "No result."
        return "\n\n".join([
            f"File: {Path(d['metadata'].get('source','unknown')).name}\n{d['page_content']}"
            for d in docs
        ])
    
    @lru_cache(maxsize=100)
    def _cached_semantic_search(query:str , session_id:str , top_k):
        if not v_retriever:
            return ()
        return tuple(v_retriever.retrieve(query=query, session_id=session_id, user_id=user_id, top_k=top_k))


    async def _semantic_search(query: str, language: Optional[str], top_k: int = 5):
        if not v_retriever: return []

        docs = _cached_semantic_search(query , session_id , top_k)

        return _format_docs(docs)

    async def _keyword_search(query: str, language: Optional[str], top_k: int) -> List[Dict[str,Any]]:
        try:
            matches = []
            lang_map = {
                "python": ['.py'], "javascript": ['.js','.jsx'], "typescript": ['.ts','.tsx'],
                "java": ['.java'], "cpp": ['.cpp','.hpp','.cc','.cxx','.h'], "go": [".go"],
                "rust": [".rs"], "html": [".html", ".htm"], "css": [".css"],
                "json": [".json"], "yaml": [".yaml", ".yml"], "markdown": [".md"]
            }
            allowed_ext = None
            if language:
                allowed_ext = lang_map.get(language.lower())
                if not allowed_ext:
                    allowed_ext = [f".{language.lstrip('.').lower()}"]

            query_lower = query.lower()
            cursor = raw_files_collection.find({"session_id": session_id})
            
            for doc in cursor:
                file_path = doc.get("file_path", "")
                content = doc.get("content", "")

                if allowed_ext:
                    _, ext = os.path.splitext(file_path)
                    if ext.lower() not in allowed_ext: continue

                lines = content.splitlines()
                for line_idx, line in enumerate(lines):
                    if query_lower in line.lower():
                        matches.append({
                            "file": file_path,
                            "line_number": line_idx + 1,
                            "content": line.rstrip('\r\n'),
                            "match_type": "keyword"
                        })
                        if len(matches) >= top_k:
                            return matches
            return matches[:top_k]
        except Exception as e:
            logger.error(f"Error in keyword search: {str(e)}")
            return []

   

    @tool
    async def search_code(query: str, language: Optional[str] = None, top_k: Union[int,str] = 5, search_type: str = 'semantic') -> Any:
        """Search for code snippets using semantic/keyword search.""" 
        try:
            if search_type == 'semantic' and collection is not None:
                return await _semantic_search(query, language, top_k)
            elif search_type == 'keyword':
                result =  await _keyword_search(query, language, top_k)
                return json.dumps(result, indent=2)
            
        except Exception as e:
            return f"Error searching code: {str(e)}"

    @tool
    async def find_file(pattern: str, file_type: Optional[str] = None, max_results: int = 20) -> str:
        """Find files in the codebase by name pattern or path."""
        try:
            matched_file = []
            ext = f".{file_type.lstrip('.')}" if file_type else None
            has_wildcard = any(char in pattern for char in ['*','?','['])
            cursor = raw_files_collection.find({"session_id": str(session_id)}, {"file_path": 1, "_id": 0})

            for doc in cursor:
                file_path = doc.get('file_path', "")
                if not file_path: continue
                file_name = os.path.basename(file_path)

                if ext:
                    _, current_ext = os.path.splitext(file_name)
                    if current_ext.lower() != ext: continue

                if has_wildcard:
                    if fnmatch.fnmatch(file_name.lower(), pattern.lower()): matched_file.append(file_path)
                else:
                    if pattern.lower() in file_name.lower(): matched_file.append(file_path)

                if len(matched_file) >= max_results: break

            if not matched_file:
                return f"No files found matching '{pattern}'"
            
            return "Found files:\n" + "\n".join(matched_file)
        except Exception as e:
            return [f"Error finding file: {str(e)}"]

    @tool
    async def get_file_content(file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
        """Get the full content of a specific file with line numbers for reading source code."""
        try:
            document = raw_files_collection.find_one({"session_id": str(session_id), "file_path": file_path})
            if not document:
                filename = os.path.basename(file_path)
                pattern = re.compile(rf"{re.escape(filename)}$" , re.IGNORECASE)
                document = raw_files_collection.find_one({"session_id":str(session_id), "file_path":pattern})
            
            full_text = document["content"]
            lines = full_text.splitlines(keepends=True)
            
            if start_line and end_line:
                start_idx = max(0, start_line - 1)
                lines = lines[start_idx:end_line]

            return ''.join(lines)
        except Exception as e:
            return f"Error reading file: {str(e)}"

    @tool
    async def analyze_function(function_name: str, file_path: Optional[str] = None, include_calls: bool = False, include_dependencies: bool = True) -> str:
        """Get a deep dive into a specific function (signature, return types, and dependencies)."""
        try:
            target_file_path = None
            target_content = None
            found_line_no = -1

            if file_path:
                doc = raw_files_collection.find_one({"session_id": str(session_id), "file_path": file_path})
                if doc:
                    target_file_path = file_path
                    target_content = doc.get("content", "")

            if not target_content:
                cursor = raw_files_collection.find({"session_id": str(session_id)})
                pattern = re.compile(rf"\b(?:def|function|func|fn|fun)\s+{re.escape(function_name)}\b|\b{re.escape(function_name)}\s*\(", re.IGNORECASE)
                for doc in cursor:
                    content = doc.get("content", "")
                    current_path = doc.get("file_path", "")
                    lines = content.splitlines()
                    for i, line in enumerate(lines):
                        if pattern.search(line):
                            target_file_path = current_path
                            target_content = content
                            found_line_no = i + 1
                            break
                    if target_content: break

            if not target_content:
                return f"Error: Function '{function_name}' not found in any supported code files."
            
            analysis = {"name": function_name, "file": str(target_file_path)}
            _, ext = os.path.splitext(target_file_path)

            if ext.lower() == '.py':
                try:                   
                    tree = ast.parse(target_content)
                    func_def = next((node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name), None)
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
                analysis["warning"] = f"Deep AST parsing is only supported for Python. Showing basic text match for {ext} file."
                try:
                    lines = target_content.splitlines(keepends=True)
                    start = max(0, found_line_no - 1)
                    analysis['code_preview'] = "".join(lines[start:start + 100])
                except Exception:
                    pass
            return analysis
        except Exception as e:
            return f"Error analyzing function: {str(e)}"

    @tool
    async def get_git_log(limit: int = 10, file_path: Optional[str] = None, format: str = "summary") -> str:
        """Retrieve the commit history to see how a file or the repo has changed over time."""
        try:
            if collection is None: return "Error: Database collection not initialized."
            doc = collection.find_one({"session_id": str(session_id)})
            if not doc or "metadata" not in doc or "repo_url" not in doc["metadata"]:
                return "Error: Could not find a valid GitHub repo_url for this session."
            
            repo_url = doc["metadata"]["repo_url"]
            clean_url = repo_url.rstrip(".git").rstrip("/")
            parts = clean_url.split("github.com/")[-1].split("/")
            if len(parts) < 2: return f"Error: Invalid GitHub URL format: {repo_url}"
            owner, repo = parts[0], parts[1]

            api_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
            params = {"per_page": limit}
            if file_path: params["path"] = file_path
            headers = {"Accept": "application/vnd.github.v3+json"}

            async with httpx.AsyncClient() as httpx_client:
                response = await httpx_client.get(api_url, params=params, headers=headers,timeout=10)

            if response.status_code == 403: return "Error: GitHub API rate limit exceeded."
            elif response.status_code != 200: return f"Error: GitHub API error ({response.status_code})"
            
            commits = response.json()
            log_summary = ""
            for c in commits:
                sha, author = c["sha"][:7], c["commit"]["author"]["name"]
                message, date = c["commit"]["message"].split('\n')[0], c["commit"]["author"]["date"]
                log_summary += f"[{sha}] {date} - {author} : {message}\n"
            return log_summary if log_summary else "No commits found"
        except Exception as e:
            return f"Error fetching git log: {str(e)}"

    @tool
    async def list_directory(directory_path: str, recursive: bool = False, filter_pattern: Optional[str] = None) -> str:
        """List all files and subdirectories in a specific folder to understand project structure."""
        try:
            cursor = raw_files_collection.find({"session_id": str(session_id)}, {"file_path": 1, "_id": 0})
            all_files = [doc.get("file_path", "") for doc in cursor if doc.get("file_path")]
            items = []
            dir_path_clean = directory_path.rstrip("./\\")

            for file_path in all_files:
                if dir_path_clean and not file_path.startswith(dir_path_clean): continue
                if not recursive:
                    if dir_path_clean:
                        if '/' in file_path[len(dir_path_clean):].lstrip('/'): continue
                    else:
                        if '/' in file_path: continue
                if filter_pattern and filter_pattern not in os.path.basename(file_path): continue
                items.append(file_path)

            warning = "Truncated results to 300 items" if len(items) > 300 else None
            result = {"items": items[:300], "count": min(len(items), 300), "warning": warning}
            return json.dumps(result, indent=2)
        

        except Exception as e:
            return f"error: {str(e)}"

    @tool
    async def analyze_class(class_name: str, file_path: Optional[str] = None, include_methods: bool = True, include_usage: bool = False) ->str:
        """Analyze a class structure, including inheritance, methods, and attributes."""
        try:
            target_file_path = None
            target_content = None
            found_line_num = -1

            if file_path:
                doc = raw_files_collection.find_one({"session_id": str(session_id), "file_path": file_path}) 
                if doc:
                    target_file_path = file_path
                    target_content = doc.get("content")

            if not target_content:
                cursor = raw_files_collection.find({"session_id": str(session_id)}) 
                pattern = re.compile(rf"\b(?:class|struct|interface)\s+{re.escape(class_name)}\b", re.IGNORECASE)
                for doc in cursor:
                    content = doc.get("content", "")
                    current_path = doc.get("file_path", "")
                    lines = content.splitlines()
                    for i, line in enumerate(lines):
                        if pattern.search(line):
                            target_file_path = current_path
                            target_content = content
                            found_line_num = i + 1
                            break
                    if target_content: break

            if not target_content:
                return f"Error: Class '{class_name}' not found."
            
            analysis = {"name": class_name, "file": target_file_path}
            _, ext = os.path.splitext(target_file_path)

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
                                if isinstance(node, ast.FunctionDef):
                                    methods.append({
                                        "name": node.name,
                                        "args": [arg.arg for arg in node.args.args],
                                        "docstring": ast.get_docstring(node)
                                    })
                            analysis["methods"] = methods
                    else:
                        analysis["warning"] = "AST Could not locate class Structure"
                        analysis['line_number'] = found_line_num
                except SyntaxError:
                    analysis["warning"] = "Syntax error in python file"
                    analysis['line_number'] = found_line_num
            else:
                analysis['line_number'] = found_line_num
                analysis['warning'] = f"Only Python supported for deep AST. Showing match for {ext}."
                try:
                    lines = target_content.splitlines(keepends=True)
                    start = max(0, found_line_num - 1)
                    analysis["code_preview"] = "".join(lines[start:start + 100])
                except Exception:
                    pass

            return json.dumps(analysis, indent=2)
        
        except Exception as e:
            return f"Error analyzing class: {str(e)}"
    @tool
    async def get_dependencies(file_path: str, depth: int = 1) -> str:
        """List all imports and module dependencies for a file or specific function."""
        try:
            filename = os.path.basename(file_path)
            pattern = re.compile(rf"{re.escape(filename)}$", re.IGNORECASE)
            doc = raw_files_collection.find_one({"session_id": str(session_id), "file_path": pattern})
            
            if not doc or not doc.get("content"):
                return f"Error: File '{file_path}' not found."

            content = doc.get("content", "")
            try:
                tree = ast.parse(content)
            except SyntaxError:
                return "Error: AST parsing failed. Ensure file is valid Python code."

            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names: imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module: imports.append(node.module)

            result =  {"source": "ast_parsing", "exact_file_found": doc.get("file_path"), "imports": imports}
            return json.dumps(result, indent=2)
        

        except Exception as e:
            return f"Error: {str(e)}"


    @tool
    async def get_git_blame(file_path: str, start_line: int, end_line: int) -> str:
        """See who modified specific lines of code and when."""
        try:
            if collection is None: return "Error: Database collection not initialized."
            doc = collection.find_one({"session_id": str(session_id)})
            if not doc or "metadata" not in doc or "repo_url" not in doc["metadata"]:
                return "Error: Could not find a valid GitHub repo_url."
            
            repo_url = doc["metadata"]["repo_url"]

            if repo_url not in repo_cache:
                temp_dir =  tempfile.mkdtemp()

                clone_cmd = ["git", "clone", "--filter=blob:none", repo_url, temp_dir]


                clone_result = subprocess.run(clone_cmd, capture_output=True, text=True)
                
                if clone_result.returncode != 0:
                    return f"Error: Failed to clone repo: {clone_result.stderr.strip()}"
                

                repo_cache[repo_url] = temp_dir

            repo_dir = repo_cache[repo_url]

            blame_cmd = ["git", "-C", repo_dir, "blame", f"-L{start_line},{end_line}", file_path]

            result = subprocess.run(blame_cmd, capture_output=True, text=True, timeout=30, encoding='utf-8', errors='ignore')

            if result.returncode != 0:
                return f"Error: Git blame failed. Ensure '{file_path}' exists. {result.stderr.strip()}"
                

            return result.stdout
        
        except subprocess.TimeoutExpired:
            return "Error: Git blame timeout after 15 seconds."
        
        except Exception as e:
            return f"Error: {str(e)}"


    return [
        search_code, 
        find_file, 
        get_file_content, 
        analyze_function, 
        get_git_log, 
        list_directory, 
        analyze_class, 
        get_dependencies, 
        get_git_blame
    ]