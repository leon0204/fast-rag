-- PostgreSQL + pgvector 初始化脚本
-- 此脚本会在容器启动时自动执行

-- 创建 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 创建文档块表
CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    file_name VARCHAR(255),
    chunk_index INTEGER,
    file_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    embedding vector(768)
);

-- 创建向量索引（使用HNSW索引提升性能）
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding 
ON document_chunks USING hnsw (embedding vector_cosine_ops);

-- 创建文件索引
CREATE INDEX IF NOT EXISTS idx_document_chunks_file_name 
ON document_chunks (file_name);

-- 创建时间索引
CREATE INDEX IF NOT EXISTS idx_document_chunks_created_at 
ON document_chunks (created_at);

-- 创建复合索引
CREATE INDEX IF NOT EXISTS idx_document_chunks_file_chunk 
ON document_chunks (file_name, chunk_index);

-- 设置表空间和参数优化
ALTER TABLE document_chunks SET (
    autovacuum_vacuum_scale_factor = 0.1,
    autovacuum_analyze_scale_factor = 0.05
);

-- 创建统计信息
ANALYZE document_chunks;

-- 输出初始化完成信息
DO $$
BEGIN
    RAISE NOTICE 'PostgreSQL + pgvector 初始化完成！';
    RAISE NOTICE '数据库: fast_rag';
    RAISE NOTICE '用户: postgres';
    RAISE NOTICE '密码: password';
    RAISE NOTICE '端口: 5432';
END $$;
