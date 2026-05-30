# 🧠 Codebase Assistant

**AI-powered repository navigator for exploring GitHub codebases through natural language.**

Codebase Assistant ingests GitHub repositories, builds vector and graph indexes, and enables developers to query codebases conversationally. It combines semantic retrieval with repository structure awareness to provide accurate answers about files, functions, dependencies, and application flow.

---

## ✨ Features

* Conversational repository exploration using natural language
* Hybrid RAG pipeline (Vector Search + Graph Retrieval)
* Multi-user session isolation
* Real-time streaming responses
* Persistent chat history
* Repository dependency analysis
* Dockerized deployment

---

## 🏗️ Architecture

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
 │ Embeddings   │                     │ Tool Calling │
 │ + Chunking   │                     │ + Retrieval  │
 └──────┬───────┘                     └──────┬───────┘
        │                                    │
        └──────────────┬─────────────────────┘
                       ▼
               ┌──────────────┐
               │ MongoDB      │
               │ Atlas        │
               └──────────────┘
```

---

## 🔄 Agent Workflow

```text
START
  │
  ▼
LLM Node
  │
  ▼
Tool Required?
 ├── No ──► END
 │
 ▼
Tool Execution
 │
 ▼
Tool Results
 │
 ▼
LLM Node
```

---

## 📚 Hybrid RAG

The system combines two retrieval strategies:

| Retrieval Type  | Purpose                                              |
| --------------- | ---------------------------------------------------- |
| Vector Search   | Finds semantically relevant code and concepts        |
| Graph Retrieval | Tracks imports, dependencies, and file relationships |

This allows the assistant to understand both **what code does** and **how components are connected**.

---

## 🚀 Quick Start

### Clone Repository

```bash
git clone https://github.com/yourusername/codebase-assistant.git
cd codebase-assistant
```

### Configure Environment Variables

```env
GROQ_API_KEY=your_groq_api_key
COHERE_API_KEY=your_cohere_api_key

MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/
```

### Run with Docker

```bash
docker compose up --build
```

---

## 🌐 Access

| Service      | URL                        |
| ------------ | -------------------------- |
| Streamlit UI | http://localhost:8501      |
| FastAPI Docs | http://localhost:8000/docs |

---

## 📡 API Endpoints

| Endpoint            | Purpose                    |
| ------------------- | -------------------------- |
| POST /session/start | Create repository session  |
| POST /ingest        | Clone and index repository |
| POST /query/stream  | Chat with the repository   |

All requests require the `X-User-Id` header for user isolation.

---

## 🗄️ MongoDB Collections

| Collection   | Description                       |
| ------------ | --------------------------------- |
| vector_store | Code chunks and embeddings        |
| graph_store  | Repository dependency graph       |
| sessions     | Chat history and session metadata |

---

## 🧰 Tech Stack

| Layer            | Technology            |
| ---------------- | --------------------- |
| Frontend         | Streamlit             |
| Backend          | FastAPI               |
| Agent            | LangGraph             |
| LLM              | Groq                  |
| Embeddings       | Sentence Transformers |
| Database         | MongoDB Atlas         |
| Graph Engine     | rustworkx             |
| Containerization | Docker                |

---

## 📜 License

MIT License


