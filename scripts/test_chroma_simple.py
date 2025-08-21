#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的ChromaDB测试脚本 - 适配0.5.x版本
"""

import sys
import os
from pathlib import Path

def test_chroma_basic():
    """测试ChromaDB基本功能"""
    try:
        import chromadb
        print(f"✅ ChromaDB版本: {chromadb.__version__}")
        
        # 创建测试目录
        test_dir = "/hy-tmp/RAG_Evidence4Organ_chroma_db"
        os.makedirs(test_dir, exist_ok=True)
        print(f"✅ 测试目录: {test_dir}")
        
        # 使用ChromaDB 0.5.x的正确初始化方式
        try:
            client = chromadb.PersistentClient(path=test_dir)
            print("✅ PersistentClient初始化成功")
        except Exception as e:
            print(f"❌ PersistentClient失败: {e}")
            return False
        
        # 测试集合操作
        try:
            # 列出集合
            collections = client.list_collections()
            print(f"✅ 当前集合数: {len(collections)}")
            
            # 创建测试集合
            test_collection = client.create_collection(
                name="test_collection",
                metadata={"description": "测试集合"}
            )
            print("✅ 测试集合创建成功")
            
            # 删除测试集合
            client.delete_collection(name="test_collection")
            print("✅ 测试集合删除成功")
            
            return True
            
        except Exception as e:
            print(f"❌ 集合操作失败: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ ChromaDB导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始ChromaDB基本测试")
    print("=" * 40)
    
    if test_chroma_basic():
        print("=" * 40)
        print("🎉 测试通过！可以开始构建RAG索引")
        print("下一步:")
        print("1. python -m RAG_Evidence4Organ.rag_system.build_rag_index")
        print("2. 或 bash /opt/RAG_Evidence4Organ/rag_system/start_indexing.sh")
    else:
        print("=" * 40)
        print("❌ 测试失败，请检查ChromaDB安装")

if __name__ == "__main__":
    main() 