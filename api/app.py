import os

from fastapi import FastAPI , Header , HTTPException , BackgroundTasks
import uvicorn

from fastapi.responses import StreamingResponse

from typing import Optional,AsyncGenerator,Dict,Any
import json
import logging
from datetime import datetime
from config_settings import get_settings

from pydantic import BaseModel
from agent.agent import CodebaseAgent


from fastapi.responses import JSONResponse



from session.session_manager import SessionManager
from ingestion.loader import GitLoader
from ingestion.splitter import Splitter
from ingestion.vector_store import VectorStore
from graph.builder import GraphBuilder
from graph.store import GraphStore
from graph.indexer import GraphIndexer
from datetime import datetime


app = FastAPI(
    title = "CodeBase Assistant",
    description = "AI-powered codebase understanding with session isolation",
    version = "2.0.0"

)

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


settings =  get_settings()


vector_store = VectorStore()
vector_store.connect()

session_manager = SessionManager(vector_store.db)


active_agents: Dict[str,CodebaseAgent] = {}


def get_or_create_agent(session_id:str,x_user_id:str)->CodebaseAgent:
    if session_id not in active_agents:
        active_agents[session_id] = CodebaseAgent(
            session_id = session_id,
            user_id = x_user_id,
            # model="llama-3.1-8b-instant",
            model="llama-3.3-70b-versatile",
            vector_db=vector_store.collection,
           
        )
    
    return active_agents[session_id]



class IngestRequest(BaseModel):
    repo_url:str
    session_id:str


class Startrequest(BaseModel):
    repo_url: str



class Queryrequest(BaseModel):
    session_id: str
    query: str
    stream:bool=True


class ToolRequest(BaseModel):
    session_id:str
    inputs:Dict[str,Any]


class StreamMessage(BaseModel):
    type:str
    data:dict
    timestamp:str


@app.get("/")
async def root():
    """Landing page"""
    return {
        "message": "Codebase Assistant API v3.0.0",
        "status": "running",
        "documentation": "/docs",
        "endpoints": {
            "session": {
                "start": "POST /session/start",
                "get": "GET /session/{session_id}",
                "end": "DELETE /session/{session_id}"
            },
            "query": {
                "standard": "POST /query",
                "stream": "POST /query/stream"
            },
            "ingestion": "POST /ingest"
        }
    }


@app.post("/ingest")
async def ingest(request: IngestRequest,x_user_id:str = Header(...)):
    session = session_manager.validate_session(request.session_id , x_user_id)

    if not session:
        raise HTTPException(
            status_code=403,
            detail="Invalid Session"
        )
    

    loader = GitLoader(repo_url = request.repo_url , session_id=request.session_id, user_id = x_user_id)
    raw_documents = loader.load_to_mongo()

    if not raw_documents:
        raise HTTPException(status_code=400, detail="No readable text files found in the repository.")

    print("Step 2: Splitting files into semantic chunks...")

    splitter = Splitter()
    vector_chunks = splitter.split(raw_documents)

    print("Embedding and storing chunks...")

    vector_store.insert_embeddings(
        docs=vector_chunks,
        repo_url=request.repo_url,
        session_id=request.session_id,
        user_id=x_user_id
    )
    print(" Ingestion Complete!")
    
    graph_store = GraphStore(vector_store.db,session_id=request.session_id)

    if graph_store.exists(request.repo_url):
        print('Graph Exists, loading from DB...')
        graph , _ = graph_store.load(request.repo_url)

    else:
        print("Graph not Present Building it..")
        builder = GraphBuilder()
        graph = builder.build(raw_documents)
        graph_store.save(graph , request.repo_url)
        print(f" Graph built and saved")
    
    existing_graph_indices = vector_store.collection.count_documents(
        {"metadata.session_id": request.session_id, "metadata.content_type": "graph_relationship"}
    )

    if existing_graph_indices == 0: 
        indexer = GraphIndexer(vector_store , request.session_id)
        indexer.index(graph , request.repo_url)
        print("Graph indexed to vectore store")

    return {
        "status" : "ingested",
    }



@app.post("/session/start")
async def create_session(request:Startrequest, x_user_id:str = Header(...)):
    print("Received repo_url:", request.repo_url)
    print("Received user_id:", x_user_id)

    session_id = session_manager.create_session(
        user_id  = x_user_id , 
        repo_url = request.repo_url
    )

    # if not session_id:
    #     session_id = session_manager.get_existing_session(x_user_id = x_user_id , repo_url = request.repo_url)

    return {"session_id": session_id}


@app.get("/conversation/{session_id}")
async def get_conversation(session_id:str , x_user_id:str = Header(...)):
    session = session_manager.validate_session(
        session_id,
        x_user_id
    )

    if not session:
        raise HTTPException(status_code=403,detail="Invalid Session")
    
    
    history = session_manager.get_recent_context(session_id, last_n=50)

    return {
        "session_id":session_id,
        "messages":history,
        "timestamps":datetime.now().isoformat()
    }



@app.delete("/session/{session_id}")
async def end_session(session_id:str , x_user_id: str = Header(...)):
    
    session = session_manager.validate_session(session_id , x_user_id)

    if not session:
        raise HTTPException(status_code=403,
        detail="Invalid Session")
    

    session_manager.end_session(session_id)

    if session_id in active_agents:
        del active_agents[session_id]

    return {"status": "ended"}


@app.post("/query")
async def process_query(request:Queryrequest , x_user_id:str = Header(...)):
    if not request.query.strip():
        raise HTTPException(status_code=400 , detail="Query cannot be empty")
    
    if not session_manager.validate_session(request.session_id,x_user_id):
        raise HTTPException(status_code=403,detail="Invalid session")
    

    agent = get_or_create_agent(request.session_id,x_user_id)

    try:
        events = []

        async for event in agent.stream_response(request.query):
            events.append(event)

        final_event = events[-1] if events else {"type":"error","data":{"error":"No response"}}
        final_answer = final_event.get("data",{}).get("answer","")

        if final_answer:
            session_manager.save_messages(request.session_id,"user",request.query,request.query)


            session_manager.save_messages(request.session_id, "assistant", request.query, final_answer)


        return {
            "status":"success",
            "query":request.query,
            "response":final_answer,
            "session_id":request.session_id,
            "timestamp":datetime.now().isoformat(),
            "event_count":len(events)

        }

    except Exception as e:
        logger.error(f"Error Processing query:{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/query/stream")
async def stream_query(request: Queryrequest, x_user_id: str = Header(...)):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    if not session_manager.validate_session(request.session_id,x_user_id):
        raise HTTPException(status_code=403, detail="Invalid session")
    
    agent = get_or_create_agent(request.session_id , x_user_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        final_answer = ""

        try:
            async for event in agent.stream_response(request.query):
                
                raw_ts = event.get("timestamp", datetime.now())
                
                if not isinstance(raw_ts, str):
                    safe_ts = raw_ts.isoformat() if hasattr(raw_ts, 'isoformat') else str(raw_ts)
                else:
                    safe_ts = raw_ts

                yield json.dumps({
                    "type": event.get("type"),
                    "data": event.get("data", {}),
                    "timestamp": safe_ts
                }) + '\n'

                if event.get("type") == "end":
                    final_answer = event.get("data", {}).get("answer", "")

            if final_answer:
                session_manager.save_messages(request.session_id,"user",request.query,request.query)


                session_manager.save_messages(request.session_id, "assistant", request.query, final_answer)

        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            yield json.dumps({
                "type": "error",
                "data": {"error": f"Streaming interrupted: {str(e)}"},
                "timestamp": datetime.now().isoformat()
            }) + '\n'

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

    

@app.exception_handler(Exception)
async def global_exception_handler(request,exc):
    logger.error(f"Unhandled exception:{str(exc)}")

    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )


@app.on_event("startup")
async def startup():
    logger.info("starting Codebase Assistant API")
    logger.info(f"Model:{settings.model}")

@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting Down Codebase Assistant")



if __name__=="__main__":
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        workers=1,
        log_level=settings.log_level.lower()
    )




        













