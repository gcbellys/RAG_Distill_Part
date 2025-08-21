#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diag_Distillation Process Worker - 三步分离式诊断蒸馏系统

该脚本实现新的三步诊断蒸馏逻辑：
1. 步骤1：从患者陈述中提取主诉症状
2. 步骤2：从医生诊断中提取器官信息  
3. 步骤3：将症状-器官映射到具体解剖部位

使用方法:
python3 process_worker.py --input_dir dataset/ --output_dir results/ --api_key_name api_13 --start_index 10001 --end_index 10001
"""

import os
import sys
import argparse
import json
import re
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# 导入配置
sys.path.append('/opt/RAG_Evidence4Organ')
from configs.system_config import MULTI_API_CONFIG
from configs.model_config import ALLOWED_ORGANS, ORGAN_ANATOMY_STRUCTURE, ELSE_STRUCT, normalize_organ
from Question_Distillation_v2.extractors.llm_extractor import LLMExtractor
from Diag_Distillation.prompts.medical_prompts import DiagnosticExtractionPrompts, get_prompt_by_step
from configs.model_config import ORGAN_ANATOMY_STRUCTURE

# 导入logger
try:
    from loguru import logger
except ImportError:
    # 如果没有loguru，创建一个简单的logger
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

def print_header():
    """打印系统启动信息"""
    print("=" * 80)
    print("🏥 Diag_Distillation - 三步分离式诊断蒸馏系统")
    print("=" * 80)
    print(f"⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📍 工作目录: {os.getcwd()}")
    print("📋 蒸馏流程:")
    print("   步骤1: 患者陈述症状提取")
    print("   步骤2: 医生诊断器官提取") 
    print("   步骤3: 症状-器官解剖映射")
    print("-" * 80)

def print_progress(current, total, start_time):
    """打印进度信息"""
    elapsed = time.time() - start_time
    if current > 0:
        eta = (elapsed / current) * (total - current)
        eta_str = f"{int(eta//60)}:{int(eta%60):02d}"
    else:
        eta_str = "未知"
    
    percentage = (current / total) * 100 if total > 0 else 0
    print(f"📊 进度: [{current}/{total}] {percentage:.1f}% | ⏱️ 已用: {int(elapsed//60)}:{int(elapsed%60):02d} | 🔮 预计剩余: {eta_str}")

def print_step_info(step_num, step_name, chunk_count=None):
    """打印步骤信息"""
    step_prefix = f"🔍 步骤{step_num}"
    if chunk_count:
        print(f"{step_prefix} {step_name} (处理 {chunk_count} 个文本块)")
    else:
        print(f"{step_prefix} {step_name}")

def print_api_call_info(api_name, report_num, step, chunk_index=None):
    """打印API调用信息"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    if chunk_index is not None:
        print(f"🌐 [{timestamp}] API调用: {api_name} | 报告: {report_num} | 步骤: {step} | 块: {chunk_index}")
    else:
        print(f"🌐 [{timestamp}] API调用: {api_name} | 报告: {report_num} | 步骤: {step}")

def print_extraction_summary(results):
    """打印提取结果摘要（兼容多种结构）"""
    print("📋 提取结果摘要:")

    # Handle the {"raw": ..., "normalized": ...} wrapper
    if isinstance(results, dict) and "raw" in results:
        # Prefer summarizing the normalized output if available
        if "normalized" in results and results["normalized"]:
            results = results["normalized"]
        else:
            results = results.get("raw") or {}

    # NEW: Handle the final normalized list structure: [{"s_symptom":...}]
    if isinstance(results, list) and results and "s_symptom" in results[0]:
        symptom_count = len(results)
        unit_count = sum(len(item.get("U_unit_set", [])) for item in results)
        print(f"   ✅ 标准化症状条目: {symptom_count}")
        print(f"   ✅ 标准化诊断单元总数: {unit_count}")
        if symptom_count > 0:
            first = results[0]
            s_symptom = first.get("s_symptom", "-")
            first_unit_set = first.get("U_unit_set", [])
            if first_unit_set:
                first_unit = first_unit_set[0].get("u_unit", {})
                d_diagnosis = first_unit.get("d_diagnosis", "-")
                organName = (first_unit.get("o_organ", {}) or {}).get("organName", "-")
                print(f"   👉 示例: 症状='{s_symptom}' | 诊断='{d_diagnosis}' | 器官='{organName}'")
            else:
                print(f"   👉 示例: 症状='{s_symptom}' | (无诊断单元)")
        return

    if not isinstance(results, dict):
        print(f"   ❌ 结果格式异常: {type(results)}")
        return

    # 优先：step3 样式
    if "symptom_organ_mappings" in results and isinstance(results["symptom_organ_mappings"], list):
        mappings = results.get("symptom_organ_mappings", [])
        count = len(mappings)
        print(f"   ✅ 症状-器官映射条数: {count}")
        if count > 0:
            first = mappings[0]
            ps = first.get("patient_symptom", "-")
            og = first.get("diagnosed_organ", "-")
            locs = first.get("anatomical_locations", [])
            print(f"   👉 示例: 症状='{ps}' | 器官='{og}' | 解剖部位={', '.join(locs[:3])}")
        return

    # 次优：整合提示词完整结构（step1/2/3）
    has_any = False
    if "step1_patient_complaints" in results:
        pcs = (results["step1_patient_complaints"] or {}).get("complaint_sections", [])
        print(f"   ✅ 患者陈述段落: {len(pcs)}")
        has_any = has_any or bool(pcs)
    if "step2_physician_diagnoses" in results:
        dss = (results["step2_physician_diagnoses"] or {}).get("diagnostic_sections", [])
        print(f"   ✅ 医生诊断段落: {len(dss)}")
        has_any = has_any or bool(dss)
    if "step3_anatomical_mappings" in results:
        maps = (results["step3_anatomical_mappings"] or {}).get("symptom_organ_mappings", [])
        print(f"   ✅ 症状-器官映射: {len(maps)}")
        has_any = has_any or bool(maps)
    if has_any:
        return

    # 兼容：旧式扁平字段（不再推荐）
    if results.get('patient_symptom'):
        print(f"   ✅ 患者症状: {results['patient_symptom'][:50]}...")
    else:
        print("   ❌ 患者症状: 未提取到")
    
    if results.get('diagnosed_organ'):
        print(f"   ✅ 诊断器官: {results['diagnosed_organ']}")
    else:
        print("   ❌ 诊断器官: 未提取到")
    
    if results.get('anatomical_locations'):
        locations = ', '.join(results['anatomical_locations'])
        print(f"   ✅ 解剖部位: {locations}")
    else:
        print("   ❌ 解剖部位: 未提取到")
    
    confidence = results.get('confidence', 'unknown')
    print(f"   📈 置信度: {confidence}")

def print_error_info(error, report_num, step=None):
    """打印错误信息"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    step_info = f" | 步骤: {step}" if step else ""
    print(f"❌ [{timestamp}] 错误 - 报告: {report_num}{step_info}")
    print(f"   错误详情: {str(error)}")

def print_file_save_info(filepath, success=True):
    """打印文件保存信息"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    if success:
        print(f"💾 [{timestamp}] 文件已保存: {filepath}")
    else:
        print(f"❌ [{timestamp}] 文件保存失败: {filepath}")

def numeric_sort_key(s: str):
    """为数字排序生成key, e.g., 'report_1.txt' < 'report_2.txt' < 'report_10.txt'"""
    match = re.search(r'report_(\d+)\.txt', s)
    if match:
        return int(match.group(1))
    return 0

def load_reports_from_list(file_path: str) -> List[Dict[str, Any]]:
    """从一个文件列表文件中加载报告"""
    print(f"正在从任务列表 {file_path} 加载报告...")
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
                print(f"❌ 读取报告文件 {report_path} 失败: {e}")
        
        print(f"✅ 成功从任务列表加载 {len(reports)} 条报告用于处理。")
        return reports
    except Exception as e:
        print(f"❌ 加载任务列表文件 {file_path} 时发生未知错误: {e}")
        return []

def load_reports_in_range(directory_path: str, start_index: int, end_index: int) -> List[Dict[str, Any]]:
    """从目录加载指定范围内的.txt报告 (使用自然排序)"""
    print(f"正在从目录 {directory_path} 加载索引范围 {start_index}-{end_index} 的报告...")
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
                print(f"❌ 读取文件 {filename} 失败: {e}")
        
        print(f"✅ 成功加载 {len(reports)} 条报告用于处理。")
        return reports
    except Exception as e:
        print(f"❌ 加载目录 {directory_path} 时发生未知错误: {e}")
        return []

def validate_diagnostic_extraction(extraction: Dict[str, Any]) -> bool:
    """验证诊断提取结果的完整性"""
    required_fields = {
        'step1_patient_complaints': ['complaint_sections'],
        'step2_physician_diagnoses': ['diagnostic_sections'], 
        'step3_anatomical_mappings': ['symptom_organ_mappings']
    }
    
    for step, fields in required_fields.items():
        if step not in extraction:
            print(f"⚠️ 诊断提取缺少步骤: {step}")
            return False
        for field in fields:
            if field not in extraction[step]:
                print(f"⚠️ 步骤 {step} 缺少字段: {field}")
                return False
    
    return True

def parse_diagnostic_response(response_text, step_name):
    """
    解析LLM返回的诊断结果，处理各种可能的格式
    """
    if not response_text:
        print(f"   ⚠️ {step_name}: API返回空响应")
        return None
    
    print(f"   📄 {step_name}: 收到响应 ({len(response_text)} 字符)")
    
    # 如果response_text是字典，提取response字段
    if isinstance(response_text, dict):
        if 'response' in response_text:
            response_text = response_text['response']
            print(f"   🔧 {step_name}: 从字典中提取response字段")
        else:
            print(f"   ❌ {step_name}: 字典响应中缺少response字段")
            return None
    
    # 尝试提取JSON
    json_patterns = [
        r'```json\s*(\{.*?\})\s*```',  # ```json {...} ```
        r'```\s*(\{.*?\})\s*```',      # ``` {...} ```  
        r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'  # 匹配嵌套的JSON对象
    ]
    
    for i, pattern in enumerate(json_patterns, 1):
        matches = re.findall(pattern, response_text, re.DOTALL)
        if matches:
            print(f"   🎯 {step_name}: 使用模式{i}找到JSON")
            json_str = matches[0] if isinstance(matches[0], str) else matches[0]
            try:
                result = json.loads(json_str)
                print(f"   ✅ {step_name}: JSON解析成功")
                return result
            except json.JSONDecodeError as e:
                print(f"   ⚠️ {step_name}: JSON解析失败 (模式{i}): {e}")
                continue
    
    print(f"   ❌ {step_name}: 所有JSON提取模式都失败")
    print(f"   📝 {step_name}: 原始响应前200字符: {response_text[:200]}...")
    return None

def smart_chunk_medical_report(text: str) -> List[Dict[str, str]]:
    """
    基于医学报告结构进行智能分块，专门为诊断蒸馏优化
    返回: [{"section": "章节名", "content": "内容", "type": "类型"}, ...]
    """
    import re
    
    # 优化的章节模式，分为患者陈述和医生诊断两类
    patient_section_patterns = [
        (r'chief complaint:?', 'chief complaint'),
        (r'history of present illness:?', 'history of present illness'),
        (r'present illness:?', 'present illness'),
        (r'complaint:?', 'patient complaint'),
        (r'patient reports:?', 'patient reports'),
        (r'patient states:?', 'patient states'),
        (r'patient complains of:?', 'patient complains'),
        (r'subjective:?', 'subjective'),
        (r'symptoms:?', 'symptoms'),
        (r'clinical symptoms:?', 'clinical symptoms')
    ]
    
    physician_section_patterns = [
        (r'assessment and plan:?', 'assessment and plan'),
        (r'assessment:?', 'assessment'),
        (r'impression:?', 'impression'),
        (r'diagnosis:?', 'diagnosis'),
        (r'plan:?', 'treatment plan'),
        (r'discharge diagnosis:?', 'discharge diagnosis'),
        (r'brief hospital course:?', 'hospital course'),
        # 新增常见诊断/判断章节别名
        (r'final diagnosis:?', 'final diagnosis'),
        (r'clinical impression:?', 'clinical impression'),
        (r'medical decision making:?', 'medical decision making'),
        (r'\bmdm\b:?', 'medical decision making'),
        (r'findings:?', 'findings'),
        (r'ed course:?', 'ed course'),
        (r'emergency department course:?', 'ed course'),
        (r'plan and recommendations:?', 'plan and recommendations'),
        (r'disposition:?', 'disposition')
    ]
    
    chunks = []
    text_lower = text.lower()
    processed_ranges = []
    
    # 处理患者陈述章节
    for pattern, canonical_name in patient_section_patterns:
        matches = list(re.finditer(pattern, text_lower))
        for match in matches:
            start_pos = match.start()
            
            # 检查重叠
            is_overlapping = any(
                abs(start_pos - existing_start) < 300
                for existing_start, _ in processed_ranges
            )
            if is_overlapping:
                continue
            
            # 找到章节结束位置
            end_pos = len(text)
            for next_pattern, _ in patient_section_patterns + physician_section_patterns:
                next_matches = list(re.finditer(next_pattern, text_lower[start_pos + len(match.group()):]))
                if next_matches:
                    potential_end = start_pos + len(match.group()) + next_matches[0].start()
                    if potential_end > start_pos and potential_end < end_pos:
                        end_pos = potential_end
            
            section_content = text[start_pos:end_pos].strip()
            if len(section_content) > 100:  # 最小长度要求
                chunks.append({
                    "section": f"patient_{canonical_name}",
                    "content": section_content,
                    "type": "patient_complaint"
                })
                processed_ranges.append((start_pos, end_pos))
                print(f"   🔍 识别到患者陈述章节: '{canonical_name}' ({len(section_content)} 字符)")
                break
    
    # 处理医生诊断章节
    for pattern, canonical_name in physician_section_patterns:
        matches = list(re.finditer(pattern, text_lower))
        for match in matches:
            start_pos = match.start()
            
            # 检查重叠
            is_overlapping = any(
                abs(start_pos - existing_start) < 300
                for existing_start, _ in processed_ranges
            )
            if is_overlapping:
                continue
            
            # 找到章节结束位置
            end_pos = len(text)
            for next_pattern, _ in physician_section_patterns:
                next_matches = list(re.finditer(next_pattern, text_lower[start_pos + len(match.group()):]))
                if next_matches:
                    potential_end = start_pos + len(match.group()) + next_matches[0].start()
                    if potential_end > start_pos and potential_end < end_pos:
                        end_pos = potential_end
            
            section_content = text[start_pos:end_pos].strip()
            if len(section_content) > 100:  # 最小长度要求
                chunks.append({
                    "section": f"physician_{canonical_name}",
                    "content": section_content,
                    "type": "physician_diagnosis"
                })
                processed_ranges.append((start_pos, end_pos))
                print(f"   🔍 识别到医生诊断章节: '{canonical_name}' ({len(section_content)} 字符)")
                break
    
    if not chunks:
        print("⚠️ 未找到标准章节，使用整体处理")
        return [{
            "section": "full_report",
            "content": text,
            "type": "mixed"
        }]
    
    print(f"   📊 智能分块完成，共 {len(chunks)} 个有效块")
    return chunks

def _fallback_extract_organs_on_full_text(extractor, report_text, prompts, report_num, api_key_name):
    """
    一个回退函数，当智能分块未能识别到任何医生诊断章节时，
    该函数会在整个报告文本上运行一次器官提取。
    """
    results = []
    try:
        print_api_call_info(api_key_name, report_num, "器官提取-整篇回退")
        prompt = prompts.get_step2_diagnosis_organ_extraction_prompt(report_text).replace("{text_content}", report_text)
        response = extractor.call_api(prompt)
        parsed = parse_diagnostic_response(response, "器官提取-整篇回退")
        if parsed:
            results.append(parsed)
            print("   ✅ 整篇回退: 成功提取器官")
        else:
            print("   ⚠️ 整篇回退: 器官提取失败")
    except Exception as e:
        print_error_info(e, report_num, "器官提取-整篇回退")
    return results

def _normalize_outputs(step1_results: List[Dict[str, Any]], step2_results: List[Dict[str, Any]], mapping_result: Dict[str, Any], original_text: str) -> List[Dict[str, Any]]:
    """
    将三步结果规范化为所需结构：
    按照新的JSON结构输出：s_symptom -> U_unit_set -> u_unit -> (d_diagnosis, o_organ, b_textual_basis)
    
    严格约束：
    1. 只使用预定义的器官列表
    2. 必须有具体的解剖位置（不能是"General area"等）
    3. 无法确定器官的症状直接过滤掉
    """
    # _organ_key_match函数已删除，现在使用configs/model_config.py中的normalize_organ函数
    
    def _is_body_system_match(body_system: str, organ_name: str) -> bool:
        """检查身体系统是否与器官匹配"""
        system_organ_map = {
            "cardiovascular": ["Heart (Cor)", "Artery (Arteria)", "Vein (Vena)"],
            "respiratory": ["Lung (Pulmo)", "Trachea", "Bronchus"],
            "gastrointestinal": ["Liver (Hepar)", "Stomach (Gaster)", "Pancreas", "Esophagus"],
            "neurological": ["Brain", "Cerebellum", "Brainstem"],
            "genitourinary": ["Kidney (Ren)", "Urinary bladder (Vesica urinaria)"],
            "endocrine": ["Thyroid gland", "Pancreas", "Adrenal gland (Suprarenal gland)"]
        }
        
        for organ in system_organ_map.get(body_system, []):
            if organ.lower() in organ_name.lower() or organ_name.lower() in organ.lower():
                return True
        return False
    
    def _get_default_anatomical_locations(organ_name: str) -> list:
        """为器官获取默认的解剖位置"""
        normalized_organ = normalize_organ(organ_name)
        if normalized_organ in ORGAN_ANATOMY_STRUCTURE:
            return ORGAN_ANATOMY_STRUCTURE[normalized_organ][:2]  # 返回前2个位置
        return ["General area", "Main structure"]

    # （本段保留空行用于可读性）

    # ---------------------- 以上：新增工具函数 ----------------------

    # --- 使用model_config.py中的完整器官列表 ---
    # ALLOWED_ORGANS 现在从 configs/model_config.py 导入，包含55个器官
    print(f"   🔧 使用完整器官列表: {len(ALLOWED_ORGANS)} 个器官")
    
    # 器官名称标准化函数现在从 model_config.py 导入

    print("   🔄 开始标准化新的描述性内容结构...")
    
    # 收集所有描述性发现 (s_symptom) - 适配新的数据结构
    all_descriptive_findings = []
    
    # 从step1结果中提取描述性发现
    for obj in (step1_results or []):
        try:
            # 新结构：从descriptive_findings中提取
            findings = obj.get("descriptive_findings", [])
            for finding in findings:
                if finding and isinstance(finding, dict):
                    finding_text = finding.get("finding_text", "")
                    if finding_text:
                        all_descriptive_findings.append({
                            "s_symptom": finding_text,
                            "finding_type": finding.get("finding_type", "unknown"),
                            "source_quote": finding.get("source_quote", ""),
                            "body_system": finding.get("body_system", "other"),
                            "confidence": finding.get("extraction_confidence", "medium")
                        })
            
            # 兼容旧结构：从symptom_sections中提取
            sections = obj.get("symptom_sections", []) or obj.get("patient_complaint_sections", [])
            for sec in sections:
                symptoms = sec.get("extracted_symptoms", []) or sec.get("main_symptoms", [])
                for symptom in symptoms:
                    if symptom and isinstance(symptom, str):
                        all_descriptive_findings.append({
                            "s_symptom": symptom,
                            "finding_type": "patient_symptom",
                            "source_quote": sec.get("original_text", ""),
                            "body_system": "other",
                            "confidence": "medium"
                        })
            
            print(f"   📊 从step1提取到 {len(findings)} 个描述性发现")
        except Exception as e:
            print(f"   ⚠️ 描述性发现解析错误: {e}")
            continue
    
    # 收集所有医生诊断
    all_diagnoses = []
    
    # 从step2结果中提取诊断
    for obj in (step2_results or []):
        try:
            # 新结构：从physician_diagnoses中提取
            diagnoses = obj.get("physician_diagnoses", [])
            for diagnosis in diagnoses:
                if diagnosis and isinstance(diagnosis, dict):
                    diagnosis_text = diagnosis.get("diagnosis_text", "")
                    affected_organs = diagnosis.get("affected_organs", [])
                    if diagnosis_text and affected_organs:
                        all_diagnoses.append({
                            "diagnosis": diagnosis_text,
                            "organs": affected_organs,
                            "source_quote": diagnosis.get("source_quote", ""),
                            "confidence": diagnosis.get("extraction_confidence", "medium")
                        })
            
            # 兼容旧结构：从diagnostic_sections中提取
            sections = obj.get("diagnostic_sections", [])
            for sec in sections:
                mentioned_organs = sec.get("mentioned_organs", [])
                for organ_info in mentioned_organs:
                    if isinstance(organ_info, dict):
                        organ_name = organ_info.get("organ_name", "")
                        context = organ_info.get("context", "")
                        if organ_name and context:
                            all_diagnoses.append({
                                "diagnosis": context,
                                "organs": [{"organ_name": organ_name, "organ_confidence": "medium", "organ_basis": context}],
                                "source_quote": sec.get("original_text", ""),
                                "confidence": "medium"
                            })
            
            print(f"   📊 从step2提取到 {len(diagnoses)} 个医生诊断")
        except Exception as e:
            print(f"   ⚠️ 诊断解析错误: {e}")
            continue

    # 获取症状-器官映射
    mapping_list = (mapping_result or {}).get("symptom_organ_mappings", []) if isinstance(mapping_result, dict) else []
    print(f"   📊 获取到 {len(mapping_list)} 个症状-器官映射")

    # 构建最终标准化输出结构: s → U
    final_output = []
    
    # 🔧 修复：从映射中提取所有唯一症状，而不仅仅依赖Step1
    all_unique_symptoms = set()
    
    # 从描述性发现中收集症状
    for finding in all_descriptive_findings:
        all_unique_symptoms.add(finding["s_symptom"])
    
    # 从映射中收集额外的症状（防止Step1遗漏）
    for mp in mapping_list:
        if isinstance(mp, dict) and mp.get("patient_symptom"):
            all_unique_symptoms.add(mp.get("patient_symptom"))
    
    print(f"   📊 发现 {len(all_unique_symptoms)} 个唯一症状需要处理")
    
    for s_symptom in all_unique_symptoms:
        print(f"   🔍 处理症状: {s_symptom}")
        
        # 为每个症状构建U_unit_set
        U_unit_set = []
        
        # 找到与该症状相关的所有映射
        symptom_mappings = []
        for mp in mapping_list:
            if isinstance(mp, dict) and mp.get("patient_symptom") == s_symptom:
                symptom_mappings.append(mp)
        
        # 如果没有直接映射，尝试通过诊断信息创建映射
        if not symptom_mappings:
            # 查找对应的描述性发现信息（如果存在）
            finding_info = None
            for finding in all_descriptive_findings:
                if finding["s_symptom"] == s_symptom:
                    finding_info = finding
                    break
            
            # 根据描述性发现的body_system尝试匹配相关诊断
            finding_body_system = finding_info.get("body_system", "other") if finding_info else "other"
            
            for diagnosis in all_diagnoses:
                for organ_info in diagnosis.get("organs", []):
                    organ_name = organ_info.get("organ_name", "")
                    if organ_name and _is_body_system_match(finding_body_system, organ_name):
                        # 创建映射
                        synthetic_mapping = {
                            "patient_symptom": s_symptom,
                            "diagnosed_organ": organ_name,
                            "anatomical_locations": _get_default_anatomical_locations(organ_name),
                            "text_evidence": {
                                "symptom_source": finding_info.get("source_quote", "") if finding_info else "",
                                "diagnosis_source": diagnosis.get("source_quote", ""),
                                "anatomical_basis": f"Based on {finding_body_system} system involvement and diagnosis context."
                            }
                        }
                        symptom_mappings.append(synthetic_mapping)
                        print(f"   🔗 创建合成映射: {s_symptom} -> {organ_name}")
                        break
        
        # 处理找到的映射
        for mp in symptom_mappings:
            organ_name_raw = mp.get("diagnosed_organ", "")
            normalized_organ = normalize_organ(organ_name_raw)
            locations = mp.get("anatomical_locations", []) or []
            
            # 器官验证：使用normalize_organ函数和完整的ALLOWED_ORGANS列表
            if normalized_organ == "unknown" or normalized_organ not in ALLOWED_ORGANS:
                print(f"   🗑️ 过滤掉非预定义器官: {organ_name_raw} -> {normalized_organ}")
                continue
            
            # 严格解剖位置验证：必须有具体位置，不能是模糊描述
            if not locations:
                print(f"   🗑️ 过滤掉无解剖位置的症状: {s_symptom}")
                continue
            
            # 过滤掉模糊的解剖位置描述
            vague_locations = ["general area", "multiple systems", "general", "unspecified", "unknown"]
            filtered_locations = []
            for loc in locations:
                loc_lower = loc.lower()
                if not any(vague in loc_lower for vague in vague_locations):
                    filtered_locations.append(loc)
            
            # 如果过滤后没有具体位置，跳过这个症状
            if not filtered_locations:
                print(f"   🗑️ 过滤掉只有模糊解剖位置的症状: {s_symptom} -> {normalized_organ}")
                continue
            
            # 确保至少有2个具体的解剖位置
            if len(filtered_locations) < 2:
                # 从预定义结构中补充具体位置
                if normalized_organ in ORGAN_ANATOMY_STRUCTURE:
                    available = [loc for loc in ORGAN_ANATOMY_STRUCTURE[normalized_organ] 
                               if loc not in filtered_locations and 
                               not any(vague in loc.lower() for vague in vague_locations)]
                    while len(filtered_locations) < 2 and available:
                        filtered_locations.append(available.pop(0))
                
                # 如果仍然少于2个，跳过这个症状
                if len(filtered_locations) < 2:
                    print(f"   🗑️ 过滤掉解剖位置不足的症状: {s_symptom} -> {normalized_organ} (只有{len(filtered_locations)}个位置)")
                    continue
            
            # 构建u_unit
            text_evidence = mp.get("text_evidence", {}) or {}
            
            # 验证诊断信息 - 适配新结构
            diagnosis = text_evidence.get("diagnosis_source", "") or text_evidence.get("organ_source", "")
            if not diagnosis or diagnosis.lower() in ["unknown", "unknown diagnosis", "n/a"]:
                print(f"   🗑️ 过滤掉诊断信息不明的症状: {s_symptom}")
                continue
            
            u_unit = {
                "d_diagnosis": diagnosis,
                "o_organ": {
                    "organName": normalized_organ,
                    "anatomicalLocations": filtered_locations[:3]  # 最多3个位置
                },
                "b_textual_basis": {
                    "doctorsDiagnosisAndJudgment": diagnosis,
                    "medicalInference": text_evidence.get("anatomical_basis", f"Clinical evidence indicates {normalized_organ} involvement with specific anatomical locations: {', '.join(filtered_locations)}.")
                }
            }
            U_unit_set.append({"u_unit": u_unit})
            print(f"   ✅ 成功创建诊断单元: {s_symptom} -> {normalized_organ} -> {filtered_locations}")
        
        # 关键约束：如果U_unit_set为空，直接跳过这个描述性发现，不记录在JSON中
        if not U_unit_set:
            print(f"   🗑️ 描述性发现 '{s_symptom}' 无法确定器官或解剖位置，已过滤掉")
            continue
        
        # 构建最终的s_symptom条目 - 标准化格式 s → U（恢复无条件加入）
        final_output.append({
            "s_symptom": s_symptom,
            "U_unit_set": U_unit_set
        })
    
    print(f"   📊 最终输出: {len(final_output)} 个有效症状（已过滤掉无法确定器官的症状）")
    return final_output

def process_report_with_diagnostic_steps(extractor, report_data, report_num, prompts, api_key_name):
    """
    使用三步诊断法处理单个报告
    """
    print(f"\n🏥 开始处理报告 {report_num}")
    print("-" * 60)
    
    # 获取报告文本 (兼容txt和json格式)
    report_text = report_data.get('text', '') or report_data.get('medical_record_content', '')
    if not report_text:
        print(f"❌ 报告 {report_num}: 缺少医疗记录内容")
        return None
    
    print(f"📄 报告内容长度: {len(report_text)} 字符")
    
    # 第一步：智能分块和分类
    print_step_info(1, "智能分块和症状提取")
    chunks = smart_chunk_medical_report(report_text)
    patient_chunks = [chunk for chunk in chunks if chunk.get('type') == 'patient_complaint']
    physician_chunks = [chunk for chunk in chunks if chunk.get('type') == 'physician_diagnosis']
    
    print(f"   📊 总块数: {len(chunks)} | 患者陈述块: {len(patient_chunks)} | 医生诊断块: {len(physician_chunks)}")
    
    # 第二步：从患者陈述和其他章节中提取描述性内容（症状、检查、体征）
    print_step_info(2, "综合描述性内容提取", len(patient_chunks))
    patient_symptoms = []
    
    # 优先处理患者陈述块 - 提取描述性内容
    for i, chunk in enumerate(patient_chunks):
        print_api_call_info(api_key_name, report_num, "描述性内容提取", i+1)
        try:
            prompt = prompts.get_step1_comprehensive_descriptive_extraction_prompt(chunk['content'])
            response = extractor.call_api(prompt)
            parsed = parse_diagnostic_response(response, f"描述性内容提取-块{i+1}")
            if parsed and parsed.get("descriptive_findings"):
                patient_symptoms.append(parsed)
                findings_count = len(parsed.get('descriptive_findings', []))
                excluded_count = len(parsed.get('excluded_content', []))
                print(f"   ✅ 块{i+1}: 提取{findings_count}个描述性发现，排除{excluded_count}个诊断判断")
            else:
                print(f"   ⚠️ 块{i+1}: 未发现有效描述性内容")
        except Exception as e:
            print_error_info(e, report_num, f"描述性内容提取-块{i+1}")
    
    # 如果患者陈述块中没有提取到足够症状，尝试从其他章节提取
    if not patient_symptoms or len(patient_symptoms) < 2:
        print("   🔍 患者陈述块症状不足，尝试从医生诊断的叙事章节提取症状")
        
        # 智能选择可能包含症状的医生诊断块（偏向叙事性）
        narrative_physician_chunks = [
            chunk for chunk in physician_chunks 
            if any(keyword in chunk['section'] for keyword in ['course', 'history', 'narrative'])
        ]

        # 从筛选出的医生诊断块中寻找描述性内容
        for i, chunk in enumerate(narrative_physician_chunks):
            print_api_call_info(api_key_name, report_num, f"描述性内容提取-医生叙事块{i+1}")
            try:
                prompt = prompts.get_step1_comprehensive_descriptive_extraction_prompt(chunk['content'])
                response = extractor.call_api(prompt)
                parsed = parse_diagnostic_response(response, f"描述性内容提取-医生叙事块{i+1}")
                if parsed and parsed.get("descriptive_findings"):
                    patient_symptoms.append(parsed)
                    findings_count = len(parsed.get('descriptive_findings', []))
                    print(f"   ✅ 医生叙事块{i+1}: 提取{findings_count}个描述性发现")
            except Exception as e:
                print_error_info(e, report_num, f"描述性内容提取-医生叙事块{i+1}")
    
    # 如果仍然没有描述性内容，尝试从整篇文本提取
    if not patient_symptoms:
        print("   🔍 分块描述性内容提取失败，尝试从整篇文本提取")
        try:
            prompt = prompts.get_step1_comprehensive_descriptive_extraction_prompt(report_text)
            response = extractor.call_api(prompt)
            parsed = parse_diagnostic_response(response, "整篇描述性内容提取")
            if parsed and parsed.get("descriptive_findings"):
                patient_symptoms.append(parsed)
                findings_count = len(parsed.get('descriptive_findings', []))
                excluded_count = len(parsed.get('excluded_content', []))
                print(f"   ✅ 整篇文本: 提取{findings_count}个描述性发现，排除{excluded_count}个诊断判断")
            else:
                print("   ⚠️ 整篇文本: 未发现有效描述性内容")
        except Exception as e:
            print_error_info(e, report_num, "整篇描述性内容提取")
    
    # 第三步：从医生诊断中提取器官
    print_step_info(3, "医生诊断器官提取", len(physician_chunks))
    diagnosed_organs = []
    
    for i, chunk in enumerate(physician_chunks):
        print_api_call_info(api_key_name, report_num, "器官提取", i+1)
        try:
            prompt = prompts.get_step2_diagnosis_organ_extraction_prompt(chunk['content']).replace("{text_content}", chunk['content'])
            response = extractor.call_api(prompt)
            parsed = parse_diagnostic_response(response, f"器官提取-块{i+1}")
            if parsed:
                diagnosed_organs.append(parsed)
                print(f"   ✅ 块{i+1}: 成功提取器官")
            else:
                print(f"   ⚠️ 块{i+1}: 器官提取失败")
        except Exception as e:
            print_error_info(e, report_num, f"器官提取-块{i+1}")

    # 回退：若未识别到医生诊断块或未能提取出器官，则对整篇文本执行一次器官提取
    if not physician_chunks or not diagnosed_organs:
        print("   ⚠️ 未识别到有效医生诊断块或器官，触发整篇器官提取回退")
        fallback_results = _fallback_extract_organs_on_full_text(extractor, report_text, prompts, report_num, api_key_name)
        diagnosed_organs.extend([res for res in fallback_results if res])
    
    # 第四步：整合结果并进行解剖映射
    print_step_info(4, "症状-器官解剖映射")
    final_step3_result = None
    if patient_symptoms and diagnosed_organs:
        print_api_call_info(api_key_name, report_num, "解剖映射")
        try:
            prompt = prompts.get_step3_anatomical_mapping_prompt(
                patient_symptoms, diagnosed_organs, report_text
            )
            response = extractor.call_api(prompt)
            final_step3_result = parse_diagnostic_response(response, "解剖映射")
            
            if final_step3_result:
                print("   ✅ 解剖映射成功")
                print_extraction_summary(final_step3_result)
            else:
                print("   ⚠️ 解剖映射失败")
        except Exception as e:
            print_error_info(e, report_num, "解剖映射")
    else:
        print("   ⚠️ 缺少症状或器官信息，跳过解剖映射")
    
    # 如果三步法成功，进行标准化
    if final_step3_result:
        print("   ✅ 三步法提取成功，进行标准化...")
        try:
            normalized_output = _normalize_outputs(patient_symptoms, diagnosed_organs, final_step3_result, report_text)
            return {"raw": final_step3_result, "normalized": normalized_output}
        except Exception as e:
            print_error_info(e, report_num, "标准化输出构建")
            # 如果标准化失败，将继续尝试整合提示词

    # 如果三步法失败或标准化失败，尝试使用整合提示词作为最终结果
    print_step_info("备选", "使用整合提示词重试")
    try:
        print_api_call_info(api_key_name, report_num, "整合提示词")
        prompt = prompts.get_integrated_diagnostic_prompt(report_text)
        response = extractor.call_api(prompt)
        # 整合提示词直接返回最终格式
        integrated_result = parse_diagnostic_response(response, "整合提示词")
        
        if integrated_result:
            print("   ✅ 整合提示词成功")
            # 整合提示词的结果就是标准化的结果
            print_extraction_summary(integrated_result)
            
            # 创建一个模拟的 "raw" 用于日志记录和兼容性
            raw_dummy = {
                "source": "integrated_prompt",
                "step1_patient_complaints": patient_symptoms,
                "step2_physician_diagnoses": diagnosed_organs
            }
            # 确保整合提示词的结果是列表格式
            if isinstance(integrated_result, dict):
                # 如果是单个字典，包装成标准的 s -> U 格式（恢复为占位症状）
                wrapped_result = [{
                    "s_symptom": "integrated_extraction", 
                    "U_unit_set": [{"u_unit": integrated_result}]
                }]
                return {"raw": raw_dummy, "normalized": wrapped_result}
            else:
                return {"raw": raw_dummy, "normalized": integrated_result}
        else:
            print("   ❌ 整合提示词也失败")
            # 返回部分数据以供调试
            return {
                "raw": {"step1": patient_symptoms, "step2": diagnosed_organs, "step3": None}, 
                "normalized": []
            }
            
    except Exception as e:
        print_error_info(e, report_num, "整合提示词")
        return {
            "raw": {"step1": patient_symptoms, "step2": diagnosed_organs, "step3": "error"}, 
            "normalized": []
        }

def main():
    parser = argparse.ArgumentParser(description='Diag_Distillation 三步分离式诊断蒸馏系统')
    parser.add_argument('--input_dir', type=str, required=True, help='输入目录路径')
    parser.add_argument('--output_dir', type=str, required=True, help='输出目录路径')
    parser.add_argument('--api_key_name', type=str, required=True, help='API密钥名称')
    parser.add_argument('--start_index', type=int, required=True, help='开始索引')
    parser.add_argument('--end_index', type=int, required=True, help='结束索引')
    parser.add_argument('--log_level', type=str, default='INFO', help='日志级别')
    
    args = parser.parse_args()
    
    # 打印系统启动信息
    print_header()
    
    # 打印配置信息
    print("⚙️ 运行配置:")
    print(f"   📁 输入目录: {args.input_dir}")
    print(f"   📁 输出目录: {args.output_dir}")
    print(f"   🔑 API密钥: {args.api_key_name}")
    print(f"   📊 处理范围: {args.start_index} - {args.end_index}")
    print(f"   📋 日志级别: {args.log_level}")
    print("-" * 80)
    
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(os.path.join(args.output_dir, 'diagnostic_results'), exist_ok=True)
    os.makedirs(os.path.join(args.output_dir, 'logs'), exist_ok=True)
    
    # 初始化API配置
    if args.api_key_name not in MULTI_API_CONFIG:
        print(f"❌ API密钥 '{args.api_key_name}' 不存在于配置中")
        sys.exit(1)
    
    api_config = MULTI_API_CONFIG[args.api_key_name]
    print(f"🔧 API配置: {api_config['model']} @ {api_config['base_url']}")
    
    # 初始化提取器和提示词
    extractor = LLMExtractor(
        model=api_config['model'],
        api_key=api_config['api_key'],
        base_url=api_config['base_url']
    )
    prompts = DiagnosticExtractionPrompts()
    
    print("✅ 系统初始化完成")
    print("=" * 80)
    
    # 开始处理
    start_time = time.time()
    total_files = args.end_index - args.start_index + 1
    processed_count = 0
    success_count = 0
    error_count = 0
    
    for i in range(args.start_index, args.end_index + 1):
        print_progress(processed_count, total_files, start_time)
        
        # 尝试txt文件，如果不存在则尝试json文件
        txt_file = os.path.join(args.input_dir, f'report_{i}.txt')
        json_file = os.path.join(args.input_dir, f'report_{i}.json')
        output_file = os.path.join(args.output_dir, 'diagnostic_results', f'diagnostic_{i}.json')
        
        input_file = None
        if os.path.exists(txt_file):
            input_file = txt_file
        elif os.path.exists(json_file):
            input_file = json_file
        
        if not input_file:
            print(f"⚠️ 跳过: report_{i} (txt和json文件都不存在)")
            processed_count += 1
            continue
        
        try:
            # 读取输入文件
            if input_file.endswith('.txt'):
                with open(input_file, 'r', encoding='utf-8') as f:
                    text_content = f.read()
                report_data = {
                    'text': text_content,
                    'case_id': str(i),
                    'filename': f'report_{i}.txt'
                }
                print(f"📄 读取txt文件: {input_file}")
            else:
                with open(input_file, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                print(f"📄 读取json文件: {input_file}")
            
            # 处理报告
            result = process_report_with_diagnostic_steps(extractor, report_data, i, prompts, args.api_key_name)
            
            if result:
                # 保存结果
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print_file_save_info(output_file, True)
                
                # 若包含标准化结果，另存一份更易用的JSON
                try:
                    normalized_dir = os.path.join(args.output_dir, 'diagnostic_results_normalized')
                    os.makedirs(normalized_dir, exist_ok=True)
                    normalized_file = os.path.join(normalized_dir, f'diagnostic_{i}.json')
                    normalized_payload = result.get('normalized') if isinstance(result, dict) else None
                    if normalized_payload:
                        with open(normalized_file, 'w', encoding='utf-8') as f2:
                            json.dump(normalized_payload, f2, ensure_ascii=False, indent=2)
                        print_file_save_info(normalized_file, True)
                except Exception as e:
                    print_error_info(e, i, "写入标准化JSON")
                
                success_count += 1
            else:
                print(f"❌ 报告 {i}: 处理失败")
                error_count += 1
            
        except Exception as e:
            print_error_info(e, i)
            print(f"   详细错误: {traceback.format_exc()}")
            error_count += 1
        
        processed_count += 1
        print("─" * 60)
    
    # 打印最终统计
    total_time = time.time() - start_time
    print("=" * 80)
    print("🎉 处理完成!")
    print(f"📊 最终统计:")
    print(f"   ✅ 成功: {success_count}")
    print(f"   ❌ 失败: {error_count}")
    print(f"   📁 总计: {processed_count}")
    print(f"   ⏰ 总用时: {int(total_time//60)}:{int(total_time%60):02d}")
    print(f"   📈 成功率: {(success_count/processed_count*100):.1f}%" if processed_count > 0 else "   📈 成功率: 0%")
    print("=" * 80)

if __name__ == "__main__":
    main() 