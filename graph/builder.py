import ast
import rustworkx as rx
from pathlib import Path
from typing import Optional
import re



def parse_python_file(file_path:str):
    try:
        with open(file_path , "r" , encoding = "utf-8" , errors = "ignore") as f:
            source = f.read()

        tree = ast.parse(source)

        imports = []
        functions = []
        classes = []
        calls = []

        for node in ast.walk(tree):
            if isinstance(node , ast.Import):
                for alias in node.names:
                    imports.append(alias.name.split(".")[0])

            
            elif isinstance(node , ast.ImportFrom):
                if node.module:
                    imports.append(node.module.split(".")[0])


            elif isinstance(node , ast.FunctionDef):
                functions.append(node.name)

            elif isinstance(node , ast.AsyncFunctionDef):
                functions.append(node.name)
            

            elif isinstance(node , ast.ClassDef):
                classes.append(node.name)


            elif isinstance(node , ast.Call):
                if isinstance(node.func , ast.Name):
                    calls.append(node.func.id)


                elif isinstance(node.func , ast.Attribute):
                    calls.append(node.func.attr)


        return {
            "file": Path(file_path).name,
            "path":str(file_path),
            "imports": list(set(imports)),
            "functions":list(set(functions)),
            "classes": list(set(classes)),
            "calls" : list(set(calls)),
            "language": "python"
        }
    
    except Exception as e:
        print(f"Could not parse {file_path}: as {e}")
        return None
    

def parse_java_file(file_path: str) -> Optional[dict]:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()

        imports = []
        functions = []
        classes = []
        calls = []

        # import com.example.X
        for match in re.finditer(r"import\s+([\w.]+);", source):
            parts = match.group(1).split(".")
            imports.append(parts[-1])   # just class name

        # class X
        for match in re.finditer(r"class\s+(\w+)", source):
            classes.append(match.group(1))

        # public/private void/String X()
        for match in re.finditer(
            r"(?:public|private|protected|static)\s+\w+\s+(\w+)\s*\(", source
        ):
            functions.append(match.group(1))

        # method calls: X(
        for match in re.finditer(r"(\w+)\s*\(", source):
            calls.append(match.group(1))

        return {
            "imports": list(set(imports)),
            "functions": list(set(functions)),
            "classes": list(set(classes)),
            "calls": list(set(calls)),
            "language": "java"
        }
    except Exception as e:
        print(f"⚠️ Java parse failed {file_path}: {e}")
        return None


def parse_go_file(file_path: str) -> Optional[dict]:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()

        imports = []
        functions = []
        classes = []
        calls = []

        # import "X" or import ( "X" )
        for match in re.finditer(r'"([\w./]+)"', source):
            imp = match.group(1)
            imports.append(imp.split("/")[-1])   # last part only

        # func X(
        for match in re.finditer(r"func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(", source):
            functions.append(match.group(1))

        # type X struct
        for match in re.finditer(r"type\s+(\w+)\s+struct", source):
            classes.append(match.group(1))

        # X( calls
        for match in re.finditer(r"(\w+)\s*\(", source):
            calls.append(match.group(1))

        return {
            "imports": list(set(imports)),
            "functions": list(set(functions)),
            "classes": list(set(classes)),
            "calls": list(set(calls)),
            "language": "go"
        }
    except Exception as e:
        print(f"⚠️ Go parse failed {file_path}: {e}")
        return None
    

PARSERS = {
    ".py": parse_python_file,
    ".java": parse_java_file,
    ".go": parse_go_file
}

def parse_file(file_path: str):
    suffix = Path(file_path).suffix.lower()
    parser = PARSERS.get(suffix)

    if not parser:
        return None
    
    result = parser(file_path)

    if result:
        result["file"] = Path(file_path).name
        result["path"] = str(file_path)

    return result


class GraphBuilder:
    def __init__(self):
        self.graph = rx.PyDiGraph()
        self.file_to_index = {}


    def build(self, repo_path):
        repo_path = Path(repo_path)


        all_files = []

        for suffix in PARSERS.keys():
            all_files.extend(repo_path.rglob(f"*{suffix}"))


        file_data = {}

        for file_path in all_files:
            parsed = parse_file(str(file_path))

            if not parsed:
                continue

            file_name = parsed["file"]

            idx = self.graph.add_node({
                "file": file_name,
                "path": parsed["path"],
                "functions": parsed["functions"],
                "classes": parsed["classes"],
                "calls": parsed["calls"],
                "language": parsed["language"]
            })

            self.file_to_index[file_name] = idx
            self.file_to_index[Path(file_name).stem.lower()] = idx
            
            file_data[file_name] = parsed

            print(f" {file_name} [{parsed['language']}]"
                  f" | funcs: {len(parsed['functions'])}"
                  f" | imports: {len(parsed['imports'])}")
            
    
        
        for filename , parsed in file_data.items():
            source_idx = self.file_to_index.get(filename)

            if source_idx is None:
                continue

            for imp in parsed["imports"]:
                target_idx = (

                    self.file_to_index.get(f"{imp}.py") or
                    self.file_to_index.get(f"{imp}.java") or
                    self.file_to_index.get(f"{imp}.go") or
                    self.file_to_index.get(imp.lower())

                )

                if target_idx is not None and target_idx != source_idx:
                    self.graph.add_edge(source_idx , target_idx, {
                        "type": "imports",
                        "from": filename,
                        "to": self.graph[target_idx]["file"]
                    })

                    print(f"  {filename} ──► {self.graph[target_idx]['file']}")
                
                else:
                    print('print(f"  Warning: Target for {filename} not found in graph.")')
                
              
        return self.graph
    
    def get_index(self, filename:str):
        return (
            self.file_to_index(filename) or self.file_to_index(Path(filename).stem.lower())
        )
