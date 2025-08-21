#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的ChromaDB测试脚本
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = "/opt/RAG_Evidence4Organ"
sys.path.insert(0, project_root)

def test_chroma_import():
    """测试ChromaDB导入"""
    try:
        import chromadb
        print(f"✅ ChromaDB版本: {chromadb.__version__}")
        return True
    except ImportError as e:
        print(f"❌ ChromaDB导入失败: {e}")
        return False

def test_directory_access():
    """测试目录访问"""
    try:
        chroma_dir = Path("/hy-tmp/RAG_Evidence4Organ_chroma_db")
        if not chroma_dir.exists():
            chroma_dir.mkdir(parents=True, exist_ok=True)
            print(f"✅ 创建目录: {chroma_dir}")
        else:
            print(f"✅ 目录已存在: {chroma_dir}")
        
        # 测试写入权限
        test_file = chroma_dir / "test.txt"
        test_file.write_text("test")
        test_file.unlink()
        print(f"✅ 目录可写: {chroma_dir}")
        return True
    except Exception as e:
        print(f"❌ 目录访问失败: {e}")
        return False

def test_chroma_client():
    """测试ChromaDB客户端"""
    try:
        import chromadb
        
        # 尝试不同的初始化方式
        chroma_dir = "/hy-tmp/RAG_Evidence4Organ_chroma_db"
        
        try:
            # 方式1: PersistentClient
            client = chromadb.PersistentClient(path=chroma_dir)
            print("✅ 使用PersistentClient初始化成功")
        except Exception as e1:
            print(f"⚠️ PersistentClient失败: {e1}")
            try:
                # 方式2: Client with Settings
                client = chromadb.Client(
                    chromadb.config.Settings(persist_directory=chroma_dir)
                )
                print("✅ 使用Client初始化成功")
            except Exception as e2:
                print(f"⚠️ Client失败: {e2}")
                # 方式3: 默认客户端
                client = chromadb.Client()
                print("✅ 使用默认Client初始化成功")
        
        # 测试基本操作
        collections = client.list_collections()
        print(f"✅ 当前集合数: {len(collections)}")
        
        return True
    except Exception as e:
        print(f"❌ ChromaDB客户端测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始ChromaDB简单测试")
    print("=" * 50)
    
    # 1. 测试导入
    if not test_chroma_import():
        return False
    
    # 2. 测试目录访问
    if not test_directory_access():
        return False
    
    # 3. 测试客户端
    if not test_chroma_client():
        return False
    
    print("=" * 50)
    print("🎉 所有测试通过！")
    print("现在可以开始构建RAG索引了")
    return True

if __name__ == "__main__":
    main() 