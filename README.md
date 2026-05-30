
🧠Codebase Assistant - AI-Powered Repository Navigator
A conversational AI assistant designed to ingest, index, and navigate complex GitHub repositories. Built with a modern microservices architecture using LangGraph, FastAPI, Streamlit, and MongoDB Atlas Vector Search. It features hybrid RAG capabilities, combining semantic search with structural graph indexing.

✨ Features
🤖 AI Agent Architecture

LangGraph Orchestration: Stateful, ReAct-style agent workflow.

Streaming Responses: Real-time token streaming to the UI via Server-Sent Events (SSE).

Conversation Memory: Multi-turn interactions persisted in MongoDB.

Dynamic Tool Calling: LLM intelligently selects the right tool for searching code or navigating dependencies.

🔐 Multi-User Session Isolation

Secure X-User-Id header-based routing.

Isolated chat histories and active agents per user session.

Encrypted cookie management on the frontend.

📚 Graph & Vector RAG Pipeline

MongoDB Atlas: Unified storage for vectors, graph edges, and chat memory.

Local Embeddings: Uses Hugging Face all-MiniLM-L6-v2 (via sentence-transformers) for high-quality, free semantic embeddings.

Graph Indexing: Uses rustworkx to map file dependencies, imports, and codebase structure.

🛠️ Agent Tools

vector_retrieval: Semantic search across the codebase for concepts and logic.

file_match: Direct retrieval of specific file contents.

(Extendable factory pattern to easily add GitHub API or web search tools)

💾 Data Persistence

Fully remote storage via MongoDB Atlas (no local volumes required for data).

Automatic document deduplication and index management.  

🚀 Quick Start

Installation & Setup

1. Clone the repository:
git clone https://github.com/yourusername/codebase-assistant.git
cd codebase-assistant

2.Set up environment variables:
Create a .env file in the root directory:


# API Keys
GROQ_API_KEY=your_groq_api_key
COHERE_API_KEY=your_cohere_key

# MongoDB Configuration
MONGO_URI=mongodb+srv://<user>:<password>@cluster.mongodb.net/

3.Build and Run the Containers:

docker compose up --build
Access the Application
🎨 Streamlit App: http://localhost:8501

📖 API Documentation (Swagger): http://localhost:8000/docs

docs

🎨 Streamlit Web Interface
A beautiful, interactive web interface for exploring your codebases.

Features:

1.Session Management: Automatically handles User IDs via encrypted cookies.

2.Repository Ingestion: Simply paste a GitHub URL to trigger the backend cloning and embedding pipeline.

3.Real-time Chat: Interactive chat window with live-streaming responses.

4.Status Indicators: Visual feedback during the heavy lifting of indexing and embedding.

Quick Start via Browser:
Simply navigate to http://localhost:8501 after running docker compose up.


API Usage (For Direct API Access)
Authentication
All endpoints require authentication via the X-User-Id header to maintain session isolation.

Endpoints
1. POST /session/start - Initialize a Session
Registers a user and target repository.

curl -X POST http://localhost:8000/session/start \
  -H "Content-Type: application/json" \
  -H "X-User-Id: user_123" \
  -d '{"repo_url": "https://github.com/user/repo"}'


2. POST /ingest - Process a Repository
Clones, splits, embeds, and indexes the codebase.

curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -H "X-User-Id: user_123" \
  -d '{"repo_url": "https://github.com/user/repo", "session_id": "session_abc"}'

3. POST /query/stream - Chat with the Codebase
Streams the LLM response via NDJSON

curl -X POST http://localhost:8000/query/stream \
  -H "Content-Type: application/json" \
  -H "X-User-Id: user_123" \
  -d '{"session_id": "session_abc", "query": "Where is the authentication logic located?"}'


🏗️Architecture

User Request → Streamlit UI → Docker Network → FastAPI Backend
                                                    ↓
                                            [Session Manager]
                                                    ↓
                              ┌─────────────────────┴─────────────────────┐
                              │                                           │
                        Ingestion Route                              Chat Route
                        (Git Clone)                               (LangGraph Agent)
                              ↓                                           ↓
                      [Text Splitter]                              [Tool Execution]
                              ↓                                           ↓
                 [Sentence Transformers]                    [Vector/Graph Retrieval]
                              ↓                                           ↓
                      [MongoDB Atlas]  ← ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  [Context Sync]


LangGraph State Machine

Entry → LLM Node (Decision) → Should Call Tool?
          ↑                        ├─ Yes → Tool Executor Node ─┐
          │                        └─ No → END                  │
          └─────────────────────────────────────────────────────┘


🎯 Key Design Decisions- 
1. Why Graph + Vector (Hybrid RAG)?
Codebases are highly relational. Semantic vector search is great for finding concepts, but Graph indexing ensures the AI understands dependencies (e.g., "File A imports File B").

📊 Database Schema (MongoDB Collections)
vector_store: Contains chunked code strings, embedding vectors, and metadata (file path, repo URL).

graph_store: Contains serialized rustworkx nodes and edges mapping the repository structure.

sessions: Contains session_id, user_id, and conversational message history (HumanMessage, AIMessage).

