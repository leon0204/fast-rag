#!/bin/bash

# Fast RAG 快速启动脚本
# 一键启动所有服务

set -e

echo "🚀 Fast RAG 快速启动脚本"
echo "================================"

# 检查 Docker 服务状态
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker 服务未运行，请先启动 Docker"
    exit 1
fi

# 检查 Ollama 服务状态
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "⚠️  Ollama 服务未运行，请先启动 Ollama"
    echo "   启动命令: ollama serve"
    echo "   或者: brew services start ollama (macOS)"
fi

# 启动数据库服务
echo "🗄️  启动 PostgreSQL + pgvector 服务..."
if [ ! -f ".env" ]; then
    echo "📝 创建环境变量文件..."
    cp env.docker .env
    echo "✅ 环境变量文件创建完成"
fi

# 启动 Docker 服务
docker compose up -d

# 等待数据库启动
echo "⏳ 等待数据库服务启动..."
sleep 15

# 检查数据库状态
if docker exec fast_rag_postgres pg_isready -U postgres -d fast_rag >/dev/null 2>&1; then
    echo "✅ 数据库服务启动成功"
else
    echo "❌ 数据库服务启动失败"
    docker compose logs postgres
    exit 1
fi

# # 启动 Python 应用
# echo "🐍 启动 Python 应用..."
# echo "   应用将在 http://localhost:8000 启动"
# echo "   按 Ctrl+C 停止应用"
# echo ""

# # 启动应用
# python main.py
