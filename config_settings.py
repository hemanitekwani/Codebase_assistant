from pydantic_settings import BaseSettings , SettingsConfigDict
from functools import lru_cache
from typing import Optional



class Settings(BaseSettings):
    model:str = "llama-3.3-70b-versatile"
    groq_api_key: Optional[str] = None

    temprature:float=0.1


    mongodb_uri:str="mongodb://localhost:27017"
    db_name:str="codebase"


    embedding_model:str="sentence-transformers/all-MiniLM-L6-v2"

    cloned_repo_dir:str='data/repos'
    max_file_size:int=5
    index_chunk_size:int=512
    index_overlap:int=50

    
    max_context_window:int=128000
    max_conversation_history:int=50
    enable_summerization:bool=True
    summary_threshold:int=20

    enable_code_execution:bool=False
    code_execution_timeout:int=30
    enable_git_tools:bool=True

    enable_cache:bool=True
    cache_ttl_seconds:int=3600

    enable_rate_limiting:bool=True
    rate_limit_calls:int=100
    rate_limit_period:int=60

    host:str="0.0.0.0"
    port:int=8000
    log_level:str="INFO"
    log_format:str="json"
    enable_streaming:bool=True


    model_config = SettingsConfigDict(env_file=".env" ,case_sensitive=False,extra="ignore")


@lru_cache()
def get_settings()->Settings:
    return Settings()


