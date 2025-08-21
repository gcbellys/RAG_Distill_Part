#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
症状提取Worker脚本
专门用于从医学报告中提取症状描述，构建测试集
作者: CDJ_LP
描述: 
该脚本是症状提取流程的核心工作单元。它接收一个文件范围和
一个API配置名称，处理指定范围内的报告，提取症状描述并将结果保存到独立文件。

执行方法:
python Question_set/symptom_worker.py \
    --input_dir dataset/ \
    --output_dir Question_set/results/ \
    --api_key_name api_1 \
    --start_index 40000 \
    --end_index 40100 \
    --prompt_type comprehensive
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

from Question_set.extractors.symptom_extractor import SymptomExtractor
from Question_set.prompts.symptom_prompts import SymptomExtractionPrompts, get_prompt_by_task
from Question_set.processors.document_processor import DocumentProcessor
from configs.system_config import MULTI_API_CONFIG

def numeric_sort_key(s: str):
    """为数字排序生成key, e.g., 'report_1.txt' < 'report_2.txt' < 'report_10.txt'"""
    match = re.search(r'report_(\d+)\.txt', s)
    if match:
        return int(match.group(1))
    return 0

def load_reports_from_list(file_path: str) -> List[Dict[str, Any]]:
    """从文件列表文件中加载报告"""
    try:
        reports = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                if not os.path.exists(line):
                    logger.warning(f"第{line_num}行: 文件不存在: {line}")
                    continue
                
                try:
                    with open(line, 'r', encoding='utf-8') as report_file:
                        content = report_file.read()
                        case_id = os.path.basename(line).replace('.txt', '')
                        reports.append({
                            "text": content,
                            "case_id": case_id,
                            "file_path": line
                        })
                except Exception as e:
                    logger.error(f"读取报告文件 {line} 失败: {str(e)}")
                    continue
        
        logger.info(f"从文件列表成功加载 {len(reports)} 个报告")
        return reports
        
    except Exception as e:
        logger.error(f"加载文件列表失败: {str(e)}")
        return []

def load_reports_in_range(input_dir: str, start_index: int, end_index: int) -> List[Dict[str, Any]]:
    """从指定目录和范围加载报告"""
    try:
        all_files = [f for f in os.listdir(input_dir) if f.endswith('.txt') and f.startswith('report_')]
        all_files.sort(key=numeric_sort_key)
        
        if end_index > len(all_files):
            end_index = len(all_files)
            logger.warning(f"结束索引超出范围，调整为 {end_index}")
        
        selected_files = all_files[start_index:end_index]
        reports = []
        
        for filename in selected_files:
            file_path = os.path.join(input_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    case_id = filename.replace('.txt', '')
                    reports.append({
                        "text": content,
                        "case_id": case_id,
                        "file_path": file_path
                    })
            except Exception as e:
                logger.error(f"读取文件 {file_path} 失败: {str(e)}")
                continue
        
        logger.info(f"从范围 [{start_index}, {end_index}) 成功加载 {len(reports)} 个报告")
        return reports
        
    except Exception as e:
        logger.error(f"从范围加载报告失败: {str(e)}")
        return []

def save_symptom_results(symptoms: List[Dict[str, Any]], case_id: str, 
                        output_dirs: Dict[str, str]) -> bool:
    """保存症状提取结果到文件"""
    try:
        # 保存JSON结果
        json_file = os.path.join(output_dirs["json"], f"{case_id}_symptoms.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(symptoms, f, ensure_ascii=False, indent=2)
        
        # 保存简化的文本结果
        txt_file = os.path.join(output_dirs["txt"], f"{case_id}_symptoms.txt")
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"病例ID: {case_id}\n")
            f.write(f"提取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"症状数量: {len(symptoms)}\n")
            f.write("=" * 60 + "\n\n")
            
            for i, symptom in enumerate(symptoms, 1):
                f.write(f"症状 {i}:\n")
                f.write(f"  描述: {symptom.get('symptom_description', 'N/A')}\n")
                f.write(f"  类型: {symptom.get('symptom_type', 'N/A')}\n")
                f.write(f"  身体系统: {symptom.get('body_system', 'N/A')}\n")
                f.write(f"  严重程度: {symptom.get('severity', 'N/A')}\n")
                f.write(f"  原文: {symptom.get('original_text', 'N/A')[:100]}...\n")
                f.write("-" * 40 + "\n\n")
        
        return True
        
    except Exception as e:
        logger.error(f"保存症状提取结果失败: {str(e)}")
        return False

def save_processing_log(case_id: str, processing_info: Dict[str, Any], 
                       output_dirs: Dict[str, str]) -> bool:
    """保存处理日志"""
    try:
        log_file = os.path.join(output_dirs["logs"], f"{case_id}_processing.json")
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(processing_info, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存处理日志失败: {str(e)}")
        return False

def process_single_report(report: Dict[str, Any], extractor: SymptomExtractor, 
                         processor: DocumentProcessor, prompt: str,
                         output_dirs: Dict[str, str]) -> Dict[str, Any]:
    """处理单个报告的症状提取"""
    
    case_id = report.get("case_id", "unknown")
    text = report.get("text", "")
    
    processing_info = {
        "case_id": case_id,
        "start_time": datetime.now().isoformat(),
        "text_length": len(text),
        "word_count": len(text.split()),
        "steps": []
    }
    
    try:
        # 步骤1: 文档预处理和分块
        processing_info["steps"].append({
            "step": "document_processing",
            "timestamp": datetime.now().isoformat(),
            "action": "开始文档分块处理"
        })
        
        chunks = processor.process_document(text, case_id)
        
        processing_info["chunks_generated"] = len(chunks)
        processing_info["steps"].append({
            "step": "document_processing",
            "timestamp": datetime.now().isoformat(),
            "action": f"文档分块完成，生成 {len(chunks)} 个分块"
        })
        
        if not chunks:
            logger.warning(f"病例 {case_id}: 未生成有效分块，跳过处理")
            processing_info["status"] = "skipped"
            processing_info["reason"] = "无有效分块"
            save_processing_log(case_id, processing_info, output_dirs)
            return {"case_id": case_id, "symptoms": [], "status": "skipped"}
        
        # 步骤2: 症状提取
        processing_info["steps"].append({
            "step": "symptom_extraction",
            "timestamp": datetime.now().isoformat(),
            "action": "开始症状提取"
        })
        
        all_symptoms = []
        
        if len(chunks) == 1:
            # 单块处理
            chunk = chunks[0]
            symptoms = extractor.extract_symptoms_from_text(chunk["content"], prompt)
            all_symptoms.extend(symptoms)
        else:
            # 多块处理
            all_symptoms = extractor.extract_symptoms_from_chunks(chunks, prompt)
        
        processing_info["symptoms_extracted"] = len(all_symptoms)
        processing_info["steps"].append({
            "step": "symptom_extraction",
            "timestamp": datetime.now().isoformat(),
            "action": f"症状提取完成，提取到 {len(all_symptoms)} 个症状"
        })
        
        # 步骤3: 保存结果
        processing_info["steps"].append({
            "step": "save_results",
            "timestamp": datetime.now().isoformat(),
            "action": "开始保存结果"
        })
        
        # 为每个症状添加额外信息
        for symptom in all_symptoms:
            symptom["case_id"] = case_id
            symptom["extraction_timestamp"] = datetime.now().isoformat()
        
        # 保存症状提取结果
        save_success = save_symptom_results(all_symptoms, case_id, output_dirs)
        
        processing_info["end_time"] = datetime.now().isoformat()
        processing_info["status"] = "completed" if save_success else "save_failed"
        processing_info["save_success"] = save_success
        
        # 保存处理日志
        save_processing_log(case_id, processing_info, output_dirs)
        
        logger.success(f"病例 {case_id} 处理完成：提取到 {len(all_symptoms)} 个症状")
        
        return {
            "case_id": case_id,
            "symptoms": all_symptoms,
            "status": "completed",
            "processing_info": processing_info
        }
        
    except Exception as e:
        logger.error(f"处理病例 {case_id} 时发生异常: {str(e)}")
        processing_info["end_time"] = datetime.now().isoformat()
        processing_info["status"] = "error"
        processing_info["error"] = str(e)
        save_processing_log(case_id, processing_info, output_dirs)
        
        return {
            "case_id": case_id,
            "symptoms": [],
            "status": "error",
            "error": str(e)
        }

def main():
    parser = argparse.ArgumentParser(description="症状提取Worker脚本")
    parser.add_argument("--input_dir", type=str, help="包含原始.txt报告的目录")
    parser.add_argument("--output_dir", type=str, required=True, help="存放输出结果的目录")
    parser.add_argument("--api_key_name", type=str, required=True, help="API配置名称")
    parser.add_argument("--start_index", type=int, help="处理的起始文件索引")
    parser.add_argument("--end_index", type=int, help="处理的结束文件索引")
    parser.add_argument("--file_list", type=str, help="包含待处理文件路径的列表文件")
    parser.add_argument("--prompt_type", type=str, default="comprehensive", 
                       choices=["identification", "generation", "comprehensive", "batch"],
                       help="提示词类型")
    args = parser.parse_args()

    # 校验参数
    if args.file_list:
        logger.info(f"🚀 症状提取Worker以文件列表模式启动: API='{args.api_key_name}', 任务文件='{args.file_list}'")
    elif args.input_dir and args.start_index is not None and args.end_index is not None:
        logger.info(f"🚀 症状提取Worker以范围模式启动: API='{args.api_key_name}', 范围=[{args.start_index}, {args.end_index})")
    else:
        logger.error("参数错误: 必须提供 '--file_list' 或者 '--input_dir', '--start_index' 和 '--end_index'")
        return

    # 1. 初始化API配置和提取器
    api_config = MULTI_API_CONFIG.get(args.api_key_name)
    if not api_config:
        logger.error(f"未找到API配置: {args.api_key_name}")
        return

    extractor = SymptomExtractor(
        model=api_config["model"],
        api_key=api_config["api_key"],
        base_url=api_config["base_url"]
    )

    # 2. 初始化文档处理器
    processor = DocumentProcessor()

    # 3. 获取提示词
    prompt = get_prompt_by_task(args.prompt_type)
    logger.info(f"使用提示词类型: {args.prompt_type}")

    # 4. 创建输出目录结构
    worker_output_dir = os.path.join(args.output_dir, f"worker_{args.api_key_name}")
    os.makedirs(worker_output_dir, exist_ok=True)

    output_dirs = {
        "json": os.path.join(worker_output_dir, "symptom_results"),
        "txt": os.path.join(worker_output_dir, "symptom_summaries"),
        "logs": os.path.join(worker_output_dir, "processing_logs")
    }

    for dir_path in output_dirs.values():
        os.makedirs(dir_path, exist_ok=True)

    logger.info(f"Worker输出目录: {worker_output_dir}")

    # 5. 加载待处理报告
    if args.file_list:
        reports_to_process = load_reports_from_list(args.file_list)
    else:
        reports_to_process = load_reports_in_range(args.input_dir, args.start_index, args.end_index)

    if not reports_to_process:
        logger.warning("未加载到任何报告，Worker退出")
        return

    # 6. 处理报告
    total_processed = 0
    total_symptoms = 0
    successful_cases = 0
    
    logger.info(f"开始处理 {len(reports_to_process)} 个报告...")

    for i, report in enumerate(reports_to_process):
        try:
            logger.info(f"处理进度: {i+1}/{len(reports_to_process)} - {report['case_id']}")
            
            result = process_single_report(report, extractor, processor, prompt, output_dirs)
            
            total_processed += 1
            if result["status"] == "completed":
                successful_cases += 1
                total_symptoms += len(result["symptoms"])
            
            # 显示处理统计
            if (i + 1) % 10 == 0 or i == len(reports_to_process) - 1:
                logger.info(f"处理统计: {total_processed}/{len(reports_to_process)} 已处理, "
                          f"{successful_cases} 成功, 共提取 {total_symptoms} 个症状")
                
        except Exception as e:
            logger.error(f"处理报告 {i} 时发生异常: {str(e)}")
            continue

    # 7. 生成最终统计报告
    final_stats = {
        "worker_name": args.api_key_name,
        "total_reports": len(reports_to_process),
        "processed_reports": total_processed,
        "successful_reports": successful_cases,
        "total_symptoms_extracted": total_symptoms,
        "success_rate": successful_cases / total_processed if total_processed > 0 else 0,
        "avg_symptoms_per_report": total_symptoms / successful_cases if successful_cases > 0 else 0,
        "completion_time": datetime.now().isoformat(),
        "prompt_type": args.prompt_type
    }

    stats_file = os.path.join(worker_output_dir, "worker_statistics.json")
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(final_stats, f, ensure_ascii=False, indent=2)

    logger.success(f"🎉 Worker {args.api_key_name} 处理完成!")
    logger.info(f"📊 最终统计: {successful_cases}/{total_processed} 成功处理, 共提取 {total_symptoms} 个症状")
    logger.info(f"📁 结果保存在: {worker_output_dir}")

if __name__ == "__main__":
    main() 