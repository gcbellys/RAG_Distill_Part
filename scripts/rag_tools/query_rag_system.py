#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG系统查询脚本
接收文本查询，从向量数据库中检索相关医学证据
"""

import os
import sys
import argparse
from typing import List, Dict, Any
from loguru import logger
import pprint
from collections import defaultdict
import json

# Restore the original sys.path modification
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rag_system.storage.chroma_storage import ChromaStorage
from rag_system.models.bio_lm_embedding import BioLMEmbedding
from rag_system.models.embedding_function_adapter import ChromaEmbeddingFunctionAdapter
from knowledge_distillation.extractors.llm_extractor import LLMExtractor
from configs.system_config import RAG_CONFIG, API_KEYS

class RAGQuerySystem:
    """A simplified RAG query system with single query rewrite."""
    def __init__(self, collection_name: str = "medical_evidence"):
        logger.info("Initializing RAG Query System...")
        self.embedding_model = BioLMEmbedding()
        chroma_embedding_function = ChromaEmbeddingFunctionAdapter(self.embedding_model)
        self.vector_store = ChromaStorage(
            collection_name=collection_name,
            embedding_function=chroma_embedding_function
        )
        self.query_rewriter = LLMExtractor(
            model="deepseek",
            api_key=API_KEYS.get("deepseek")
        )
        logger.success("RAG Query System Initialized.")

    def _generate_hypothetical_document(self, query_text: str) -> str:
        """Generates a hypothetical document based on the user's query."""
        logger.info(f"Generating hypothetical document for: '{query_text}'")
        prompt = f"""
As a medical expert, generate a concise, hypothetical clinical note that would be a perfect answer to the user's described symptoms.
Focus on capturing the essence of the user's feelings, especially unique ones like "heart feels heavy".
This note will be used to find similar real cases in a medical database.

User's Description: "{query_text}"

Hypothetical Clinical Note:
"""
        try:
            result = self.query_rewriter.call_api(prompt)
            if result and result.get("success"):
                hypothetical_doc = result.get("response", "").strip()
                logger.success("Generated hypothetical document.")
                return hypothetical_doc
            logger.warning("Failed to generate hypothetical document, will use original query.")
            return query_text
        except Exception as e:
            logger.error(f"An error occurred during hypothetical document generation: {e}")
            return query_text

    def _generate_multiple_queries(self, query_text: str) -> List[str]:
        """Generates multiple diverse queries from a single user query using an LLM."""
        logger.info(f"Generating multiple queries for: '{query_text}'")
        prompt = f"""
You are an expert medical triage assistant. Your task is to analyze the user's symptoms and generate a JSON array of 3-5 highly relevant search queries for a medical knowledge base.
The queries should focus on identifying the primary organ system involved based on the most critical symptoms provided.
Prioritize the most specific and medically significant terms in the user's query.

User's Description: "{query_text}"

Based on this, generate focused queries. For example, for "heart feels heavy", create queries directly investigating cardiac distress signals.

Generate the JSON array of search queries now:
"""
        try:
            result = self.query_rewriter.call_api(prompt)
            if result and result.get("success"):
                response_text = result.get("response", "[]").strip()
                json_part = response_text[response_text.find('['):response_text.rfind(']')+1]
                queries = json.loads(json_part)
                if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
                    logger.success(f"Generated {len(queries)} sub-queries: {queries}")
                    return queries
            logger.warning(f"Failed to generate sub-queries, falling back to original. Reason: {result.get('error', 'Unknown')}")
            return [query_text]
        except Exception as e:
            logger.error(f"An exception occurred during sub-query generation: {e}. Falling back to original query.")
            return [query_text]

    def _reciprocal_rank_fusion(self, search_results_lists: List[List[Dict[str, Any]]], k: int = 60) -> List[Dict[str, Any]]:
        """Fuses multiple lists of search results using Reciprocal Rank Fusion."""
        ranked_scores = defaultdict(float)
        doc_details = {}

        for results_list in search_results_lists:
            for rank, result in enumerate(results_list):
                doc_id = result['id']
                ranked_scores[doc_id] += 1 / (k + rank + 1)
                if doc_id not in doc_details:
                    doc_details[doc_id] = result
        
        sorted_doc_ids = sorted(ranked_scores.keys(), key=lambda id: ranked_scores[id], reverse=True)
        
        final_results = []
        for doc_id in sorted_doc_ids:
            final_doc = doc_details[doc_id]
            final_doc['rrf_score'] = ranked_scores[doc_id]
            final_results.append(final_doc)
            
        logger.info(f"RRF fusion complete. Merged {len(search_results_lists)} result lists into {len(final_results)} unique results.")
        return final_results

    def search(self, query_text: str, top_k: int = 5, use_rewrite: bool = True) -> List[Dict[str, Any]]:
        """Performs a search using multi-query generation and RRF."""
        
        search_query_text = query_text
        if use_rewrite:
            # First, generate a hypothetical document to better capture the query's essence
            hypothetical_doc = self._generate_hypothetical_document(query_text)
            
            # Then, generate sub-queries based on the original query to ensure breadth
            sub_queries = self._generate_multiple_queries(query_text)
            
            # The hypothetical document becomes the primary, most important query
            all_queries = [hypothetical_doc] + sub_queries
        else:
            all_queries = [query_text]
            logger.info("Skipping query rewriting. Using original query.")

        all_search_results = []
        logger.info(f"Executing search for {len(all_queries)} queries (1 hypothetical + {len(all_queries)-1} sub-queries)...")
        for sub_query in all_queries:
            if not sub_query.strip():
                continue
            try:
                results = self.vector_store.query(query_texts=[sub_query], n_results=top_k * 2)
                
                formatted_results = []
                if results and results.get('ids') and results['ids'][0]:
                    for i in range(len(results['ids'][0])):
                        formatted_results.append({
                            "id": results['ids'][0][i], "distance": results['distances'][0][i],
                            "metadata": results['metadatas'][0][i], "document": results['documents'][0][i]
                        })
                all_search_results.append(formatted_results)
            except Exception as e:
                logger.error(f"An error occurred during search for sub-query '{sub_query}': {e}")
        
        fused_results = self._reciprocal_rank_fusion(all_search_results)
        
        return fused_results[:top_k]

def main():
    """Main function to run the query system from the command line."""
    parser = argparse.ArgumentParser(description="Query the RAG system for medical evidence.")
    parser.add_argument("query", type=str, help="The symptom or evidence to query.")
    parser.add_argument("--top_k", type=int, default=5, help="Number of top results to return.")
    parser.add_argument('--no-rewrite', action='store_false', dest='rewrite', help="Disable query rewriting.")
    args = parser.parse_args()

    # Instantiate and run the system
    query_system = RAGQuerySystem(collection_name=RAG_CONFIG.get("collection_name"))
    search_results = query_system.search(args.query, top_k=args.top_k, use_rewrite=args.rewrite)

    # Print results
    if search_results:
        print("\n" + "="*25 + " 🔍 检索结果 (RRF Fused) " + "="*25)
        for i, result in enumerate(search_results):
            print(f"\n--- Top {i+1} (RRF Score: {result.get('rrf_score', 'N/A'):.4f}) ---")
            
            organ = result['metadata'].get('organ', 'N/A')
            specific_part = result['metadata'].get('specific_part', 'N/A')
            
            print(f"  🎯 器官 (Organ): {organ}")
            print(f"  📍 具体部位 (Specific Part): {specific_part}")
            
            print("\n  【原始证据】")
            print(f"    原始症状: {result['metadata'].get('original_symptom', 'N/A')}")
            print(f"    原始证据文本: {result['metadata'].get('original_evidence', 'N/A')}")
            print(f"    来源病例ID: {result['metadata'].get('case_id', 'N/A')}")
            
        print("\n" + "="*60)
    else:
        print("\n" + "="*25 + " 🚫 未找到相关结果 " + "="*25)

if __name__ == "__main__":
    main() 