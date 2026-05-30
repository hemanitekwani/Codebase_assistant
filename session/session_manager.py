import uuid
from datetime import datetime
from enum import Enum
import logging

from typing import Optional

logger = logging.getLogger(__name__)


class SessionStatus(str,Enum):
    ACTIVE = "active"
    ENDED = "ended"



class SessionManager:
    def __init__(self , db):
        self.sessions = db['sessions']
        self.chat_history = db['chat_history']
        self._create_indexes()


        

    def _create_indexes(self):
        try:
            self.sessions.create_index("session_id" ,unique=True)
            self.sessions.create_index([("user_id",1), ("repo_url",1)])
            self.chat_history.create_index([("session_id",1), ("timestamp",-1)])

        except Exception as e:
            logger.warning(f"Index creation failed: {e}")

        
    def create_session(self, user_id:str , repo_url:str): 

        print("Looking for:", {"user_id": user_id, "repo_url": repo_url})

        existing = self.sessions.find_one({
        "user_id": user_id,
        "repo_url": repo_url,
        "status": SessionStatus.ACTIVE
        })

        if existing:
            logger.info(f"Reusing session {existing['session_id']}")
            
            self.sessions.update_one(
                {"session_id":existing["session_id"]},
                {
                    "$set":{
                        "last_activity":datetime.now()
                    }
                }
            )

            return existing["session_id"]
        

        session_id  =  str(uuid.uuid4())

        self.sessions.insert_one({
            "session_id": session_id,
            "user_id" : user_id,
            "repo_url": repo_url,
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "status": SessionStatus.ACTIVE,

            "metadata":{
                "queries_executed":0,
                "tools_used":[],
                "total_tokens":0
            }
        })

        logger.info(f"Created session {session_id}")

        return session_id


    def validate_session(self , session_id,user_id):
        session = self.sessions.find_one({"session_id": session_id , "user_id":user_id,"status" : SessionStatus.ACTIVE})

        if session:
            self.sessions.update_one(
                {"session_id": session_id},
                {
                    "$set":{
                        "last_activity":datetime.now()
                    }
                }
            )

        return session

    def fetch_session(self , session_id):
        return self.sessions.find_one({"session_id": session_id} , {"_id": 0})
    
    def save_messages(self , session_id , role , query , content):
        self.chat_history.insert_one({
            "session_id" : session_id,
            "role" : role,
            "query":query,
            "content": content,
            "timestamp": datetime.now()

        })

    
    def get_recent_context(self, session_id , last_n : 3):
        messages = list(self.chat_history.find(
           {"session_id" : session_id},
           {"_id" : 0}
        ).sort("timestamp" , -1).limit(last_n))

        messages.reverse()

        if not messages:
            return ""
        
        return "\n".join([
            f"User: {m['role'].upper()}\n {m['content'][:500]}"
            for m in messages
        ])
    

    def update_metadata(self , session_id:str, tool_name:Optional[str]=None,tokens:int=0):
        update = {
            "$inc":{
                "metadata.queries_executed":1,
                "metadata.total_tokens":tokens
            }
        }

        if tool_name:
            update["$addToSet"]= {
                "metadata.tools_used":tool_name

            }

        self.sessions.update_one(
            {"session_id":session_id},
            update
        )
            
    
 
    def end_session(self , session_id):
        self.sessions.update_one({"session_id": session_id} , {"$set": {"status": SessionStatus.ENDED , "ended_at":datetime.now()}})





