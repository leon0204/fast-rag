#!/bin/bash

# Fast RAG 停止脚本
# 一键停止所有服务

echo "🛑 Fast RAG 停止脚本"
echo "================================"

# 停止 Python 应用（如果在前台运行）
echo "🐍 停止 Python 应用..."
pkill -f "python main.py" 2>/dev/null || true

# 停止 Docker 服务
echo "🐳 停止 Docker 服务..."
docker compose down

echo "✅ 所有服务已停止"
echo ""
echo "📚 其他管理命令："
echo "   查看服务状态: docker compose ps"
echo "   查看日志: docker compose logs"
echo "   重启服务: docker compose restart"
echo "   清理数据: docker compose down -v"
