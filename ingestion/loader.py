import os
import subprocess
import uuid
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("pat_token")

class gitloader:
    def __init__(self, repo_url):
        self.repo_url = repo_url


    def load(self):
        base_dir = os.path.join("data" , "repos")
        os.makedirs(base_dir , exist_ok = True)

        temp_dir = os.path.join(base_dir, str(uuid.uuid4()))

        if token:
            self.repo_url = self.repo_url.replace("https://", f"https://{token}@")

        subprocess.run(["git", "clone" , self.repo_url , temp_dir], check = True)

        return temp_dir
    

 

