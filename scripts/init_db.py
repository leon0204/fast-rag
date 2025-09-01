#!/usr/bin/env python3
"""
数据库初始化脚本
用于创建PostgreSQL数据库和pgvector扩展
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import DB_CONFIG, init_database


def create_database_if_not_exists():
    """创建数据库（如果不存在）"""
    # 连接到默认的postgres数据库
    conn_params = DB_CONFIG.copy()
    conn_params['database'] = 'postgres'
    
    try:
        conn = psycopg2.connect(**conn_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # 检查数据库是否存在
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_CONFIG['database'],))
        exists = cursor.fetchone()
        
        if not exists:
            print(f"创建数据库: {DB_CONFIG['database']}")
            cursor.execute(f"CREATE DATABASE {DB_CONFIG['database']}")
            print("✅ 数据库创建成功")
        else:
            print(f"✅ 数据库 {DB_CONFIG['database']} 已存在")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ 创建数据库失败: {e}")
        print("请确保PostgreSQL服务正在运行，且用户有创建数据库的权限")
        sys.exit(1)


def main():
    print("=" * 50)
    print("🗄️  PostgreSQL + pgvector 数据库初始化")
    print("=" * 50)
    
    # 1. 创建数据库
    print("\n1. 检查/创建数据库...")
    create_database_if_not_exists()
    
    # 2. 初始化表和扩展
    print("\n2. 初始化pgvector扩展和表结构...")
    try:
        init_database()
        print("✅ 数据库初始化完成")
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        print("请确保已安装pgvector扩展")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("🎉 数据库初始化成功！")
    print("=" * 50)
    print("\n下一步：")
    print("1. 启动应用: python main.py")
    print("2. 上传文档: POST /upload")
    print("3. 开始对话: POST /chat/stream")


if __name__ == "__main__":
    main()
