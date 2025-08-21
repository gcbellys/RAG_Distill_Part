#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档处理器
用于症状提取的文档分块和预处理，适配原蒸馏系统的分块逻辑
"""

import re
from typing import List, Dict, Any
from loguru import logger

class DocumentProcessor:
    """文档处理器类，专门用于症状提取的文档预处理"""
    
    def __init__(self, min_chunk_size: int = 200, max_chunk_size: int = 4000):
        """
        初始化文档处理器
        
        Args:
            min_chunk_size: 最小块大小
            max_chunk_size: 最大块大小
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        
        # 医学报告中包含症状信息的关键章节（按优先级排序）
        self.priority_section_patterns = [
            (r'brief hospital course:?', 'brief hospital course'),
            (r'hospital course by issue/system:?', 'hospital course by system'),  
            (r'hospital course by system:?', 'hospital course by system'),
            (r'hospital course:?', 'hospital course'),
            (r'assessment and plan:?', 'assessment and plan'),
            (r'impression:?', 'impression'),
            (r'history of present illness:?', 'history of present illness'),
            (r'chief complaint:?', 'chief complaint'),
            (r'physical examination:?', 'physical examination'),
            (r'physical exam:?', 'physical examination'),
            (r'pertinent results:?', 'pertinent results'),
            (r'past medical history:?', 'past medical history'),
            (r'review of systems:?', 'review of systems'),
            (r'discharge diagnosis:?', 'discharge diagnosis'),
            (r'discharge medications:?', 'discharge medications'),
            (r'labs:?', 'laboratory results'),
            (r'laboratory:?', 'laboratory results'),
            (r'vital signs:?', 'vital signs')
        ]
        
        # 症状关键词 - 用于判断章节是否包含症状信息
        self.symptom_keywords = [
            'pain', 'ache', 'fever', 'nausea', 'vomiting', 'bleeding', 'swelling',
            'dysfunction', 'failure', 'disease', 'syndrome', 'infection', 'inflammation',
            'hypertension', 'hypotension', 'tachycardia', 'bradycardia', 'arrhythmia',
            'pneumonia', 'embolism', 'infarction', 'ischemia', 'effusion', 'mass',
            'elevated', 'decreased', 'abnormal', 'positive', 'negative', 'acute', 'chronic',
            'complaint', 'symptom', 'distress', 'discomfort', 'weakness', 'fatigue',
            'shortness', 'difficulty', 'trouble', 'unable', 'rash', 'lesion', 'wound',
            'cough', 'wheeze', 'dyspnea', 'chest', 'abdominal', 'headache', 'dizziness'
        ]
    
    def process_document(self, text: str, case_id: str = "unknown") -> List[Dict[str, Any]]:
        """
        处理单个文档，返回包含症状信息的分块
        
        Args:
            text: 文档文本
            case_id: 病例ID
            
        Returns:
            分块列表，每个分块包含section_name和content
        """
        logger.info(f"开始处理文档 {case_id}，长度: {len(text)} 字符")
        
        if len(text) <= self.max_chunk_size:
            # 短文档直接检查是否包含症状
            if self._contains_symptoms(text):
                return [{
                    "section_name": "complete_document",
                    "content": text.strip(),
                    "case_id": case_id,
                    "word_count": len(text.split())
                }]
            else:
                logger.info(f"文档 {case_id} 未包含症状关键词，跳过处理")
                return []
        
        # 长文档采用智能分块
        chunks = self._smart_chunk_medical_report(text, case_id)
        
        if not chunks:
            logger.warning(f"文档 {case_id} 未找到标准章节，使用备用分块策略")
            chunks = self._fallback_chunking(text, case_id)
        
        logger.info(f"文档 {case_id} 处理完成，生成 {len(chunks)} 个有效分块")
        return chunks
    
    def _smart_chunk_medical_report(self, text: str, case_id: str) -> List[Dict[str, Any]]:
        """
        基于医学报告结构进行智能分块
        适配并优化原系统的分块逻辑，专门用于症状提取
        """
        chunks = []
        text_lower = text.lower()
        used_sections = set()
        processed_ranges = []
        
        # 找到所有关键章节
        for pattern, canonical_name in self.priority_section_patterns:
            if canonical_name in used_sections:
                continue
                
            matches = list(re.finditer(pattern, text_lower))
            for match in matches:
                start_pos = match.start()
                
                # 检查是否与已处理的范围重叠
                is_overlapping = any(
                    abs(start_pos - existing_start) < 500
                    for existing_start, _ in processed_ranges
                )
                if is_overlapping:
                    logger.debug(f"跳过重复章节 '{canonical_name}': 与已处理内容重叠")
                    continue
                
                # 找到章节结束位置
                end_pos = self._find_section_end(text_lower, start_pos, match.group())
                section_content = text[start_pos:end_pos].strip()
                
                # 过滤太短的章节
                if len(section_content) < self.min_chunk_size:
                    continue
                
                # 检查章节是否包含症状关键词
                if not self._contains_symptoms(section_content):
                    logger.debug(f"跳过章节 '{canonical_name}': 未检测到症状关键词")
                    continue
                
                # 处理大章节
                if len(section_content) > self.max_chunk_size:
                    sub_chunks = self._split_large_section(section_content, canonical_name, case_id)
                    chunks.extend(sub_chunks)
                else:
                    chunks.append({
                        "section_name": canonical_name,
                        "content": section_content,
                        "case_id": case_id,
                        "word_count": len(section_content.split()),
                        "char_count": len(section_content)
                    })
                
                used_sections.add(canonical_name)
                processed_ranges.append((start_pos, end_pos))
                logger.debug(f"识别到有效章节: '{canonical_name}' ({len(section_content)} 字符)")
                break
        
        return chunks
    
    def _find_section_end(self, text_lower: str, start_pos: int, match_text: str) -> int:
        """找到章节的结束位置"""
        end_pos = len(text_lower)
        
        # 查找下一个章节的开始位置
        search_start = start_pos + len(match_text)
        
        for next_pattern, _ in self.priority_section_patterns:
            next_matches = list(re.finditer(next_pattern, text_lower[search_start:]))
            if next_matches:
                potential_end = search_start + next_matches[0].start()
                if potential_end > start_pos and potential_end < end_pos:
                    end_pos = potential_end
        
        return end_pos
    
    def _contains_symptoms(self, text: str) -> bool:
        """检查文本是否包含症状关键词"""
        content_lower = text.lower()
        return any(keyword in content_lower for keyword in self.symptom_keywords)
    
    def _split_large_section(self, content: str, section_name: str, case_id: str) -> List[Dict[str, Any]]:
        """将大章节分割为小块"""
        chunks = []
        sentences = re.split(r'[.!?]+\s+', content)
        
        current_chunk = ""
        chunk_count = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # 检查添加这个句子是否会超过大小限制
            if len(current_chunk) + len(sentence) + 2 > self.max_chunk_size and current_chunk:
                # 保存当前块
                if len(current_chunk) >= self.min_chunk_size and self._contains_symptoms(current_chunk):
                    chunk_count += 1
                    chunks.append({
                        "section_name": f"{section_name}_part_{chunk_count}",
                        "content": current_chunk.strip(),
                        "case_id": case_id,
                        "word_count": len(current_chunk.split()),
                        "char_count": len(current_chunk),
                        "is_subsection": True,
                        "parent_section": section_name
                    })
                current_chunk = sentence
            else:
                if current_chunk:
                    current_chunk += ". " + sentence
                else:
                    current_chunk = sentence
        
        # 处理最后一块
        if current_chunk and len(current_chunk) >= self.min_chunk_size and self._contains_symptoms(current_chunk):
            chunk_count += 1
            chunks.append({
                "section_name": f"{section_name}_part_{chunk_count}",
                "content": current_chunk.strip(),
                "case_id": case_id,
                "word_count": len(current_chunk.split()),
                "char_count": len(current_chunk),
                "is_subsection": True,
                "parent_section": section_name
            })
        
        logger.info(f"大章节 '{section_name}' 分割为 {len(chunks)} 个子块")
        return chunks
    
    def _fallback_chunking(self, text: str, case_id: str) -> List[Dict[str, Any]]:
        """备用分块策略 - 基于内容和段落进行分块"""
        chunks = []
        paragraphs = text.split('\n\n')
        
        current_chunk = ""
        chunk_count = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # 检查添加这个段落是否会超过大小限制
            if len(current_chunk) + len(paragraph) + 2 > self.max_chunk_size and current_chunk:
                # 保存当前块
                if len(current_chunk) >= self.min_chunk_size and self._contains_symptoms(current_chunk):
                    chunk_count += 1
                    chunks.append({
                        "section_name": f"content_block_{chunk_count}",
                        "content": current_chunk.strip(),
                        "case_id": case_id,
                        "word_count": len(current_chunk.split()),
                        "char_count": len(current_chunk),
                        "is_fallback": True
                    })
                current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # 处理最后一块
        if current_chunk and len(current_chunk) >= self.min_chunk_size and self._contains_symptoms(current_chunk):
            chunk_count += 1
            chunks.append({
                "section_name": f"content_block_{chunk_count}",
                "content": current_chunk.strip(),
                "case_id": case_id,
                "word_count": len(current_chunk.split()),
                "char_count": len(current_chunk),
                "is_fallback": True
            })
        
        logger.info(f"备用分块完成，生成 {len(chunks)} 个内容块")
        return chunks
    
    def batch_process_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量处理文档
        
        Args:
            documents: 文档列表，每个文档包含text和case_id
            
        Returns:
            所有文档的分块列表
        """
        all_chunks = []
        
        for i, doc in enumerate(documents):
            try:
                text = doc.get("text", "")
                case_id = doc.get("case_id", f"doc_{i}")
                
                logger.info(f"处理文档 {i+1}/{len(documents)}: {case_id}")
                
                chunks = self.process_document(text, case_id)
                all_chunks.extend(chunks)
                
            except Exception as e:
                logger.error(f"处理文档 {i} 时发生异常: {str(e)}")
                continue
        
        logger.info(f"批量处理完成：{len(documents)} 个文档生成 {len(all_chunks)} 个分块")
        return all_chunks
    
    def get_processing_stats(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取处理统计信息
        
        Args:
            chunks: 分块列表
            
        Returns:
            统计信息字典
        """
        if not chunks:
            return {"total_chunks": 0}
        
        # 按章节类型统计
        section_stats = {}
        total_chars = 0
        total_words = 0
        
        for chunk in chunks:
            section_name = chunk.get("section_name", "unknown")
            if section_name not in section_stats:
                section_stats[section_name] = 0
            section_stats[section_name] += 1
            
            total_chars += chunk.get("char_count", 0)
            total_words += chunk.get("word_count", 0)
        
        return {
            "total_chunks": len(chunks),
            "total_characters": total_chars,
            "total_words": total_words,
            "avg_chunk_size": total_chars / len(chunks) if chunks else 0,
            "section_distribution": section_stats,
            "unique_sections": len(section_stats)
        } 