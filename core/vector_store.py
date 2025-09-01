import logging
from typing import List, Dict, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
import ollama
import torch

from config.database import get_db_connection


class VectorStore:
    def __init__(self):
        self.embedding_model = 'nomic-embed-text'
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """生成文本向量嵌入"""
        if not texts:
            return []
        
        vectors: List[List[float]] = []
        for content in texts:
            try:
                resp = ollama.embeddings(model=self.embedding_model, prompt=content)
                # 确保向量是浮点数列表
                embedding = [float(x) for x in resp["embedding"]]
                vectors.append(embedding)
            except Exception as e:
                logging.error(f"生成向量嵌入失败: {e}")
                raise
        
        return vectors
    
    def store_chunks(self, chunks: List[str], file_name: str, file_type: str = "unknown") -> int:
        """存储文档块到数据库"""
        if not chunks:
            return 0
        
        # 生成向量嵌入
        embeddings = self.embed_texts(chunks)
        
        # 批量插入数据库
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 准备批量插入数据
            data_to_insert = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                # 将向量转换为PostgreSQL的vector类型
                embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                data_to_insert.append((chunk, file_name, i, file_type, embedding_str))
            
            # 批量插入
            cursor.executemany("""
                INSERT INTO document_chunks (content, file_name, chunk_index, file_type, embedding)
                VALUES (%s, %s, %s, %s, %s::vector)
            """, data_to_insert)
            
            conn.commit()
            inserted_count = len(chunks)
            logging.info(f"成功存储 {inserted_count} 个文档块，文件: {file_name}")
            return inserted_count
            
        except Exception as e:
            conn.rollback()
            logging.error(f"存储文档块失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def search_similar(self, query_embedding: List[float], top_k: int = 3) -> List[Dict]:
        """搜索相似文档块"""
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # 将查询向量转换为PostgreSQL的vector类型
            query_vector_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            # 使用余弦相似度搜索
            cursor.execute("""
                SELECT id, content, file_name, chunk_index, file_type,
                       embedding <=> %s::vector as distance
                FROM document_chunks
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (query_vector_str, query_vector_str, top_k))
            
            results = cursor.fetchall()
            return [dict(row) for row in results]
            
        except Exception as e:
            logging.error(f"搜索相似文档失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def get_all_chunks(self) -> List[Dict]:
        """获取所有文档块（用于兼容性）"""
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute("""
                SELECT id, content, file_name, chunk_index, file_type, created_at
                FROM document_chunks
                ORDER BY file_name, chunk_index
            """)
            
            results = cursor.fetchall()
            return [dict(row) for row in results]
            
        except Exception as e:
            logging.error(f"获取所有文档块失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def delete_file_chunks(self, file_name: str) -> int:
        """删除指定文件的所有文档块"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM document_chunks WHERE file_name = %s", (file_name,))
            deleted_count = cursor.rowcount
            conn.commit()
            logging.info(f"删除文件 {file_name} 的 {deleted_count} 个文档块")
            return deleted_count
            
        except Exception as e:
            conn.rollback()
            logging.error(f"删除文件文档块失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def get_file_list(self) -> List[Dict]:
        """获取已上传文件列表"""
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute("""
                SELECT file_name, file_type, COUNT(*) as chunk_count, 
                       MIN(created_at) as first_upload, MAX(created_at) as last_upload
                FROM document_chunks
                GROUP BY file_name, file_type
                ORDER BY last_upload DESC
            """)
            
            results = cursor.fetchall()
            return [dict(row) for row in results]
            
        except Exception as e:
            logging.error(f"获取文件列表失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def get_chunks_by_file(self, file_name: str, limit: int = 100, offset: int = 0, preview_length: int = 200) -> List[Dict]:
        """按文件名获取文档块，支持分页与预览长度（preview_length>0 时返回预览字段）"""
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            if preview_length and preview_length > 0:
                cursor.execute(
                    """
                    SELECT id, file_name, file_type, chunk_index, created_at,
                           LENGTH(content) AS content_length,
                           LEFT(content, %s) AS content_preview
                    FROM document_chunks
                    WHERE file_name = %s
                    ORDER BY chunk_index
                    LIMIT %s OFFSET %s
                    """,
                    (preview_length, file_name, limit, offset),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, file_name, file_type, chunk_index, created_at, content,
                           LENGTH(content) AS content_length
                    FROM document_chunks
                    WHERE file_name = %s
                    ORDER BY chunk_index
                    LIMIT %s OFFSET %s
                    """,
                    (file_name, limit, offset),
                )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logging.error(f"获取文件 {file_name} 的chunk失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def get_chunk_count_by_file(self, file_name: str) -> int:
        """获取某个文件的chunk总数"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM document_chunks WHERE file_name = %s", (file_name,))
            return int(cursor.fetchone()[0])
        except Exception as e:
            logging.error(f"统计文件 {file_name} 的chunk数量失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def search_chunks_in_file(self, file_name: str, keyword: str, limit: int = 50, offset: int = 0, preview_length: int = 200) -> List[Dict]:
        """在指定文件内按关键字搜索content，ILIKE模糊匹配，支持分页与预览长度"""
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            pattern = f"%{keyword}%"
            if preview_length and preview_length > 0:
                cursor.execute(
                    """
                    SELECT id, file_name, file_type, chunk_index, created_at,
                           LENGTH(content) AS content_length,
                           LEFT(content, %s) AS content_preview
                    FROM document_chunks
                    WHERE file_name = %s AND content ILIKE %s
                    ORDER BY chunk_index
                    LIMIT %s OFFSET %s
                    """,
                    (preview_length, file_name, pattern, limit, offset),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, file_name, file_type, chunk_index, created_at, content,
                           LENGTH(content) AS content_length
                    FROM document_chunks
                    WHERE file_name = %s AND content ILIKE %s
                    ORDER BY chunk_index
                    LIMIT %s OFFSET %s
                    """,
                    (file_name, pattern, limit, offset),
                )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logging.error(f"文件内关键字搜索失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()


# 全局向量存储实例
vector_store = VectorStore()
