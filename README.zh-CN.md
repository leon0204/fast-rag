# Fast RAG（中文）

[English](README.MD) | 中文

> 本地、隐私优先的 RAG：使用 PostgreSQL + pgvector 与 Ollama，SSE 流式返回，简单、快速、易于改造。

<p>
  <a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white"></a>
  <a href="https://fastapi.tiangolo.com/"><img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-Latest-009485?logo=fastapi&logoColor=white"></a>
  <a href="https://www.postgresql.org/"><img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-15+-4169E1?logo=postgresql&logoColor=white"></a>
  <a href="https://github.com/pgvector/pgvector"><img alt="pgvector" src="https://img.shields.io/badge/pgvector-0.8.0-0A7CFF"></a>
  <a href="https://www.docker.com/"><img alt="Docker" src="https://img.shields.io/badge/Docker-Required-2496ED?logo=docker&logoColor=white"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/License-MIT-black"></a>
</p>

## 功能特性
- pgvector 语义检索（768 维 `nomic-embed-text`）
- SSE 流式响应
- 可选前端：React + Vite + TypeScript
- 本地模型：Ollama
- 快速入库：规范化 → 句子分块 → 批量向量化 → 入库
- 语料管理 REST：列表、统计、Chunks、搜索、删除

## 架构
![img_1.png](img_1.png)


## 目录
- [快速开始（Docker）](#快速开始docker)
- [本地安装](#本地安装)
- [运行](#运行)
- [前端](#前端)
- [API](#api)
- [数据库](#数据库)
- [性能调优](#性能调优)
- [故障排除](#故障排除)
- [License](#license)

---

## 快速开始（Docker）

1) 安装 Docker / Docker Compose
- macOS
```bash
brew install --cask docker
# 或
brew install docker docker-compose
```
- Ubuntu/Debian
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

2) 部署
```bash
chmod +x scripts/docker_deploy.sh start.sh stop.sh
./scripts/docker_deploy.sh
# 或快速启动
./start.sh
```

3) 验证
```bash
docker compose ps
docker compose logs postgres
docker exec fast_rag_postgres psql -U postgres -d fast_rag -c "SELECT version();"
```

---

## 本地安装
```bash
pip install -r requirements.txt
cp env.example .env   # 根据环境配置 DB_*
python scripts/init_db.py   # 若不使用 docker 的初始化
```

---

## 运行
```bash
python main.py
```
服务地址： http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 前端 
![Screenshot](img_3.png)

前端位于 `frontend-app/`（React + Vite + TypeScript）。

开发
```bash
cd frontend-app
npm install          # 或 pnpm i / yarn
npm run dev          # http://localhost:5173
```

配置
```bash
# frontend-app/.env 示例
VITE_API_BASE=http://localhost:8000
```
前端通过 `POST /chat/stream` 使用 SSE；通过 `POST /upload` 上传。

构建与预览
```bash
cd frontend-app
npm run build
npm run preview      # 预览 dist/
```

注意
- 后端默认已允许通配 CORS（见 `main.py`）。
- 如果 API 在其他主机/端口，请更新 `VITE_API_BASE`。

---

## API
上传
```http
POST /upload        (multipart/form-data; 支持 PDF/JSON/TXT)
```
对话
```http
POST /chat/stream   (form: query, session_id 可选)
```
管理
```http
GET    /manage/files
GET    /manage/stats
GET    /manage/files/{file_name}/chunks?limit&offset&preview_length
GET    /manage/files/{file_name}/search?q&limit&offset&preview_length
DELETE /manage/files/{file_name}
DELETE /manage/all
```

---

## 数据库
表
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
索引
```sql
CREATE INDEX idx_document_chunks_embedding 
  ON document_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_document_chunks_file_name 
  ON document_chunks (file_name);
```

---

## 性能调优
- 使用 HNSW 向量索引以加速相似度检索
- 入库使用批量插入；检索使用预编译语句
- 缓存查询向量；复用数据库连接

示例
```sql
EXPLAIN ANALYZE SELECT * FROM document_chunks
ORDER BY embedding <=> '[0.1, 0.2, ...]' LIMIT 3;
```

---

## 故障排除
- 数据库连接
```bash
psql -h localhost -U postgres -d fast_rag
```
- pgvector 扩展
```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
CREATE EXTENSION IF NOT EXISTS vector;
```
- 权限
```sql
GRANT ALL PRIVILEGES ON DATABASE fast_rag TO your_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;
```
- 日志
```bash
docker compose logs -f postgres
python main.py 2>&1 | tee app.log
```

---

## License
MIT. 详见 `LICENSE`。
