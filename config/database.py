import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional
import logging

# 数据库配置
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': os.environ.get('DB_PORT', '5432'),
    'database': os.environ.get('DB_NAME', 'fast_rag'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', 'password'),
}

def get_db_connection():
    """获取数据库连接"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logging.error(f"数据库连接失败: {e}")
        raise

def init_database():
    """初始化数据库和pgvector扩展"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 创建pgvector扩展
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        # 创建 trigram 扩展（用于 BM25 替代的近似匹配/相似度）
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        
        # 创建文档块表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                file_name VARCHAR(255),
                chunk_index INTEGER,
                file_type VARCHAR(50),
                created_at TIMESTAMP DEFAULT NOW(),
                embedding vector(768)
            );
        """)
        
        # 创建向量索引（使用HNSW索引提升性能）
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding 
            ON document_chunks USING hnsw (embedding vector_cosine_ops);
        """)
        
        # 创建文件索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_chunks_file_name 
            ON document_chunks (file_name);
        """)

        # 创建 trigram 索引以支持 content 相似度检索
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_chunks_content_trgm
            ON document_chunks USING GIN (content gin_trgm_ops);
        """)

        # 创建全文检索 tsvector 生成列与 GIN 索引（简单词典，中文可在入库阶段预分词到 content）
        cursor.execute("""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='document_chunks' AND column_name='content_tsv'
                ) THEN
                    ALTER TABLE document_chunks 
                    ADD COLUMN content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED;
                END IF;
            END $$;
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_chunks_tsv
            ON document_chunks USING GIN (content_tsv);
        """)
        
        conn.commit()
        logging.info("数据库初始化完成")
        
    except Exception as e:
        conn.rollback()
        logging.error(f"数据库初始化失败: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def get_chunk_count() -> int:
    """获取文档块总数"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) FROM document_chunks;")
        count = cursor.fetchone()[0]
        return count
    finally:
        cursor.close()
        conn.close()

def clear_all_chunks():
    """清空所有文档块"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM document_chunks;")
        conn.commit()
        logging.info("所有文档块已清空")
    except Exception as e:
        conn.rollback()
        logging.error(f"清空文档块失败: {e}")
        raise
    finally:
        cursor.close()
        conn.close()
