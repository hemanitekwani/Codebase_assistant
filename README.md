# 🧠 Codebase Assistant

### AI-Powered Repository Navigator

Codebase Assistant is an intelligent conversational AI system designed to ingest, understand, index, and navigate large GitHub repositories.

Built using **LangGraph**, **FastAPI**, **Streamlit**, and **MongoDB Atlas Vector Search**, it combines **semantic retrieval**, **graph-based code understanding**, and **tool-augmented reasoning** to help developers explore unfamiliar codebases through natural language.

---

# ✨ Features

## 🤖 AI Agent Architecture

### LangGraph Orchestration

* Stateful multi-step agent workflow
* Tool-aware reasoning loop
* Structured execution pipeline

### Streaming Responses

* Real-time response streaming via Server-Sent Events (SSE)
* Live tool execution updates
* Incremental answer generation

### Conversation Memory

* Multi-turn repository conversations
* Persistent chat history
* Context-aware follow-up questions

### Dynamic Tool Calling

The agent intelligently selects tools such as:

* Semantic Code Search
* File Retrieval
* Dependency Analysis
* Graph Navigation

without requiring manual intervention.

---

# 🔐 Multi-User Session Isolation

Designed for multi-user environments.

### Features

* Secure `X-User-Id` based routing
* Isolated repositories per session
* Independent conversation histories
* Active agent separation
* Encrypted frontend cookie management

---

# 📚 Hybrid RAG Pipeline

Traditional RAG struggles with understanding relationships between files.

Codebase Assistant combines:

### Vector Retrieval

Used for:

* Semantic code search
* Concept discovery
* Logic tracing
* Function lookup

### Graph Retrieval

Used for:

* Import relationships
* Dependency tracking
* File-level structure
* Repository navigation

This hybrid architecture allows the assistant to understand both:

* **What code means**
* **How code is connected**

---

# 🛠️ Agent Tooling

## Semantic Retrieval

Search repository content using vector embeddings.

```text
"Where is authentication implemented?"
```

```text
"Show me JWT validation logic."
```

---

## Direct File Retrieval

Retrieve exact file contents when the user asks for specific files.

```text
"Open tools.py"
```

```text
"Show app.py"
```

---

## Dependency Analysis

Inspect:

* Imports
* Module relationships
* Internal dependencies

---

## Extensible Tool Framework

New tools can be added easily through the factory pattern.

Examples:

* GitHub API Tools
* Jira Integration
* Documentation Search
* Web Search
* Code Execution Tools

---

# 💾 Data Persistence

All application state is stored remotely using MongoDB Atlas.

### Benefits

* No local volumes required
* Persistent sessions
* Scalable architecture
* Cloud-native deployment

---

# 🏗️ System Architecture

```text
                    ┌─────────────┐
                    │  Streamlit  │
                    │  Frontend   │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   FastAPI   │
                    │   Backend   │
                    └──────┬──────┘
                           │
        ┌──────────────────┴──────────────────┐
        │                                     │
        ▼                                     ▼

 ┌──────────────┐                     ┌──────────────┐
 │ Repository   │                     │  LangGraph   │
 │ Ingestion    │                     │    Agent     │
 └──────┬───────┘                     └──────┬───────┘
        │                                    │
        ▼                                    ▼
 ┌──────────────┐                     ┌──────────────┐
 │ Chunking &   │                     │ Tool Calling │
 │ Embeddings   │                     │ + Retrieval  │
 └──────┬───────┘                     └──────┬───────┘
        │                                    │
        └──────────────┬─────────────────────┘
                       ▼
               ┌──────────────┐
               │ MongoDB      │
               │ Atlas        │
               │ • Vectors    │
               │ • Sessions   │
               │ • Graph Data │
               └──────────────┘

# 🔄 LangGraph Workflow

```text
          START
             │
             ▼
     ┌─────────────┐
     │ LLM Reason  │
     └──────┬──────┘
            │
            ▼
     Need Tool Call?
        /       \
      Yes       No
       │         │
       ▼         ▼
 ┌───────────┐  END
 │ Tool Node │
 └─────┬─────┘
       │
       ▼
  Tool Results
       │
       ▼
 Back To LLM
```

---

# 🚀 Quick Start

## 1. Clone Repository

```bash
git clone https://github.com/yourusername/codebase-assistant.git

cd codebase-assistant
```

---

## 2. Configure Environment Variables

Create a `.env` file:

```env
# LLM Provider
GROQ_API_KEY=your_groq_api_key

# Optional Reranker
COHERE_API_KEY=your_cohere_api_key

# MongoDB Atlas
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/
```

---

## 3. Build and Run

```bash
docker compose up --build
```

---

# 🌐 Access the Application

### Streamlit UI

```text
http://localhost:8501
```

### FastAPI Docs

```text
http://localhost:8000/docs
```

---

# 🎨 Streamlit Interface

The frontend provides an intuitive repository exploration experience.

### Features

✅ Session Management

✅ Repository Ingestion

✅ Real-Time Chat

✅ Streaming Responses

✅ Tool Execution Visibility

✅ Status Indicators

---

# 📡 API Usage

## Authentication

All endpoints require:

```http
X-User-Id
```

for user isolation.

---

## Start Session

```bash
curl -X POST http://localhost:8000/session/start \
-H "Content-Type: application/json" \
-H "X-User-Id: user_123" \
-d '{
  "repo_url":"https://github.com/user/repo"
}'
```

---

## Ingest Repository

```bash
curl -X POST http://localhost:8000/ingest \
-H "Content-Type: application/json" \
-H "X-User-Id: user_123" \
-d '{
  "repo_url":"https://github.com/user/repo",
  "session_id":"session_abc"
}'
```

---

## Query Repository

```bash
curl -X POST http://localhost:8000/query/stream \
-H "Content-Type: application/json" \
-H "X-User-Id: user_123" \
-d '{
  "session_id":"session_abc",
  "query":"Where is the authentication logic located?"
}'
```

---

# 📊 MongoDB Collections

## vector_store

Stores:

* Code chunks
* Embeddings
* Metadata
* Repository references

---

## graph_store

Stores:

* Nodes
* Edges
* Dependency relationships
* Repository structure

---

## sessions

Stores:

* Session IDs
* User IDs
* Conversation history
* Context memory

---

# 🎯 Key Design Decisions

## Why Hybrid RAG?

Codebases are highly relational systems.

Vector search answers:

> "What does this code do?"

Graph search answers:

> "How is this code connected?"

Combining both provides significantly better repository understanding than traditional vector-only RAG systems.

---

# 🧰 Tech Stack

| Layer            | Technology                               |
| ---------------- | ---------------------------------------- |
| Frontend         | Streamlit                                |
| Backend          | FastAPI                                  |
| Agent Framework  | LangGraph                                |
| LLM              | Groq                                     |
| Embeddings       | Sentence Transformers (all-MiniLM-L6-v2) |
| Database         | MongoDB Atlas                            |
| Vector Search    | Atlas Vector Search                      |
| Graph Engine     | rustworkx                                |
| Containerization | Docker                                   |
| Orchestration    | Docker Compose                           |

---

# 📜 License

MIT License

---

Built to make understanding large codebases conversational, searchable, and significantly faster.

