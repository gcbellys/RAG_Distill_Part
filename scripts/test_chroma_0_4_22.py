#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChromaDB 0.4.22版本测试脚本
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = "/opt/RAG_Evidence4Organ"
sys.path.insert(0, project_root)

def test_chroma_0_4_22():
    """测试ChromaDB 0.4.22版本"""
    try:
        import chromadb
        print(f"✅ ChromaDB版本: {chromadb.__version__}")
        
        # 创建测试目录
        test_dir = "/hy-tmp/RAG_Evidence4Organ_chroma_db"
        os.makedirs(test_dir, exist_ok=True)
        print(f"✅ 测试目录: {test_dir}")
        
        # 测试1: 初始化客户端
        print("\n=== 测试1: 初始化客户端 ===")
        try:
            client = chromadb.PersistentClient(path=test_dir)
            print("✅ PersistentClient初始化成功")
        except Exception as e:
            print(f"❌ PersistentClient失败: {e}")
            return False
        
        # 测试2: 列出集合
        print("\n=== 测试2: 列出集合 ===")
        try:
            collections = client.list_collections()
            print(f"✅ 当前集合数: {len(collections)}")
        except Exception as e:
            print(f"❌ 列出集合失败: {e}")
            return False
        
        # 测试3: 创建测试集合
        print("\n=== 测试3: 创建测试集合 ===")
        try:
            test_collection = client.create_collection(
                name="test_collection",
                metadata={"description": "测试集合"}
            )
            print("✅ 测试集合创建成功")
        except Exception as e:
            print(f"❌ 创建集合失败: {e}")
            return False
        
        # 测试4: 添加文档
        print("\n=== 测试4: 添加文档 ===")
        try:
            test_collection.add(
                documents=["这是一个测试文档"],
                metadatas=[{"source": "test"}],
                ids=["test_1"]
            )
            print("✅ 文档添加成功")
        except Exception as e:
            print(f"❌ 添加文档失败: {e}")
            return False
        
        # 测试5: 查询文档
        print("\n=== 测试5: 查询文档 ===")
        try:
            results = test_collection.query(
                query_texts=["测试"],
                n_results=1
            )
            print(f"✅ 查询成功，返回 {len(results['documents'][0])} 个结果")
        except Exception as e:
            print(f"❌ 查询失败: {e}")
            return False
        
        # 测试6: 删除测试集合
        print("\n=== 测试6: 删除测试集合 ===")
        try:
            client.delete_collection(name="test_collection")
            print("✅ 测试集合删除成功")
        except Exception as e:
            print(f"❌ 删除集合失败: {e}")
            return False
        
        return True
        
    except ImportError as e:
        print(f"❌ ChromaDB导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始ChromaDB 0.4.22版本测试")
    print("=" * 50)
    
    if test_chroma_0_4_22():
        print("=" * 50)
        print("🎉 所有测试通过！")
        print("ChromaDB 0.4.22版本配置成功")
        print("\n下一步:")
        print("1. 构建RAG索引: python -m rag_system.build_rag_index")
        print("2. 或后台运行: bash /opt/RAG_Evidence4Organ/rag_system/start_indexing.sh")
    else:
        print("=" * 50)
        print("❌ 测试失败，请检查ChromaDB配置")

if __name__ == "__main__":
    main() 