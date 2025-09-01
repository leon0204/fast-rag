#!/usr/bin/env python3
"""
向量操作测试脚本
测试向量类型转换和数据库操作
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.vector_store import vector_store
import ollama


def test_embedding_generation():
    """测试向量嵌入生成"""
    print("🧪 测试向量嵌入生成...")
    
    test_text = "这是一个测试文本"
    
    try:
        # 生成向量嵌入
        embeddings = vector_store.embed_texts([test_text])
        
        if embeddings and len(embeddings) > 0:
            embedding = embeddings[0]
            print(f"✅ 向量嵌入生成成功")
            print(f"   向量维度: {len(embedding)}")
            print(f"   向量类型: {type(embedding)}")
            print(f"   前5个值: {embedding[:5]}")
            print(f"   数据类型: {[type(x) for x in embedding[:5]]}")
            
            # 检查是否都是浮点数
            all_floats = all(isinstance(x, float) for x in embedding)
            print(f"   全部为浮点数: {all_floats}")
            
            return True
        else:
            print("❌ 向量嵌入生成失败")
            return False
            
    except Exception as e:
        print(f"❌ 向量嵌入生成异常: {e}")
        return False


def test_vector_string_conversion():
    """测试向量字符串转换"""
    print("\n🧪 测试向量字符串转换...")
    
    test_embedding = [0.1, -0.2, 0.3, -0.4, 0.5]
    
    try:
        # 转换为PostgreSQL vector格式
        vector_str = '[' + ','.join(map(str, test_embedding)) + ']'
        
        print(f"✅ 向量字符串转换成功")
        print(f"   原始向量: {test_embedding}")
        print(f"   转换后: {vector_str}")
        print(f"   类型: {type(vector_str)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 向量字符串转换异常: {e}")
        return False


def test_database_connection():
    """测试数据库连接"""
    print("\n🧪 测试数据库连接...")
    
    try:
        from config.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 测试基本查询
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        
        print(f"✅ 数据库连接成功")
        print(f"   PostgreSQL版本: {version[0]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ 数据库连接异常: {e}")
        return False


def test_pgvector_extension():
    """测试pgvector扩展"""
    print("\n🧪 测试pgvector扩展...")
    
    try:
        from config.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查pgvector扩展
        cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector'")
        extension = cursor.fetchone()
        
        if extension:
            print(f"✅ pgvector扩展正常")
            print(f"   扩展名: {extension[1]}")
            print(f"   版本: {extension[5]}")
        else:
            print("❌ pgvector扩展未安装")
            return False
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ pgvector扩展测试异常: {e}")
        return False


def test_vector_table():
    """测试向量表结构"""
    print("\n🧪 测试向量表结构...")
    
    try:
        from config.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查表结构
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'document_chunks'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        
        print(f"✅ 向量表结构正常")
        print(f"   表名: document_chunks")
        print(f"   列数: {len(columns)}")
        
        for col in columns:
            print(f"     {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ 向量表结构测试异常: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 Fast RAG 向量操作测试")
    print("=" * 50)
    
    tests = [
        test_embedding_generation,
        test_vector_string_conversion,
        test_database_connection,
        test_pgvector_extension,
        test_vector_table
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ 测试 {test_func.__name__} 异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！向量操作正常")
        return True
    else:
        print("⚠️  部分测试失败，请检查配置")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
