#!/usr/bin/env python3
"""
启动FastAPI应用并测试历史记录功能
"""

import subprocess
import time
import requests
import json
import os

def start_server():
    """启动FastAPI服务器"""
    print("🚀 启动FastAPI服务器...")
    
    # 检查是否已经有服务器在运行
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            print("✅ 服务器已经在运行")
            return True
    except:
        pass
    
    # 启动服务器
    try:
        process = subprocess.Popen(
            ["python", "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # 等待服务器启动
        print("⏳ 等待服务器启动...")
        for i in range(30):  # 最多等待30秒
            try:
                response = requests.get("http://localhost:8000/health", timeout=2)
                if response.status_code == 200:
                    print("✅ 服务器启动成功!")
                    return True
            except:
                pass
            time.sleep(1)
            if i % 5 == 0:
                print(f"⏳ 等待中... ({i+1}/30)")
        
        print("❌ 服务器启动超时")
        return False
        
    except Exception as e:
        print(f"❌ 启动服务器失败: {e}")
        return False

def test_history_api():
    """测试历史记录API"""
    print("\n🧪 测试历史记录API...")
    
    base_url = "http://localhost:8000"
    
    # 1. 测试获取历史记录列表
    print("📋 测试获取历史记录列表...")
    try:
        response = requests.get(f"{base_url}/history/list")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功获取 {len(data)} 条历史记录")
            if data:
                print(f"示例记录: {json.dumps(data[0], ensure_ascii=False, indent=2)}")
        else:
            print(f"❌ 获取失败: {response.text}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    # 2. 测试获取统计信息
    print("\n📊 测试获取统计信息...")
    try:
        response = requests.get(f"{base_url}/history/stats")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 统计信息: {json.dumps(data, ensure_ascii=False, indent=2)}")
        else:
            print(f"❌ 获取失败: {response.text}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    # 3. 测试发送聊天消息
    print("\n💬 测试发送聊天消息...")
    try:
        session_id = f"test_session_{int(time.time())}"
        response = requests.post(
            f"{base_url}/chat/stream",
            data={"query": "这是一个测试消息，用于验证历史记录功能", "session_id": session_id}
        )
        print(f"聊天响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 聊天消息发送成功")
            
            # 等待历史记录保存
            print("⏳ 等待历史记录保存...")
            time.sleep(3)
            
            # 检查历史记录是否保存
            print("🔍 检查历史记录是否保存...")
            history_response = requests.get(f"{base_url}/history/list")
            if history_response.status_code == 200:
                history_data = history_response.json()
                found_session = False
                for session in history_data:
                    if session["id"] == session_id:
                        found_session = True
                        print(f"✅ 找到测试会话: {json.dumps(session, ensure_ascii=False, indent=2)}")
                        break
                
                if not found_session:
                    print("❌ 未找到测试会话")
            else:
                print(f"❌ 获取历史记录失败: {history_response.status_code}")
        else:
            print(f"❌ 聊天消息发送失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def main():
    """主函数"""
    print("=" * 60)
    print("FastRAG 历史记录功能测试")
    print("=" * 60)
    
    # 检查必要文件
    required_files = ["main.py", "api/history.py", "api/chat.py"]
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"❌ 缺少必要文件: {file_path}")
            return
    
    print("✅ 所有必要文件检查通过")
    
    # 启动服务器
    if not start_server():
        print("❌ 无法启动服务器，测试终止")
        return
    
    # 测试API
    test_history_api()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n📝 使用说明:")
    print("1. 服务器已启动在 http://localhost:8000")
    print("2. 访问 http://localhost:8000/docs 查看API文档")
    print("3. 前端应用可以调用 /history/list 等接口")
    print("4. 所有聊天记录会自动保存到 chat_history.db")
    print("\n按 Ctrl+C 停止服务器")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 测试已停止")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
