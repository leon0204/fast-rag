#!/bin/bash

# Fast RAG Docker 部署脚本
# 用于部署 PostgreSQL + pgvector 服务

set -e

echo "🐳 Fast RAG Docker 部署脚本"
echo "================================"

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    echo "   访问: https://docs.docker.com/get-docker/"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
    echo "   访问: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker 环境检查通过"

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p scripts
mkdir -p logs

# 检查配置文件
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yml 文件不存在"
    exit 1
fi

if [ ! -f "scripts/init_pgvector.sql" ]; then
    echo "❌ scripts/init_pgvector.sql 文件不存在"
    exit 1
fi

echo "✅ 配置文件检查通过"

# 停止现有服务（如果存在）
echo "🛑 停止现有服务..."
docker compose down --remove-orphans 2>/dev/null || true

# 清理现有数据（可选）
read -p "是否清理现有数据？这将删除所有数据库数据 (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 清理现有数据..."
    docker compose down -v --remove-orphans
    docker system prune -f
fi

# 启动服务
echo "🚀 启动 PostgreSQL + pgvector 服务..."
docker compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "🔍 检查服务状态..."
docker compose ps

# 检查数据库连接
echo "🔌 测试数据库连接..."
for i in {1..30}; do
    if docker exec fast_rag_postgres pg_isready -U postgres -d fast_rag >/dev/null 2>&1; then
        echo "✅ 数据库连接成功"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ 数据库连接超时"
        docker compose logs postgres
        exit 1
    fi
    echo "⏳ 等待数据库启动... ($i/30)"
    sleep 2
done

# 检查 pgvector 扩展
echo "🔍 检查 pgvector 扩展..."
if docker exec fast_rag_postgres psql -U postgres -d fast_rag -c "SELECT * FROM pg_extension WHERE extname = 'vector';" | grep -q vector; then
    echo "✅ pgvector 扩展安装成功"
else
    echo "❌ pgvector 扩展安装失败"
    docker compose logs postgres
    exit 1
fi

# 检查表结构
echo "🔍 检查表结构..."
if docker exec fast_rag_postgres psql -U postgres -d fast_rag -c "\dt" | grep -q document_chunks; then
    echo "✅ 表结构创建成功"
else
    echo "❌ 表结构创建失败"
    docker compose logs postgres
    exit 1
fi

echo ""
echo "🎉 部署完成！"
echo "================================"
echo "📊 服务信息："
echo "   PostgreSQL: localhost:5432"
echo "   pgAdmin:    http://localhost:8080"
echo "   Redis:      localhost:6379"
echo ""
echo "🔑 数据库连接信息："
echo "   数据库: fast_rag"
echo "   用户:   postgres"
echo "   密码:   password"
echo ""
echo "📝 下一步："
echo "   1. 配置环境变量: cp env.example .env"
echo "   2. 启动应用: python main.py"
echo "   3. 上传文档: POST /upload"
echo "   4. 开始对话: POST /chat/stream"
echo ""
echo "📚 管理命令："
echo "   查看日志: docker compose logs -f"
echo "   停止服务: docker compose down"
echo "   重启服务: docker compose restart"
echo "   查看状态: docker compose ps"
