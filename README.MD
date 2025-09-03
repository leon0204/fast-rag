# Fast RAG
![img_4.png](img_4.png)
![img_6.png](img_6.png)
[中文](README.zh-CN.md) | English

> Local, privacy-first RAG using PostgreSQL + pgvector and Ollama. Streams responses via SSE. Simple, fast, hackable.



<p>
  <a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white"></a>
  <a href="https://fastapi.tiangolo.com/"><img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-Latest-009485?logo=fastapi&logoColor=white"></a>
  <a href="https://www.postgresql.org/"><img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-15+-4169E1?logo=postgresql&logoColor=white"></a>
  <a href="https://github.com/pgvector/pgvector"><img alt="pgvector" src="https://img.shields.io/badge/pgvector-0.8.0-0A7CFF"></a>
  <a href="https://www.docker.com/"><img alt="Docker" src="https://img.shields.io/badge/Docker-Required-2496ED?logo=docker&logoColor=white"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/License-MIT-black"></a>
</p>

## Features
- Semantic search with pgvector (768-dim `nomic-embed-text`)
- Streaming responses via SSE
- Optional frontend: React + Vite + TypeScript
- Local models via Ollama or openai api
- Fast ingestion: normalize → sentence chunk → batch embed → insert
- Manage corpus via REST (list, stats, chunks, search, delete)

## Architecture
![img_1.png](img_1.png)


## Table of Contents
- [Quick Start (Docker)](#quick-start-docker)
- [Local Setup](#local-setup)
- [Run](#run)
- [Frontend (optional)](#frontend-optional)
- [API](#api)
- [Database](#database)
- [Performance Tuning](#performance-tuning)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Quick Start (Docker)

1) Install Docker / Docker Compose
- macOS
```bash
brew install --cask docker
# or
brew install docker docker-compose
```
- Ubuntu/Debian
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

2) Deploy
```bash
chmod +x scripts/docker_deploy.sh start.sh stop.sh
./scripts/docker_deploy.sh
# or quick start
./start.sh
```

3) Verify
```bash
docker compose ps
docker compose logs postgres
docker exec fast_rag_postgres psql -U postgres -d fast_rag -c "SELECT version();"
```

---

## Local Setup
```bash
pip install -r requirements.txt
cp env.example .env   # edit DB_* for your environment
python scripts/init_db.py   # if not using docker init
```

---

## Run
```bash
python main.py
```
App: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Frontend 
![Screenshot](img_3.png)

React + Vite + TypeScript app lives in `frontend-app/`.

Dev
```bash
cd frontend-app
npm install          # or: pnpm i / yarn
npm run dev          # http://localhost:5173
```

Config
```bash
# frontend-app/.env (example)
VITE_API_BASE=http://localhost:8000
```
The frontend uses SSE to `POST /chat/stream` and uploads via `POST /upload`.

Build & preview
```bash
cd frontend-app
npm run build
npm run preview      # serve dist/
```

Notes
- CORS is enabled in the backend for `*` by default (see `main.py`).
- Update `VITE_API_BASE` if the API runs on a different host/port.

---


---

## Database
Table
```sql
CREATE TABLE document_chunks (
  id SERIAL PRIMARY KEY,
  content TEXT NOT NULL,
  file_name VARCHAR(255),
  chunk_index INTEGER,
  file_type VARCHAR(50),
  created_at TIMESTAMP DEFAULT NOW(),
  embedding vector(768)
);
```
Indexes
```sql
CREATE INDEX idx_document_chunks_embedding 
  ON document_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_document_chunks_file_name 
  ON document_chunks (file_name);
```

---

## Performance Tuning
- Use HNSW index for fast similarity search
- Batch inserts for ingestion; prepared queries for retrieval
- Cache query embeddings; reuse DB connections

Example
```sql
EXPLAIN ANALYZE SELECT * FROM document_chunks
ORDER BY embedding <=> '[0.1, 0.2, ...]' LIMIT 3;
```

---

## Troubleshooting
- Database connection
```bash
psql -h localhost -U postgres -d fast_rag
```
- pgvector extension
```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
CREATE EXTENSION IF NOT EXISTS vector;
```
- Permissions
```sql
GRANT ALL PRIVILEGES ON DATABASE fast_rag TO your_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;
```
- Logs
```bash
docker compose logs -f postgres
python main.py 2>&1 | tee app.log
```

---



## License
MIT. See `LICENSE`.




