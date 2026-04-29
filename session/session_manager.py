import uuid
from datetime import datetime


class SessionManager:
    def __init__(self , db):
        self.sessions = db['sessions']
        self.chat_history = db['chat_history']



    def create_session(self, user_id , repo_url): 
        print("Looking for:", {"user_id": user_id, "repo_url": repo_url})
        existing = self.sessions.find_one(
        {"user_id": user_id, "repo_url": repo_url},
        {"session_id": 1, "_id": 0}
        )
        if existing:
           print(f"Reusing existing session {existing['session_id']} for user {user_id}")
           return existing["session_id"]
        

        session_id  =  str(uuid.uuid4())

        self.sessions.insert_one({
            "session_id": session_id,
            "user_id" : user_id,
            "repo_url": repo_url,
            "created_at": datetime.now(),
            "active": True
        })

        print(f"Created session with {session_id} and user with {user_id}")

        return session_id


    def validate_session(self , session_id):
        return self.sessions.find_one({"session_id": session_id , "active" : True})

    def fetch_session(self , session_id):
        return self.sessions.find_one({"session_id": session_id} , {"_id": 0})
    
    def save_messages(self , session_id , query , answer):
        self.chat_history.insert_one({
            "session_id" : session_id,
            "query" : query,
            "answer": answer,
            "timestamp": datetime.now()

        })

    
    def get_recent_context(self, session_id , last_n : 3):
        messages = list(self.chat_history.find(
           {"session_id" : session_id},
           {"_id" : 0 , "query": 1 , "answer": 1}
        ).sort("timestamp" , -1).limit(last_n))

        messages.reverse()

        if not messages:
            return ""
        
        return "\n".join([
            f"User: {m['query']}\nAssistant: {m['answer']}"
            for m in messages
        ])
    
 
    def end_session(self , session_id):
        self.sessions.update_one({"session_id": session_id} , {"$set": {"active": False}})





