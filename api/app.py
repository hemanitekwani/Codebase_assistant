from fastapi import FastAPI , Header , HTTPException
from pydantic import BaseModel
from agent.agent import build_agent
from session.session_manager import SessionManager
from ingestion.loader import gitloader
from ingestion.splitter import Splitter
from ingestion.vector_store import VectorStore
from graph.builder import GraphBuilder
from graph.store import GraphStore
from graph.indexer import GraphIndexer

app = FastAPI()


vector_store = VectorStore()
vector_store.connect()

session_manager = SessionManager(vector_store.db)
agent = build_agent(vector_store.collection)





class Startrequest(BaseModel):
    repo_url: str

class Queryrequest(BaseModel):
    session_id: str
    query: str


@app.post("/ingest")
async def ingest(request: Startrequest , x_user_id: str = Header(...)):
    loader = gitloader(request.repo_url)
    repo_path = loader.load()


    existing = vector_store.collection.count_documents(
        {"metadata.repo_url": request.repo_url,
         "metadata.content_type": "code"}
    )
    
    if existing == 0:
        docs = Splitter().split(repo_path)
        vector_store.insert_embeddings(docs , request.repo_url)
        print("Smenatic chunks Stored")
        
    
    graph_store = GraphStore(vector_store.db)

    if graph_store.exists(request.repo_url):
        print('Graph Exists, loading from DB...')
        graph , _ = graph_store.load(request.repo_url)

    else:
        print("Graph not Present Building it..")
        builder = GraphBuilder()
        graph = builder.build(repo_path)
        graph_store.save(graph , request.repo_url)
        print(f" Graph built and saved")
    
    existing_graph_indices = vector_store.collection.count_documents(
        {"metadata.repo_url": request.repo_url, "metadata.content_type": "graph_relationship"}
    )

    if existing_graph_indices == 0: 
        indexer = GraphIndexer(vector_store)
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

@app.post("/chat")
async def chat(request:Queryrequest , x_user_id: str = Header(...)):
    if not session_manager.validate_session(request.session_id):
        raise HTTPException(status_code = 403 , detail = "Invalid session")


    session = session_manager.fetch_session(request.session_id)

    recent_context = session_manager.get_recent_context(
        session_id = request.session_id,
        last_n = 3
    )

    result = agent.invoke({
        "user_id": x_user_id,
        "session_id": request.session_id,
        "query": request.query,
        "repo_url": session['repo_url'],
        "recent_context": recent_context,
        "steps": []

    })

    session_manager.save_messages(
        session_id = request.session_id,
        query = request.query,
        answer = result["answer"]
    )

    return {
        "answer" : result["answer"],
        "session_id" : request.session_id,
        "steps": result["steps"]
    }


@app.delete("/session/{session_id}")
async def end_session(session_id:str , x_user_id: str = Header(...)):
    if not session_manager.validate(session_id , x_user_id):
        raise HTTPException(status_code = 403 , detail = "Invalid Session")
    

    session_manager.end_session(session_id)
    return {"status": "ended"}


def get_existing_session(user_id  , repo_url):
    doc = session_manager.sessions.find_one(
        {"user_id": user_id, "repo_url": repo_url},
        {"session_id": 1 , "_id": 0}
        )
    
    return doc['session_id'] if doc else None
    





