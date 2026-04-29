from langchain_core.prompts import ChatPromptTemplate
from pathlib import Path
import json

GRAPH_TRIGGERS = [
    "import", "imports", "imported",
    "imported by", "depend", "depends",
    "dependency", "dependencies",
    "calls", "called by",
    "circular", "cycle",
    "what breaks", "impact",
    "path from", "uses",
    "which files use", "who uses",
]

class IntentRouter:

    def __init__(self , llm , collection):
        self.llm = llm
        self.collection = collection

    def route(self , query , repo_url):
        all_sources = self.collection.distinct("metadata.source" , {"metadata.repo_url": repo_url})

        all_filenames = [Path(s).name for s in all_sources]

        files_list = ",".join(all_filenames)
        
        if any(trigger in query.lower() for trigger in GRAPH_TRIGGERS):
            print('Rule Based -> Graph intent')
            return {"intent": "graph_intent" , "target_file": None}
        

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a query router for a codebase assistant.
             Classify the query into one of these intents:

            graph_intent: asks about file relationships, imports, dependencies,
            what calls what, circular dependencies, impact of changes
            Examples:
            "what does main.py import"
            "which files use database.py"
            "what are the dependencies of auth.py"
            "what files are imported in main.py"
            "what would break if I change tools.py"

            - file_intent: asks to see/read a specific file 
            Examples:
            "show me main.py"
            "what is in auth.py"
            "display database.py"

            - semantic_intent: asks about functionality or behavior
            Examples:
            "how does authentication work"
            "how is the database connection established"
            "what does the booking system do"
             
            Available files: {files_list}
             
            Rules:
            - ONLY classify as file_intent if user explicitly names a file with .py/.js extension
            - "database connection" is semantic_intent NOT file_intent
            - "what does database.py do" IS file_intent
            - When in doubt → semantic_intent
             

            Return JSON only:
            {{"intent": "file_intent|semantic_intent|graph_intent", "target_file": "filename or null"}}"""),
            ("human", "{query}")
            ])

        result = (prompt | self.llm).invoke({
            "query" : query,
            "files_list" : files_list
        })


        try:
            parsed = json.loads(result.content)

            print(f"Intent: {parsed['intent']} | Target: {parsed.get('target_file')}")

            return parsed
        
        except:
            return {"intent": "semantic_intent" , "target_file": None}

             


    
