#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试ChromaDB配置脚本
验证新的数据盘存储路径是否正常工作
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = "/opt/RAG_Evidence4Organ"
sys.path.insert(0, project_root)

from configs.system_config import get_config
from rag_system.storage.chroma_storage import create_chroma_storage
from loguru import logger

def test_chroma_config():
    """测试ChromaDB配置"""
    logger.info("🧪 测试ChromaDB配置...")
    
    # 1. 检查配置
    rag_config = get_config("rag")
    persist_directory = rag_config["persist_directory"]
    collection_name = rag_config["collection_name"]
    
    logger.info(f"配置的存储路径: {persist_directory}")
    logger.info(f"集合名称: {collection_name}")
    
    # 2. 检查目录是否存在
    if not persist_directory.exists():
        logger.warning(f"存储目录不存在，正在创建: {persist_directory}")
        persist_directory.mkdir(parents=True, exist_ok=True)
    else:
        logger.success(f"存储目录已存在: {persist_directory}")
    
    # 3. 检查目录权限
    if os.access(persist_directory, os.W_OK):
        logger.success(f"目录可写: {persist_directory}")
    else:
        logger.error(f"目录不可写: {persist_directory}")
        return False
    
    # 4. 测试ChromaDB初始化 - 使用0.5.x版本的API
    try:
        logger.info("初始化ChromaDB存储...")
        storage = create_chroma_storage(
            persist_directory=str(persist_directory),
            collection_name=collection_name
        )
        logger.success("ChromaDB初始化成功！")
        
        # 5. 测试基本操作
        logger.info("测试基本操作...")
        
        # 检查集合信息
        info = storage.get_collection_info()
        logger.info(f"集合信息: {info}")
        
        # 检查记录数量
        count = storage.count()
        logger.info(f"当前记录数: {count}")
        
        return True
        
    except Exception as e:
        logger.error(f"ChromaDB初始化失败: {e}")
        return False

def estimate_storage_size():
    """估算存储空间需求"""
    logger.info("📊 估算存储空间需求...")
    
    # 假设174,712条记录
    total_records = 174712
    
    # 每条记录的存储需求（估算）
    # - 768维向量: 768 * 4 bytes = 3,072 bytes
    # - 文档文本: ~500 bytes
    # - 元数据: ~200 bytes
    # - 索引开销: ~1,000 bytes
    # 总计: ~4,772 bytes per record
    
    bytes_per_record = 4772
    total_bytes = total_records * bytes_per_record
    total_mb = total_bytes / (1024 * 1024)
    total_gb = total_mb / 1024
    
    logger.info(f"总记录数: {total_records:,}")
    logger.info(f"估算存储空间: {total_mb:.1f} MB ({total_gb:.2f} GB)")
    
    # 检查可用空间
    import shutil
    total, used, free = shutil.disk_usage("/hy-tmp")
    free_gb = free / (1024**3)
    
    logger.info(f"数据盘可用空间: {free_gb:.1f} GB")
    
    if free_gb > total_gb * 2:  # 预留2倍空间
        logger.success("✅ 存储空间充足")
        return True
    else:
        logger.warning("⚠️ 存储空间可能不足")
        return False

def main():
    """主函数"""
    logger.info("🚀 开始ChromaDB配置测试")
    
    # 1. 估算存储空间
    space_ok = estimate_storage_size()
    
    # 2. 测试配置
    config_ok = test_chroma_config()
    
    if space_ok and config_ok:
        logger.success("🎉 所有测试通过！可以开始构建RAG索引")
        logger.info("下一步操作:")
        logger.info("1. 运行: python -m RAG_Evidence4Organ.rag_system.build_rag_index")
        logger.info("2. 或运行: bash /opt/RAG_Evidence4Organ/rag_system/start_indexing.sh")
    else:
        logger.error("❌ 测试失败，请检查配置")
        return False
    
    return True

if __name__ == "__main__":
    main() 