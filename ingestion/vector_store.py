from os import path
import uuid

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
from ingestion.embedder import Embedder
import os
from pathlib import Path

load_dotenv()

uri = os.getenv("mongo_client")

class VectorStore:
    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None
        self.embedder = Embedder()



    def connect(self):
        try:
            self.client = MongoClient(uri , server_api = ServerApi('1'), tlsAllowInvalidCertificates = True)
            self.db = self.client['codebase']
            self.collection = self.db['codechunk']
            self.sessions = self.db['sessions']
            self.chat_history = self.db['chat_history']
            self.code_graph = self.db["graph_code"]
            
            
        
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")


    def insert_embeddings(self,docs , repo_url,session_id):
        for doc in docs:
            try:
                raw_text = doc.page_content if isinstance(doc.page_content, str) else "\n".join(doc.page_content)

                source = doc.metadata.get("source" , "")
                filename = Path(source).name
                language = doc.metadata.get("language" , "")
                content_type = doc.metadata.get("content_type" ,"")

                enriched_text = f"File: {filename} | Language: {language} | Type: {content_type} \n\n{raw_text}"

                metadata = {
                    k: v if isinstance(v, str) else str(v)
                    for k , v in doc.metadata.items()
                }
                embedding = self.embedder.get_embeddings(enriched_text).tolist()

                self.collection.insert_one({
                    "ids" : str(uuid.uuid4()),
                    "session_id":str(session_id),
                    "page_content": enriched_text,
                    "embedding" : embedding,
                    "metadata" : {
                        "repo_url": repo_url,
                        "source": source,
                        "content_type": "code",
                        "language": language,
                        "session_id": str(session_id)
                    },
                   
                })
            
            except Exception as e:
                print(f"Error inserting document: {e}")


       