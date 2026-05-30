import os
import subprocess
import tempfile
import shutil
import uuid
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime



load_dotenv()

mongo_uri = os.getenv("mongo_client")

client = MongoClient(mongo_uri)

db = client["codebase"]

raw_files_collection = db["raw_repo_files"]

raw_files_collection.create_index([("session_id", 1)])

raw_files_collection.create_index([("user_id",1) , ("repo_url",1)])

raw_files_collection.create_index([("session_id",1),("file_path", 1)])


class GitLoader:
    def __init__(self, repo_url:str,session_id:str,user_id:str):
        self.repo_url = repo_url
        self.session_id = session_id
        self.user_id = user_id
        self.token = os.getenv("pat_token")


    def _is_text_file(self,file_path:str)->bool:
        try:
            with open(file_path,'r' , encoding='utf-8') as check_file:
                check_file.read(1024)
                return True
            
        except:
            return False
        

    def load_to_mongo(self):
        temp_dir = tempfile.mkdtemp()
        print(f"[LOADER] Created temporary directory: {temp_dir}")
        
        documents_for_splitter = []

        try:
            clone_url = self.repo_url

            if self.token:
                clone_url = clone_url.replace("https://", f"https://{self.token}@")


            print(f"[LOADER] Cloning {self.repo_url}...")
            subprocess.run(["git", "clone", clone_url, temp_dir], check=True, capture_output=True)
            
            raw_docs_for_mongo = []

            for root,dirs,files in os.walk(temp_dir):
                if '.git' in dirs:
                    dirs.remove('.git')


                for file in files:
                    file_path = os.path.join(root,file)

                    if self._is_text_file(file_path):
                        try:
                            with open(file_path , 'r',encoding='utf-8') as f:
                                content = f.read()

                            relative_path = os.path.relpath(file_path , temp_dir).replace("\\","/")

                            raw_docs_for_mongo.append({
                                "session_id":self.session_id,
                                "user_id":self.user_id,
                                "repo_url":self.repo_url,

                                "file_path":relative_path,
                                "content":content,

                                "created_at":datetime.now()
                            })

                            documents_for_splitter.append({
                                "page_content":content,
                                "metadata":{"source":relative_path , "session_id":self.session_id,"user_id":self.user_id,"repo_url":self.repo_url}
                            })

                        except Exception as e:
                            print(f"[LOADER] could not read {file_path}:{e}")


                if raw_docs_for_mongo:
                    raw_files_collection.delete_many({"session_id":self.session_id , "user_id":self.user_id})

                    raw_files_collection.insert_many(raw_docs_for_mongo)

                    print(f"[LOADER] Saved {len(raw_docs_for_mongo)} full files to 'raw_repo_files' collection!")
        
        finally:
            shutil.rmtree(temp_dir , ignore_errors=True)
            print("[LOADER] Temporary local directory deleted.")

        return documents_for_splitter


    

 

