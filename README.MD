# Fast RAG

[中文](README.zh-CN.md) | English

> Local, privacy-first RAG using PostgreSQL + pgvector and Ollama. Streams responses via SSE. Simple, fast, hackable.



<p>
  <a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white"></a>
  <a href="https://fastapi.tiangolo.com/"><img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-Latest-009485?logo=fastapi&logoColor=white"></a>
  <a href="https://www.postgresql.org/"><img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-15+-4169E1?logo=postgresql&logoColor=white"></a>
  <a href="https://github.com/pgvector/pgvector"><img alt="pgvector" src="https://img.shields.io/badge/pgvector-0.8.0-0A7CFF"></a>
  <a href="https://github.com/docling-project/docling"><img alt="Docling" src="https://img.shields.io/badge/Docling-Document_Converter-4B32C3"></a>
  <a href="https://www.postgresql.org/docs/current/pgtrgm.html"><img alt="FTS/pg_trgm" src="https://img.shields.io/badge/FTS%2Fpg__trgm-Lexical_Retrieval-0064a5"></a>
  <a href="#rag"><img alt="Hybrid Retrieval" src="https://img.shields.io/badge/Hybrid_Retrieval-Vector+Lexical-ff7f50"></a>
  <a href="https://www.docker.com/"><img alt="Docker" src="https://img.shields.io/badge/Docker-Required-2496ED?logo=docker&logoColor=white"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/License-MIT-black"></a>
</p>


![img_4.png](img_4.png)
![img_6.png](img_6.png)


![img.png](img.png)
![img_2.png](img_2.png)

## Features
- Process management 【LangGraph】
- Documents transform core tools 【Docling】、supprt PDF、DOCX、PPTX、Image、HTML、AsciiDoc、Markdown
- Semantic search with pgvector (768-dim `nomic-embed-text`)
- Streaming responses via SSE
- Optional frontend: React + Vite + TypeScript
- Local models via Ollama or openai api
- Fast ingestion: normalize → sentence chunk → batch embed → insert
- Manage corpus via REST (list, stats, chunks, search, delete)


## Architecture
![img_1.png](img_1.png)


## Table of Contents
- [Local Setup](#local-setup)
- [Run](#run)
- [Frontend (optional)](#frontend-optional)
- [License](#license)

---


- env configure


---

## Local Setup
```bash
pip install -r requirements.txt
docling-tools models download 
cp env.example .env   # edit DB_* for your environment
#python scripts/init_db.py   # if not using docker init
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


React + Vite + TypeScript app lives in `frontend-app/`.

Dev
```bash
cd frontend-app
npm install          # or: pnpm i / yarn
npm run dev          # http://localhost:5173
```

---



## License
MIT. See `LICENSE`.




