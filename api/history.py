from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
import sqlite3
import os
from datetime import datetime
import json

router = APIRouter(prefix="/history", tags=["history"])

# 数据库文件路径
HISTORY_DB_PATH = "chat_history.db"

def init_history_db():
    """初始化历史记录数据库"""
    conn = sqlite3.connect(HISTORY_DB_PATH)
    cursor = conn.cursor()
    
    # 创建聊天会话表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            message_count INTEGER DEFAULT 0
        )
    ''')
    
    # 创建聊天消息表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT CHECK(role IN ('user', 'assistant')),
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
        )
    ''')
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_id ON chat_messages (session_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_updated_at ON chat_sessions (updated_at)')
    
    conn.commit()
    conn.close()

def save_chat_message(session_id: str, role: str, content: str):
    """保存聊天消息到数据库"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查会话是否存在，如果不存在则创建
        cursor.execute('''
            INSERT OR IGNORE INTO chat_sessions (id, title, created_at, updated_at, message_count)
            VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0)
        ''', (session_id, None))
        
        # 插入消息
        cursor.execute('''
            INSERT INTO chat_messages (session_id, role, content, timestamp)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (session_id, role, content))
        
        # 更新会话的消息数量和最后更新时间
        cursor.execute('''
            UPDATE chat_sessions 
            SET message_count = (
                SELECT COUNT(*) FROM chat_messages WHERE session_id = ?
            ), updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (session_id, session_id))
        
        # 如果没有标题，使用第一条用户消息作为标题
        cursor.execute('''
            SELECT title FROM chat_sessions WHERE id = ?
        ''', (session_id,))
        current_title = cursor.fetchone()[0]
        
        if not current_title:
            cursor.execute('''
                SELECT content FROM chat_messages 
                WHERE session_id = ? AND role = 'user' 
                ORDER BY timestamp ASC LIMIT 1
            ''', (session_id,))
            first_msg = cursor.fetchone()
            if first_msg:
                title = first_msg[0][:50] + "..." if len(first_msg[0]) > 50 else first_msg[0]
                cursor.execute('''
                    UPDATE chat_sessions SET title = ? WHERE id = ?
                ''', (title, session_id))
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_db_connection():
    """获取数据库连接"""
    return sqlite3.connect(HISTORY_DB_PATH)

@router.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    init_history_db()

@router.get("/list")
async def get_chat_history(
    query: Optional[str] = Query(None, description="搜索关键词"),
    limit: int = Query(50, ge=1, le=200, description="返回数量上限"),
    offset: int = Query(0, ge=0, description="偏移量")
) -> List[Dict]:
    """获取聊天历史记录列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 构建查询SQL
        if query:
            sql = '''
                SELECT DISTINCT cs.id, cs.title, cs.updated_at, cs.message_count
                FROM chat_sessions cs
                JOIN chat_messages cm ON cs.id = cm.session_id
                WHERE cs.title LIKE ? OR cm.content LIKE ?
                ORDER BY cs.updated_at DESC
                LIMIT ? OFFSET ?
            '''
            search_param = f"%{query}%"
            cursor.execute(sql, (search_param, search_param, limit, offset))
        else:
            sql = '''
                SELECT id, title, updated_at, message_count
                FROM chat_sessions
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            '''
            cursor.execute(sql, (limit, offset))
        
        rows = cursor.fetchall()
        
        # 格式化返回数据
        history_list = []
        for row in rows:
            session_id, title, updated_at, message_count = row
            
            # 如果没有标题，使用第一条用户消息作为标题
            if not title:
                cursor.execute('''
                    SELECT content FROM chat_messages 
                    WHERE session_id = ? AND role = 'user' 
                    ORDER BY timestamp ASC LIMIT 1
                ''', (session_id,))
                first_msg = cursor.fetchone()
                title = first_msg[0][:50] + "..." if first_msg and len(first_msg[0]) > 50 else (first_msg[0] if first_msg else "新对话")
            
            history_list.append({
                "id": session_id,
                "title": title,
                "updated_at": updated_at,
                "message_count": message_count
            })
        
        conn.close()
        return history_list
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取聊天历史失败: {str(e)}")

@router.get("/session/{session_id}")
async def get_session_messages(
    session_id: str,
    limit: int = Query(100, ge=1, le=500, description="返回消息数量上限"),
    offset: int = Query(0, ge=0, description="偏移量")
) -> Dict:
    """获取指定会话的聊天消息"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取会话信息
        cursor.execute('''
            SELECT id, title, created_at, updated_at, message_count
            FROM chat_sessions
            WHERE id = ?
        ''', (session_id,))
        
        session = cursor.fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 获取消息列表
        cursor.execute('''
            SELECT role, content, timestamp
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
            LIMIT ? OFFSET ?
        ''', (session_id, limit, offset))
        
        messages = []
        for row in cursor.fetchall():
            role, content, timestamp = row
            messages.append({
                "role": role,
                "content": content,
                "timestamp": timestamp
            })
        
        conn.close()
        
        return {
            "session_id": session_id,
            "title": session[1],
            "created_at": session[2],
            "updated_at": session[3],
            "message_count": session[4],
            "messages": messages,
            "limit": limit,
            "offset": offset
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话消息失败: {str(e)}")

@router.delete("/session/{session_id}")
async def delete_session(session_id: str) -> Dict:
    """删除指定的聊天会话"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 删除会话消息
        cursor.execute('DELETE FROM chat_messages WHERE session_id = ?', (session_id,))
        
        # 删除会话
        cursor.execute('DELETE FROM chat_sessions WHERE id = ?', (session_id,))
        
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        if deleted_count == 0:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return {
            "message": f"成功删除会话 {session_id}",
            "deleted_messages": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")

@router.delete("/all")
async def clear_all_history() -> Dict:
    """清空所有聊天历史记录"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 删除所有消息
        cursor.execute('DELETE FROM chat_messages')
        message_count = cursor.rowcount
        
        # 删除所有会话
        cursor.execute('DELETE FROM chat_sessions')
        session_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return {
            "message": "成功清空所有聊天历史",
            "deleted_sessions": session_count,
            "deleted_messages": message_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空历史记录失败: {str(e)}")

@router.get("/stats")
async def get_history_stats() -> Dict:
    """获取聊天历史统计信息"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 总会话数
        cursor.execute('SELECT COUNT(*) FROM chat_sessions')
        total_sessions = cursor.fetchone()[0]
        
        # 总消息数
        cursor.execute('SELECT COUNT(*) FROM chat_messages')
        total_messages = cursor.fetchone()[0]
        
        # 用户消息数
        cursor.execute('SELECT COUNT(*) FROM chat_messages WHERE role = "user"')
        user_messages = cursor.fetchone()[0]
        
        # AI消息数
        cursor.execute('SELECT COUNT(*) FROM chat_messages WHERE role = "assistant"')
        ai_messages = cursor.fetchone()[0]
        
        # 最近活跃时间
        cursor.execute('SELECT MAX(updated_at) FROM chat_sessions')
        last_activity = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "user_messages": user_messages,
            "ai_messages": ai_messages,
            "last_activity": last_activity
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")
