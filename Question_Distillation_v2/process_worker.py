#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
并行蒸馏工作脚本 (Worker)
作者: Gemini & CDJ_LP
描述: 
该脚本是并行处理流程的核心工作单元。它接收一个文件范围和
一个API配置名称，处理指定范围内的报告，并将结果保存到独立文件。

执行方法 (由启动脚本调用):
python RAG_Evidence4Organ/Question_Distillation_v2/process_worker.py \
    --input_dir RAG_Evidence4Organ/dataset/ \
    --output_dir RAG_Evidence4Organ/Question_Distillation_v2/results/ \
    --api_key_name api_1 \
    --start_index 0 \
    --end_index 100
"""

import os
import sys
import json
import argparse
import re
from typing import List, Dict, Any
from loguru import logger
from datetime import datetime

# 添加项目根目录到Python路径
project_root = "/opt/RAG_Evidence4Organ"
sys.path.insert(0, project_root)

from Question_Distillation_v2.extractors.llm_extractor import LLMExtractor
from Question_Distillation_v2.prompts.medical_prompts import MedicalExtractionPrompts
from configs.system_config import MULTI_API_CONFIG
from configs.model_config import ORGAN_ANATOMY_STRUCTURE

def numeric_sort_key(s: str):
    """为数字排序生成key, e.g., 'report_1.txt' < 'report_2.txt' < 'report_10.txt'"""
    # 提取文件名中的数字部分
    match = re.search(r'report_(\d+)\.txt', s)
    if match:
        return int(match.group(1))
    return 0  # 如果没有匹配到数字，返回0

def load_reports_from_list(file_path: str) -> List[Dict[str, Any]]:
    """从一个文件列表文件中加载报告"""
    logger.info(f"正在从任务列表 {file_path} 加载报告...")
    reports = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            filepaths = [line.strip() for line in f if line.strip()]
        
        for report_path in filepaths:
            try:
                with open(report_path, 'r', encoding='utf-8') as report_file:
                    text = report_file.read()
                filename = os.path.basename(report_path)
                case_id_match = re.search(r'(\d+)', filename)
                case_id = case_id_match.group(1) if case_id_match else filename.replace('.txt', '')
                if text.strip():
                    reports.append({"case_id": case_id, "text": text, "filename": filename})
            except Exception as e:
                logger.error(f"读取报告文件 {report_path} 失败: {e}")
        
        logger.success(f"成功从任务列表加载 {len(reports)} 条报告用于处理。")
        return reports
    except Exception as e:
        logger.error(f"加载任务列表文件 {file_path} 时发生未知错误: {e}")
        return []

def load_reports_in_range(directory_path: str, start_index: int, end_index: int) -> List[Dict[str, Any]]:
    """从目录加载指定范围内的.txt报告 (使用自然排序)"""
    logger.info(f"正在从目录 {directory_path} 加载索引范围 {start_index}-{end_index} 的报告...")
    reports = []
    try:
        all_files = sorted(
            [f for f in os.listdir(directory_path) if f.endswith(".txt")],
            key=numeric_sort_key
        )
        files_in_range = all_files[start_index:end_index]

        for filename in files_in_range:
            file_path = os.path.join(directory_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                case_id_match = re.search(r'(\d+)', filename)
                case_id = case_id_match.group(1) if case_id_match else filename.replace('.txt', '')
                if text.strip():
                    reports.append({"case_id": case_id, "text": text, "filename": filename})
            except Exception as e:
                logger.error(f"读取文件 {filename} 失败: {e}")
        
        logger.success(f"成功加载 {len(reports)} 条报告用于处理。")
        return reports
    except Exception as e:
        logger.error(f"加载目录 {directory_path} 时发生未知错误: {e}")
        return []

def validate_extraction(extraction: Dict[str, Any]) -> bool:
    """验证单个提取结果的合规性 - 支持所有器官"""
    required_keys = ["symptom_or_disease", "inferred_organ", "suggested_anatomical_parts_to_examine", "evidence_from_report"]
    if not all(key in extraction for key in required_keys): 
        return False
    
    organ = extraction["inferred_organ"]
    parts = extraction["suggested_anatomical_parts_to_examine"]
    
    # 检查基本要求
    if not isinstance(parts, list) or len(parts) < 3: 
        return False
    
    # 检查器官类别
    if organ in ORGAN_ANATOMY_STRUCTURE:
        # 对于5个指定器官，验证解剖部位是否在允许列表中
        allowed_parts = ORGAN_ANATOMY_STRUCTURE[organ]
        if not all(part in allowed_parts for part in parts):
            return False
        # 添加器官类别标识
        extraction["organ_category"] = "specified"
    else:
        # 对于其他器官，只验证基本格式，允许LLM自由推断
        # 确保解剖部位不为空且有意义
        if not all(part and len(part.strip()) > 0 for part in parts):
            return False
        # 添加器官类别标识
        extraction["organ_category"] = "other"
    
    return True

def smart_chunk_medical_report(text: str) -> List[Dict[str, str]]:
    """
    基于医学报告结构进行智能分块
    返回: [{"section": "章节名", "content": "内容"}, ...]
    """
    import re
    
    # 医学报告中可能包含症状信息的关键章节（按优先级排序）
    # 使用更精确的模式避免重复匹配
    priority_section_patterns = [
        (r'brief hospital course:?', 'brief hospital course'),
        (r'hospital course by issue/system:?', 'hospital course by system'),  
        (r'hospital course by system:?', 'hospital course by system'),
        (r'hospital course:?', 'hospital course'),  # 放在后面避免被brief覆盖
        (r'assessment and plan:?', 'assessment and plan'),
        (r'impression:?', 'impression'),
        (r'history of present illness:?', 'history of present illness'),
        (r'chief complaint:?', 'chief complaint'),
        (r'physical examination:?', 'physical examination'),  # 统一为examination
        (r'physical exam:?', 'physical examination'),  # 映射到同一个名称
        (r'pertinent results:?', 'pertinent results'),
        (r'past medical history:?', 'past medical history')
    ]
    
    chunks = []
    text_lower = text.lower()
    used_sections = set()  # 防重复
    processed_ranges = []  # 记录已处理的文本范围，避免重复内容
    
    # 找到所有关键章节
    for pattern, canonical_name in priority_section_patterns:
        if canonical_name in used_sections:
            continue  # 跳过已处理的章节类型
            
        matches = list(re.finditer(pattern, text_lower))
        for match in matches:
            start_pos = match.start()
            
            # 检查是否与已处理的范围重叠
            is_overlapping = any(
                abs(start_pos - existing_start) < 500  # 如果开始位置很接近，认为是重复
                for existing_start, _ in processed_ranges
            )
            if is_overlapping:
                logger.info(f"跳过重复章节 '{canonical_name}': 与已处理内容重叠")
                continue
            
            # 找到章节结束位置
            end_pos = len(text)
            for next_pattern, _ in priority_section_patterns:
                next_matches = list(re.finditer(next_pattern, text_lower[start_pos + len(match.group()):]))
                if next_matches:
                    potential_end = start_pos + len(match.group()) + next_matches[0].start()
                    if potential_end > start_pos and potential_end < end_pos:
                        end_pos = potential_end
            
            section_content = text[start_pos:end_pos].strip()
            
            # 过滤太短的章节
            if len(section_content) < 200:
                continue
            
            # 检查章节是否包含症状关键词
            symptom_keywords = [
                'pain', 'ache', 'fever', 'nausea', 'vomiting', 'bleeding', 'swelling',
                'dysfunction', 'failure', 'disease', 'syndrome', 'infection', 'inflammation',
                'hypertension', 'hypotension', 'tachycardia', 'bradycardia', 'arrhythmia',
                'pneumonia', 'embolism', 'infarction', 'ischemia', 'effusion', 'mass',
                'elevated', 'decreased', 'abnormal', 'positive', 'negative', 'acute', 'chronic'
            ]
            
            content_lower = section_content.lower()
            has_symptoms = any(keyword in content_lower for keyword in symptom_keywords)
            
            if not has_symptoms:
                logger.info(f"跳过章节 '{canonical_name}': 未检测到症状关键词")
                continue
            
            # 优化分块策略：增加块大小，减少分块数量
            if len(section_content) > 4000:  # 提高阈值
                sub_chunks = split_large_section_optimized(section_content, canonical_name)
                chunks.extend(sub_chunks)
            else:
                chunks.append({
                    "section": canonical_name,
                    "content": section_content
                })
            
            used_sections.add(canonical_name)
            processed_ranges.append((start_pos, end_pos))
            logger.info(f"识别到有效章节: '{canonical_name}' ({len(section_content)} 字符)")
            break  # 找到第一个匹配就跳出，避免重复
    
    if not chunks:
        logger.warning("未找到标准章节，使用备用分块策略")
        return fallback_smart_chunking(text)
    
    logger.info(f"章节识别完成，共 {len(chunks)} 个有效块，已去重")
    return chunks

def fallback_smart_chunking(text: str) -> List[Dict[str, str]]:
    """备用的智能分块方法 - 基于内容而非章节"""
    import re
    
    # 寻找包含症状信息的段落
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    chunk_count = 1
    
    symptom_keywords = [
        'pain', 'ache', 'fever', 'nausea', 'bleeding', 'dysfunction', 'failure',
        'hypertension', 'tachycardia', 'pneumonia', 'elevated', 'decreased'
    ]
    
    for paragraph in paragraphs:
        paragraph_lower = paragraph.lower()
        has_symptoms = any(keyword in paragraph_lower for keyword in symptom_keywords)
        
        if has_symptoms or len(current_chunk) == 0:  # 包含症状或是第一个段落
            if len(current_chunk + paragraph) > 2500:
                if current_chunk:
                    chunks.append({
                        "section": f"content_block_{chunk_count}",
                        "content": current_chunk.strip()
                    })
                    chunk_count += 1
                current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
    
    if current_chunk:
        chunks.append({
            "section": f"content_block_{chunk_count}",
            "content": current_chunk.strip()
        })
    
    return chunks

def split_large_section_optimized(content: str, section_name: str) -> List[Dict[str, str]]:
    """优化的大章节分割 - 减少分块数量"""
    import re
    
    # 增加每块的大小限制，减少分块数量
    max_chunk_size = 3000  # 从2000增加到3000
    
    # 尝试按数字编号分割 (如 1., 2., 3.)
    numbered_items = re.split(r'\n\s*\d+\.', content)
    
    if len(numbered_items) > 1:
        chunks = []
        current_chunk = ""
        part_num = 1
        
        for i, item in enumerate(numbered_items):
            if not item.strip():
                continue
                
            if len(current_chunk + item) > max_chunk_size and current_chunk:
                chunks.append({
                    "section": f"{section_name} - part {part_num}",
                    "content": current_chunk.strip()
                })
                part_num += 1
                current_chunk = item.strip()
            else:
                current_chunk += "\n" + item.strip() if current_chunk else item.strip()
        
        if current_chunk:
            chunks.append({
                "section": f"{section_name} - part {part_num}",
                "content": current_chunk.strip()
            })
        
        return chunks
    
    # 如果没有数字编号，按句子分割，但使用更大的块
    sentences = content.split('. ')
    chunks = []
    current_chunk = ""
    chunk_count = 1
    
    for sentence in sentences:
        if len(current_chunk + sentence + '. ') > max_chunk_size and current_chunk:
            chunks.append({
                "section": f"{section_name} - part {chunk_count}",
                "content": current_chunk.strip()
            })
            chunk_count += 1
            current_chunk = sentence + '. '
        else:
            current_chunk += sentence + '. '
    
    if current_chunk:
        chunks.append({
            "section": f"{section_name} - part {chunk_count}",
            "content": current_chunk.strip()
        })
    
    return chunks

def process_report(report: Dict[str, Any], extractor: LLMExtractor, prompt: str) -> List[Dict[str, Any]]:
    """使用优化的结构化分块处理单个报告"""
    text, case_id = report.get("text", ""), report.get("case_id", "N/A")
    logger.info(f"Worker正在处理病例: {case_id}...")
    
    # 检查文本长度，如果太长则采用结构化分块
    if len(text) > 4000:  # 提高阈值，减少不必要的分块
        logger.info(f"病例 {case_id} 文本较长({len(text)}字符)，采用结构化分块处理")
        text_chunks = smart_chunk_medical_report(text)
        
        if not text_chunks:
            logger.warning(f"病例 {case_id} 未能识别到有效章节，跳过处理")
            return []
        
        logger.info(f"病例 {case_id} 最终分割为 {len(text_chunks)} 个优化后的章节块")
        
        all_extractions = []
        successful_chunks = 0
        
        for i, chunk_info in enumerate(text_chunks):
            section_name = chunk_info["section"]
            chunk_content = chunk_info["content"]
            
            logger.info(f"处理病例 {case_id} 的章节 {i+1}/{len(text_chunks)}: {section_name}")
            
            # 为每个章节添加上下文信息
            enhanced_prompt = prompt + f"\n\n--- Medical Report Section: {section_name} ---\n" + chunk_content
            result = extractor.call_api(enhanced_prompt)
            
            if not (result and result.get("success")):
                logger.warning(f"病例 {case_id} 章节 '{section_name}' 的LLM调用失败")
                continue
            
            chunk_extractions = parse_llm_response(result.get("response", "[]"), case_id, section_name)
            if chunk_extractions:
                all_extractions.extend(chunk_extractions)
                successful_chunks += 1
        
        logger.success(f"病例 {case_id} 结构化分块处理完成: {successful_chunks}/{len(text_chunks)} 个章节成功，共提取 {len(all_extractions)} 条记录")
        return all_extractions
    else:
        # 短文本的单次处理逻辑
        logger.info(f"病例 {case_id} 文本较短({len(text)}字符)，采用单次处理")
        full_prompt = prompt + "\n\n--- Medical Report ---\n" + text
        result = extractor.call_api(full_prompt)

        if not (result and result.get("success")):
            logger.warning(f"病例 {case_id} 的LLM调用失败。")
            return []
        
        extractions = parse_llm_response(result.get("response", "[]"), case_id)
        logger.success(f"病例 {case_id} 单次处理完成，提取 {len(extractions)} 条记录")
        return extractions

def parse_llm_response(response_text: str, case_id: str, section_name: str = None) -> List[Dict[str, Any]]:
    """解析LLM响应的独立函数"""
    try:
        # 打印原始LLM返回内容，便于调试
        section_info = f" 章节[{section_name}]" if section_name else ""
        logger.info(f"病例 {case_id}{section_info} 的LLM响应长度: {len(response_text)} 字符")
        
        # 尝试修复被截断的JSON
        # 1. 首先尝试标准解析
        import re
        match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if not match:
            logger.warning(f"病例 {case_id}{section_info} 未找到JSON数组格式")
            return []
        
        json_str = match.group(0)
        
        # 2. 检查JSON是否完整
        try:
            extractions = json.loads(json_str)
            if not isinstance(extractions, list): 
                logger.warning(f"病例 {case_id}{section_info} JSON解析结果不是数组")
                return []
            logger.success(f"病例 {case_id}{section_info} JSON解析成功，提取 {len(extractions)} 条记录")
        except json.JSONDecodeError as e:
            logger.warning(f"病例 {case_id}{section_info} JSON解析失败，尝试修复: {e}")
            
            # 3. 尝试修复被截断的JSON
            objects = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', json_str)
            if objects:
                fixed_json = "[" + ",".join(objects) + "]"
                try:
                    extractions = json.loads(fixed_json)
                    if not isinstance(extractions, list):
                        logger.warning(f"病例 {case_id}{section_info} 修复后JSON仍不是数组")
                        return []
                    logger.info(f"病例 {case_id}{section_info} JSON修复成功，使用 {len(extractions)} 个完整对象")
                except json.JSONDecodeError:
                    logger.error(f"病例 {case_id}{section_info} JSON修复失败")
                    return []
            else:
                logger.error(f"病例 {case_id}{section_info} 无法找到任何完整JSON对象")
                return []
                
    except Exception as e:
        logger.error(f"病例 {case_id}{section_info} 处理LLM响应时发生未知错误: {e}")
        return []

    valid_extractions = []
    for ext in extractions:
        ext['case_id'] = case_id
        # 添加章节信息用于追溯
        if section_name:
            ext['source_section'] = section_name
        if validate_extraction(ext):
            valid_extractions.append(ext)
    return valid_extractions

def main():
    parser = argparse.ArgumentParser(description="并行蒸馏工作脚本")
    parser.add_argument("--input_dir", type=str, help="包含原始.txt报告的目录 (与-start_index, -end_index配合使用)")
    parser.add_argument("--output_dir", type=str, required=True, help="存放独立输出JSON文件的目录")
    parser.add_argument("--api_key_name", type=str, required=True, help="在system_config.py中定义的API配置名 (e.g., api_1)")
    parser.add_argument("--start_index", type=int, help="处理的起始文件索引")
    parser.add_argument("--end_index", type=int, help="处理的结束文件索引")
    parser.add_argument("--file_list", type=str, help="一个文件，包含需要处理的报告文件的绝对路径列表 (优先于-input_dir)")
    parser.add_argument("--prompt_type", type=str, default="universal", choices=["universal", "restricted"], 
                       help="提示词类型: universal(所有器官) 或 restricted(仅5个指定器官)")
    args = parser.parse_args()

    # 校验参数
    if args.file_list:
        logger.info(f"🚀 Worker以文件列表模式启动: API='{args.api_key_name}', 任务文件='{args.file_list}'...")
    elif args.input_dir and args.start_index is not None and args.end_index is not None:
        logger.info(f"🚀 Worker以范围模式启动: API='{args.api_key_name}', 范围=[{args.start_index}, {args.end_index})...")
    else:
        logger.error("参数错误: 必须提供 '--file_list' 或者 '--input_dir', '--start_index' 和 '--end_index' 三者。")
        return

    # 1. 初始化工具、提示和为该worker创建专属输出子目录
    api_config = MULTI_API_CONFIG.get(args.api_key_name)
    if not api_config:
        logger.error(f"未在system_config.py中找到名为 '{args.api_key_name}' 的API配置。")
        return
        
    llm_extractor = LLMExtractor(
        model=api_config["model"],
        api_key=api_config["api_key"],
        base_url=api_config["base_url"]
    )
    # 根据参数选择提示词类型
    if args.prompt_type == "universal":
        inference_prompt = MedicalExtractionPrompts.get_universal_inference_prompt()
        logger.info("使用通用推理提示词 - 支持所有器官系统")
    else:
        inference_prompt = MedicalExtractionPrompts.get_inference_prompt()
        logger.info("使用限制性推理提示词 - 仅支持5个指定器官")
    
    # 为每个worker创建一个专属的子目录
    worker_output_dir = os.path.join(args.output_dir, f"worker_{args.api_key_name}")
    os.makedirs(worker_output_dir, exist_ok=True)
    
    # 创建详细输出目录结构
    detailed_dirs = {
        "json": os.path.join(worker_output_dir, "json_results"),
        "logs": os.path.join(worker_output_dir, "processing_logs"), 
        "thinking": os.path.join(worker_output_dir, "thinking_chains")
    }
    
    for dir_path in detailed_dirs.values():
        os.makedirs(dir_path, exist_ok=True)
    
    logger.info(f"Worker的输出将被保存到: {worker_output_dir}")
    logger.info(f"详细结果目录: JSON={detailed_dirs['json']}, LOG={detailed_dirs['logs']}, TXT={detailed_dirs['thinking']}")

    # 2. 根据模式加载数据
    if args.file_list:
        reports_to_process = load_reports_from_list(args.file_list)
    else:
        reports_to_process = load_reports_in_range(args.input_dir, args.start_index, args.end_index)

    if not reports_to_process:
        logger.warning("未加载到任何报告，Worker退出。")
        return

    # 3. 循环处理，并将每个报告的结果保存为独立文件
    total_processed_count = 0
    for report in reports_to_process:
        case_id = report.get('case_id', 'unknown')
        original_filename_base = os.path.splitext(report.get('filename', f"report_{case_id}"))[0]
        
        # 设置日志文件，记录该报告的处理过程
        processing_log_file = os.path.join(detailed_dirs['logs'], f"{original_filename_base}_processing.log")
        
        # 创建报告专用的logger
        report_logger = logger.bind(report_id=case_id, log_file=processing_log_file)
        report_logger.info(f"开始处理报告 {case_id} ({report.get('filename')})")
        
        # 处理报告并收集思考链
        thinking_chain = []
        valid_extractions = process_report_with_thinking(
            report, llm_extractor, inference_prompt, thinking_chain, report_logger
        )
        
        # 保存JSON结果
        if valid_extractions:
            json_result_file = os.path.join(detailed_dirs['json'], f"{original_filename_base}_extracted.json")
            try:
                result_data = {
                    "report_info": {
                        "case_id": case_id,
                        "filename": report.get('filename'),
                        "processing_time": str(datetime.now()),
                        "api_used": args.api_key_name,
                        "total_extractions": len(valid_extractions)
                    },
                    "extractions": valid_extractions
                }
                
                with open(json_result_file, 'w', encoding='utf-8') as f:
                    json.dump(result_data, f, ensure_ascii=False, indent=2)
                
                total_processed_count += len(valid_extractions)
                report_logger.success(f"JSON结果已保存: {json_result_file}")
                
            except Exception as e:
                report_logger.error(f"保存JSON文件失败: {e}")
        
        # 保存思考链
        thinking_file = os.path.join(detailed_dirs['thinking'], f"{original_filename_base}_thinking.txt")
        try:
            with open(thinking_file, 'w', encoding='utf-8') as f:
                f.write(f"报告 {case_id} 的处理思考链\n")
                f.write("=" * 50 + "\n\n")
                for i, step in enumerate(thinking_chain, 1):
                    f.write(f"步骤 {i}: {step['action']}\n")
                    f.write(f"时间: {step['timestamp']}\n") 
                    f.write(f"详情: {step['details']}\n")
                    f.write("-" * 30 + "\n\n")
            
            report_logger.success(f"思考链已保存: {thinking_file}")
            
        except Exception as e:
            report_logger.error(f"保存思考链文件失败: {e}")
        
        # 创建处理日志的摘要
        log_summary_file = os.path.join(detailed_dirs['logs'], f"{original_filename_base}_summary.log")
        try:
            with open(log_summary_file, 'w', encoding='utf-8') as f:
                f.write(f"报告处理摘要 - {case_id}\n")
                f.write("=" * 40 + "\n")
                f.write(f"文件名: {report.get('filename')}\n")
                f.write(f"处理时间: {datetime.now()}\n")
                f.write(f"使用API: {args.api_key_name}\n")
                f.write(f"提取记录数: {len(valid_extractions)}\n")
                f.write(f"处理状态: {'成功' if valid_extractions else '失败'}\n")
                f.write("-" * 40 + "\n")
                
                if valid_extractions:
                    f.write("提取的症状概要:\n")
                    for i, ext in enumerate(valid_extractions[:10], 1):  # 显示前10个
                        f.write(f"{i}. {ext.get('symptom_or_disease', 'N/A')} -> {ext.get('inferred_organ', 'N/A')}\n")
                    if len(valid_extractions) > 10:
                        f.write(f"... 还有 {len(valid_extractions) - 10} 条记录\n")
                
        except Exception as e:
            report_logger.error(f"保存摘要日志失败: {e}")

    logger.success(f"✅ Worker任务完成。总共生成 {total_processed_count} 条高质量语料。")
    logger.info(f"详细结果已分类保存在:")
    logger.info(f"  JSON结果: {detailed_dirs['json']}/")
    logger.info(f"  处理日志: {detailed_dirs['logs']}/") 
    logger.info(f"  思考链: {detailed_dirs['thinking']}/")

def process_report_with_thinking(report: Dict[str, Any], extractor: LLMExtractor, 
                               prompt: str, thinking_chain: List[Dict], report_logger) -> List[Dict[str, Any]]:
    """带思考链记录的报告处理函数"""
    from datetime import datetime
    
    text, case_id = report.get("text", ""), report.get("case_id", "N/A")
    
    thinking_chain.append({
        "action": "开始处理报告",
        "timestamp": str(datetime.now()),
        "details": f"报告长度: {len(text)} 字符"
    })
    
    # 检查文本长度，如果太长则采用结构化分块
    if len(text) > 4000:
        thinking_chain.append({
            "action": "文本分块决策",
            "timestamp": str(datetime.now()),
            "details": f"文本超过4000字符，采用结构化分块处理"
        })
        
        text_chunks = smart_chunk_medical_report(text)
        
        if not text_chunks:
            thinking_chain.append({
                "action": "分块失败",
                "timestamp": str(datetime.now()),
                "details": "未能识别到有效章节，跳过处理"
            })
            return []
        
        thinking_chain.append({
            "action": "分块成功",
            "timestamp": str(datetime.now()),
            "details": f"分割为 {len(text_chunks)} 个章节块"
        })
        
        all_extractions = []
        successful_chunks = 0
        
        for i, chunk_info in enumerate(text_chunks):
            section_name = chunk_info["section"]
            chunk_content = chunk_info["content"]
            
            thinking_chain.append({
                "action": f"处理章节 {i+1}/{len(text_chunks)}",
                "timestamp": str(datetime.now()),
                "details": f"章节: {section_name}, 长度: {len(chunk_content)} 字符"
            })
            
            enhanced_prompt = prompt + f"\n\n--- Medical Report Section: {section_name} ---\n" + chunk_content
            result = extractor.call_api(enhanced_prompt)
            
            if not (result and result.get("success")):
                thinking_chain.append({
                    "action": "API调用失败",
                    "timestamp": str(datetime.now()),
                    "details": f"章节 '{section_name}' 的LLM调用失败"
                })
                continue
            
            chunk_extractions = parse_llm_response(result.get("response", "[]"), case_id, section_name)
            if chunk_extractions:
                all_extractions.extend(chunk_extractions)
                successful_chunks += 1
                
                thinking_chain.append({
                    "action": "章节处理成功",
                    "timestamp": str(datetime.now()),
                    "details": f"从章节 '{section_name}' 提取了 {len(chunk_extractions)} 条记录"
                })
        
        thinking_chain.append({
            "action": "分块处理完成",
            "timestamp": str(datetime.now()),
            "details": f"成功处理 {successful_chunks}/{len(text_chunks)} 个章节，总提取 {len(all_extractions)} 条记录"
        })
        
        return all_extractions
    else:
        thinking_chain.append({
            "action": "单次处理决策",
            "timestamp": str(datetime.now()),
            "details": f"文本较短({len(text)}字符)，采用单次处理"
        })
        
        full_prompt = prompt + "\n\n--- Medical Report ---\n" + text
        result = extractor.call_api(full_prompt)

        if not (result and result.get("success")):
            thinking_chain.append({
                "action": "API调用失败",
                "timestamp": str(datetime.now()),
                "details": "LLM调用失败"
            })
            return []
        
        extractions = parse_llm_response(result.get("response", "[]"), case_id)
        
        thinking_chain.append({
            "action": "单次处理完成",
            "timestamp": str(datetime.now()),
            "details": f"提取 {len(extractions)} 条记录"
        })
        
        return extractions


if __name__ == "__main__":
    main() 