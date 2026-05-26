from typing import Dict,Any,List
import json


# CODE SEARCH TOOLS
 

SEARCH_CODE_DEFINITION = {
    "type": "function", 
    "function": {
        "name": "search_code",
        "description": "Search for code snippets using semantic/keyword search across the codebase",
        "parameters": { 
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (function name, class name, or description)"
                },
                "language": {
                    "type": "string",
                    "enum": ["python", "javascript", "typescript", "java", "go", "rust", "cpp"],
                    "description": "Programming language filter (optional)"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return",
                },
                "search_type": {
                    "type": "string",
                    "enum": ["semantic", "keyword"],
                    "description": "Type of search to perform",
                }
            },
            "required": ["query"]
        }
    }
}    
    
# FIND FILES

FIND_FILE_DEFINITION = {
    "type": "function",
    "function": {
        "name": "find_file",
        "description": "Find files in the codebase by name pattern or path",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "File name pattern (supports wildcards like 'auth_*' or 'utils.py')"
                },
                "file_type": {
                    "type": "string",
                    "description": "Specific file extension to filter by (e.g., .py, .js, .cpp)"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of matches to return",
                }
            },
            "required": ["pattern"]
        }
    }
}

GET_FILE_CONTENT_DEFINITION = {
    "type": "function",
    "function": {
        "name": "get_file_content",
        "description": "Get the full content of a specific file with line numbers for reading source code.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Full path to the file you want to read"
                },
                "start_line": {
                    "type": "integer",
                    "description": "Optional: Start line number (1-indexed)"
                },
                "end_line": {
                    "type": "integer",
                    "description": "Optional: End line number (1-indexed)"
                }
            },
            "required": ["file_path"]
        }
    }
}

LIST_DIRECTORY_DEFINITION = {
    "type": "function",
    "function": {
        "name": "list_directory",
        "description": "List all files and subdirectories in a specific folder to understand project structure.",
        "parameters": {
            "type": "object",
            "properties": {
                "directory_path": {
                    "type": "string",
                    "description": "Path to the directory"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Set to true to see all nested subfolders",
                },
                "filter_pattern": {
                    "type": "string",
                    "description": "Optional: Filter results (e.g., '*.py')"
                }
            },
            "required": ["directory_path"]
        }
    }
}


ANALYZE_FUNCTION_DEFINITION = {
    "type": "function",
    "function": {
        "name": "analyze_function",
        "description": "Get a deep dive into a specific function (signature, return types, and dependencies).",
        "parameters": {
            "type": "object",
            "properties": {
                "function_name": {
                    "type": "string",
                    "description": "The exact name of the function to analyze"
                },
                "file_path": {
                    "type": "string",
                    "description": "Optional: Path to the file containing the function"
                },
                "include_calls": {
                    "type": "boolean",
                    "description": "Include where this function is called from"
                },
                "include_dependencies": {
                    "type": "boolean",
                    "description": "Include other functions that this function calls"
                }
            },
            "required": ["function_name"]
        }
    }
}

ANALYZE_CLASS_DEFINITION = {
    "type": "function",
    "function": {
        "name": "analyze_class",
        "description": "Analyze a class structure, including inheritance, methods, and attributes.",
        "parameters": {
            "type": "object",
            "properties": {
                "class_name": {
                    "type": "string",
                    "description": "The exact name of the class"
                },
                "file_path": {
                    "type": "string",
                    "description": "Optional: Path to the file containing the class"
                },
                "include_methods": {
                    "type": "boolean",
                    "description": "List all methods and attributes of the class"                 
                },
                "include_usage": {
                    "type": "boolean",
                    "description": "Show where this class is instantiated in the codebase",
                }
            },
            "required": ["class_name"]
        }
    }
}

GET_DEPENDENCIES_DEFINITION = {
    "type": "function",
    "function": {
        "name": "get_dependencies",
        "description": "List all imports and module dependencies for a file or specific function.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to check"
                },
                "depth": {
                    "type": "integer",
                    "description": "How many levels of the dependency tree to traverse"
                }
            },
            "required": ["file_path"]
        }
    }
}

GET_GIT_LOG_DEFINITION = {
    "type": "function",
    "function": {
        "name": "get_git_log",
        "description": "Retrieve the commit history to see how a file or the repo has changed over time.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Optional: Specific file path to check history for"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of recent commits to return",
                },
                "format": {
                    "type": "string",
                    "enum": ["summary", "detailed"],
                }           
            },
            "required":[]
        }
    }
}

GET_GIT_BLAME_DEFINITION = {
    "type": "function",
    "function": {
        "name": "get_git_blame",
        "description": "See who modified specific lines of code and when.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file"
                },
                "start_line": {
                    "type": "integer",
                    "description": "Start line number"
                },
                "end_line": {
                    "type": "integer",
                    "description": "End line number"
                }
            },
            "required": ["file_path", "start_line", "end_line"]
        }
    }
}

EXECUTE_FUNCTION_DEFINITION = {
    "type": "function",
    "function": {
        "name": "execute_function",
        "description": "Execute a specific Python function with given arguments in a sandboxed environment. Use this only for testing or verifying logic.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the Python file containing the function"
                },
                "function_name": {
                    "type": "string",
                    "description": "The exact name of the function to run"
                },
                "args": {
                    "type": "array",
                    "description": "Optional list of positional arguments to pass to the function",
                    
                },
                "kwargs": {
                    "type": "object",
                    "description": "Optional dictionary of keyword arguments to pass to the function",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Maximum time allowed for execution before killing the process",
                }
            },
            "required": ["file_path", "function_name"]
        }
    }
}

TOOL_REGISTRY= {
    "search_code": SEARCH_CODE_DEFINITION,
    "find_file": FIND_FILE_DEFINITION,
    "get_file_content": GET_FILE_CONTENT_DEFINITION,
    "analyze_function": ANALYZE_FUNCTION_DEFINITION,
    "analyze_class": ANALYZE_CLASS_DEFINITION,
    "get_dependencies": GET_DEPENDENCIES_DEFINITION,
    "list_directory": LIST_DIRECTORY_DEFINITION,
    "get_git_log": GET_GIT_LOG_DEFINITION,
    "get_git_blame": GET_GIT_BLAME_DEFINITION,
    # "execute_function": EXECUTE_FUNCTION_DEFINITION
}


def get_tool_definitions()-> Dict[str, Any]:
    return list(TOOL_REGISTRY.values())



def get_tools_definition(tool_name:str)->List[Dict[str , Any]]:
    return TOOL_REGISTRY.get(tool_name)



def validate_tool_list(tool_name: str, input_dict: Dict[str, Any]) -> tuple[bool, str]:
    tool_def = get_tools_definition(tool_name)

    if not tool_def:
        return False , f"Tool {tool_name} not found"
    
    
    parameters = tool_def.get("function",{}).get("parameters", {})
    required_fields = parameters.get("required", [])


    for field in required_fields:
        if field not in input_dict:
            return False , f"Missing required field: {field}"
        

    return True,"Valid"
        









