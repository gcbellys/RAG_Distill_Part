#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG系统运行脚本
用于构建和运行医学证据检索系统
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
from loguru import logger

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from rag_system.models.bio_lm_embedding import create_bio_lm_embedding
from rag_system.models.bge_embedding import create_bge_embedding
from rag_system.storage.chroma_storage import create_chroma_storage
from configs.system_config import get_config, get_data_path, ensure_directories
from configs.model_config import get_embedding_model

def setup_logging():
    """设置日志"""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # 添加文件日志
    log_file = project_root / "logs" / "rag_system.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days"
    )

def load_rag_corpus(corpus_file: str) -> List[Dict[str, Any]]:
    """加载RAG语料"""
    try:
        with open(corpus_file, 'r', encoding='utf-8') as f:
            corpus = json.load(f)
        
        logger.info(f"成功加载 {len(corpus)} 条RAG语料")
        return corpus
        
    except Exception as e:
        logger.error(f"加载RAG语料失败: {e}")
        return []

def create_embedding_model(model_name: str = "bio_lm"):
    """创建嵌入模型"""
    if model_name == "bio_lm":
        return create_bio_lm_embedding()
    elif model_name.startswith("bge"):
        return create_bge_embedding(model_name="BAAI/bge-large-zh-v1.5")
    else:
        raise ValueError(f"不支持的模型类型: {model_name}")

def build_vector_database(corpus_file: str,
                         model_name: str = "bio_lm",
                         persist_directory: str = "./chroma_db",
                         collection_name: str = "medical_evidence") -> None:
    """
    构建向量数据库
    
    Args:
        corpus_file: RAG语料文件
        model_name: 嵌入模型名称
        persist_directory: 持久化目录
        collection_name: 集合名称
    """
    logger.info("开始构建向量数据库")
    logger.info(f"语料文件: {corpus_file}")
    logger.info(f"使用模型: {model_name}")
    
    # 加载语料
    corpus = load_rag_corpus(corpus_file)
    if not corpus:
        logger.error("没有可用的语料")
        return
    
    # 创建嵌入模型
    logger.info("初始化嵌入模型...")
    embedding_model = create_embedding_model(model_name)
    
    # 创建存储
    logger.info("初始化ChromaDB存储...")
    storage = create_chroma_storage(
        persist_directory=persist_directory,
        collection_name=collection_name
    )
    
    # 准备数据
    logger.info("准备数据...")
    documents = []
    metadatas = []
    ids = []
    
    for i, item in enumerate(corpus):
        # 使用document字段作为文档内容
        doc_text = item.get("document", "")
        if not doc_text:
            continue
        
        documents.append(doc_text)
        
        # 构建元数据
        metadata = {
            "case_id": item.get("case_id", ""),
            "disease_symptom": item.get("disease_symptom", ""),
            "organ": item.get("organ", ""),
            "specific_part": item.get("specific_part", ""),
            "confidence": item.get("confidence", ""),
            "specialty": item.get("specialty", ""),
            "query": item.get("query", "")
        }
        metadatas.append(metadata)
        
        # 生成ID
        doc_id = f"doc_{i:06d}"
        ids.append(doc_id)
    
    logger.info(f"准备添加 {len(documents)} 个文档")
    
    # 计算嵌入向量
    logger.info("计算嵌入向量...")
    embeddings = embedding_model.encode(documents, batch_size=32)
    
    # 添加到数据库
    logger.info("添加到向量数据库...")
    storage.add_embeddings(
        embeddings=embeddings.tolist(),
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    
    # 显示统计信息
    collection_info = storage.get_collection_info()
    logger.info("=" * 50)
    logger.info("向量数据库构建完成！")
    logger.info(f"集合名称: {collection_info.get('name', 'unknown')}")
    logger.info(f"文档数量: {collection_info.get('count', 0)}")
    logger.info(f"嵌入维度: {embedding_model.get_embedding_dimension()}")
    logger.info(f"持久化目录: {persist_directory}")

def test_search(corpus_file: str,
                model_name: str = "bio_lm",
                persist_directory: str = "./chroma_db",
                collection_name: str = "medical_evidence") -> None:
    """测试搜索功能"""
    logger.info("测试搜索功能")
    
    # 创建嵌入模型
    embedding_model = create_embedding_model(model_name)
    
    # 创建存储
    storage = create_chroma_storage(
        persist_directory=persist_directory,
        collection_name=collection_name
    )
    
    # 测试查询
    test_queries = [
        "chest pain",
        "liver function abnormality",
        "thyroid nodule",
        "dyspnea"
    ]
    
    for query in test_queries:
        logger.info(f"\n查询: '{query}'")
        
        try:
            results = storage.query(
                query_texts=query,
                n_results=3
            )
            
            if results["documents"] and results["documents"][0]:
                for i, (doc, metadata) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
                    logger.info(f"  {i+1}. 相似度: {results['distances'][0][i]:.4f}")
                    logger.info(f"     症状: {metadata.get('disease_symptom', '未知')}")
                    logger.info(f"     器官: {metadata.get('organ', '未知')}")
                    logger.info(f"     部位: {metadata.get('specific_part', '未知')}")
                    logger.info(f"     文档: {doc[:50]}...")
            else:
                logger.info("  没有找到相关结果")
                
        except Exception as e:
            logger.error(f"查询失败: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="RAG系统")
    parser.add_argument("--corpus", "-c", required=True, help="RAG语料文件")
    parser.add_argument("--model", "-m", default="bio_lm", help="嵌入模型类型")
    parser.add_argument("--persist-dir", default="./chroma_db", help="持久化目录")
    parser.add_argument("--collection", default="medical_evidence", help="集合名称")
    parser.add_argument("--test", action="store_true", help="测试搜索功能")
    parser.add_argument("--build", action="store_true", help="构建向量数据库")
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging()
    
    # 确保目录存在
    ensure_directories()
    
    # 检查语料文件
    if not os.path.exists(args.corpus):
        logger.error(f"语料文件不存在: {args.corpus}")
        return
    
    try:
        if args.build:
            # 构建向量数据库
            build_vector_database(
                corpus_file=args.corpus,
                model_name=args.model,
                persist_directory=args.persist_dir,
                collection_name=args.collection
            )
        
        if args.test:
            # 测试搜索功能
            test_search(
                corpus_file=args.corpus,
                model_name=args.model,
                persist_directory=args.persist_dir,
                collection_name=args.collection
            )
        
        if not args.build and not args.test:
            # 默认构建数据库
            build_vector_database(
                corpus_file=args.corpus,
                model_name=args.model,
                persist_directory=args.persist_dir,
                collection_name=args.collection
            )
            
    except KeyboardInterrupt:
        logger.info("用户中断处理")
    except Exception as e:
        logger.error(f"处理失败: {e}")
        raise

if __name__ == "__main__":
    main() 