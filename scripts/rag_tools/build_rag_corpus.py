#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建RAG语料库脚本 (V3 - 推理型语料加载器)
将由 generate_corpus.py 生成的推理型语料加载到向量数据库
"""

import sys
import os
import json
import argparse
from typing import List, Dict, Any
from loguru import logger

# 将项目根目录添加到sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rag_system.storage.chroma_storage import ChromaStorage
from rag_system.models.bio_lm_embedding import BioLMEmbedding
from rag_system.models.embedding_function_adapter import ChromaEmbeddingFunctionAdapter
from configs.system_config import RAG_CONFIG

def load_inferred_corpus(file_path: str) -> List[Dict[str, Any]]:
    """加载推理型语料库JSON文件"""
    logger.info(f"正在加载推理型语料文件: {file_path}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            logger.success(f"成功加载 {len(data)} 条推理语料。")
            return data
        else:
            logger.error(f"文件 {file_path} 内容不是一个JSON列表。")
            return []
    except FileNotFoundError:
        logger.error(f"文件未找到: {file_path}")
        return []
    except Exception as e:
        logger.error(f"加载文件 {file_path} 时发生未知错误: {e}")
        return []

def prepare_documents_from_inferred(corpus: List[Dict[str, Any]]) -> (List[str], List[Dict[str, Any]], List[str]):
    """
    从推理型语料准备用于索引的文档、元数据和ID。
    支持通用器官提取结果。
    """
    logger.info("正在从推理型语料准备索引文档...")
    
    documents = []
    metadatas = []
    ids = []
    
    organ_stats = {'specified': 0, 'other': 0}
    
    for i, item in enumerate(corpus):
        symptom = item.get('symptom_or_disease', '')
        parts = item.get('suggested_anatomical_parts_to_examine', [])
        organ = item.get('inferred_organ', '')
        organ_category = item.get('organ_category', 'unknown')
        
        # 将核心推理信息组合成待向量化的文档
        parts_string = ", ".join(parts)
        content_to_vectorize = f"Symptom: {symptom}. Organ: {organ}. Suggested examination for: {parts_string}."
        
        if not symptom or not parts or not organ:
            logger.warning(f"跳过索引 {i}，因为症状、器官或建议部位为空。")
            continue
        
        # 所有原始信息都成为元数据
        metadata = {str(k): str(v) for k, v in item.items()}
        
        # 创建唯一ID
        unique_id = f"{item.get('case_id', 'caseN_A')}_symptom_{i}"
        
        documents.append(content_to_vectorize)
        metadatas.append(metadata)
        ids.append(unique_id)
        
        # 统计器官类别
        if organ_category in organ_stats:
            organ_stats[organ_category] += 1
        
    logger.success(f"成功准备 {len(documents)} 个文档用于索引。")
    logger.info(f"器官类别统计: 指定器官 {organ_stats['specified']} 条, 其他器官 {organ_stats['other']} 条")
    
    return documents, metadatas, ids

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="从推理型语料构建RAG系统的向量数据库")
    parser.add_argument(
        'corpus_file', 
        type=str,
        help="由generate_corpus.py生成的推理型JSON语料文件路径"
    )
    parser.add_argument(
        '--collection_name', 
        type=str, 
        default=RAG_CONFIG.get("collection_name_inferred", "medical_evidence_inferred"),
        help="在向量数据库中创建的集合（Collection）名称"
    )
    parser.add_argument(
        '--chunk_size', 
        type=int, 
        default=500,
        help="批量处理的文档数量"
    )
    args = parser.parse_args()

    logger.info("🚀 开始构建RAG向量语料库 (从推理型语料)...")
    
    # 1. 加载语料文件
    corpus_data = load_inferred_corpus(args.corpus_file)
    if not corpus_data:
        logger.error("未能加载任何语料数据，程序终止。")
        return
        
    # 2. 准备文档
    documents, metadatas, ids = prepare_documents_from_inferred(corpus_data)
    
    # 3. 初始化嵌入模型
    logger.info("正在初始化嵌入模型 (BioLMEmbedding)...")
    embedding_model = BioLMEmbedding()
    
    # 4. 创建嵌入函数适配器
    logger.info("创建ChromaDB嵌入函数适配器...")
    chroma_embedding_function = ChromaEmbeddingFunctionAdapter(embedding_model)
    
    # 5. 初始化向量数据库
    logger.info(f"正在初始化向量数据库，集合名称: '{args.collection_name}'...")
    vector_store = ChromaStorage(
        collection_name=args.collection_name,
        embedding_function=chroma_embedding_function
    )
    
    # 6. 清空旧数据
    logger.info("正在清空旧的集合（如果存在）...")
    vector_store.reset_collection()
    
    # 7. 分批次添加文档到向量数据库
    logger.info(f"开始向向量数据库中添加 {len(documents)} 个文档...")
    
    total_docs = len(documents)
    for i in range(0, total_docs, args.chunk_size):
        batch_docs = documents[i:i + args.chunk_size]
        batch_metadatas = metadatas[i:i + args.chunk_size]
        batch_ids = ids[i:i + args.chunk_size]
        
        logger.info(f"正在处理批次: {i // args.chunk_size + 1} / {total_docs // args.chunk_size + 1}...")
        
        vector_store.add_documents(
            documents=batch_docs,
            metadatas=batch_metadatas,
            ids=batch_ids
        )
    
    logger.success("🎉🎉🎉 RAG向量语料库构建完成！🎉🎉🎉")
    logger.info(f"总计 {vector_store.count()} 个文档已成功存入集合 '{args.collection_name}'。")

if __name__ == "__main__":
    main() 