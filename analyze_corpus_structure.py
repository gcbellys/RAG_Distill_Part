#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医疗语料结构分析工具
使用API分析语料的组成成分，包括症状、诊断、治疗等信息
"""

import json
import sys
import os
from typing import Dict, List, Any
import argparse

# 添加项目路径
sys.path.append('/opt/RAG_Evidence4Organ')

from Question_Distillation_v2.extractors.llm_extractor import LLMExtractor
from configs.system_config import MULTI_API_CONFIG

class CorpusAnalyzer:
    def __init__(self, api_key_name: str = "api_16"):
        """初始化语料分析器"""
        self.api_key_name = api_key_name
        
        # 从配置中获取API信息
        if api_key_name not in MULTI_API_CONFIG:
            raise ValueError(f"API配置中未找到 {api_key_name}")
        
        api_config = MULTI_API_CONFIG[api_key_name]
        self.llm_extractor = LLMExtractor(
            model=api_config['model'],
            api_key=api_config['api_key'],
            base_url=api_config['base_url']
        )
        
    def get_analysis_prompt(self) -> str:
        """获取语料分析提示词"""
        return """
请详细分析以下医疗报告的结构和内容组成，并以JSON格式返回分析结果：

分析维度：
1. 文档类型：这是什么类型的医疗文档？
2. 主要部分：文档包含哪些主要章节？
3. 症状信息：是否包含症状描述？如果有，请列出主要症状
4. 诊断信息：是否包含诊断信息？如果有，请列出主要诊断
5. 治疗信息：是否包含治疗措施？如果有，请列出主要治疗
6. 检查结果：是否包含检查或化验结果？
7. 药物信息：是否包含药物相关信息？
8. 其他信息：还包含哪些其他医疗信息？

请以以下JSON格式返回：
{
    "document_type": "文档类型",
    "main_sections": ["主要章节1", "主要章节2"],
    "symptoms": {
        "has_symptoms": true/false,
        "symptom_list": ["症状1", "症状2"],
        "symptom_descriptions": ["对症状的详细描述"]
    },
    "diagnoses": {
        "has_diagnoses": true/false,
        "diagnosis_list": ["诊断1", "诊断2"],
        "diagnosis_details": ["诊断的详细信息"]
    },
    "treatments": {
        "has_treatments": true/false,
        "treatment_list": ["治疗1", "治疗2"],
        "treatment_details": ["治疗的详细描述"]
    },
    "lab_results": {
        "has_lab_results": true/false,
        "result_types": ["化验类型1", "化验类型2"],
        "key_findings": ["主要发现"]
    },
    "medications": {
        "has_medications": true/false,
        "medication_list": ["药物1", "药物2"],
        "medication_details": ["用药详情"]
    },
    "other_info": {
        "procedures": ["手术或操作"],
        "history": ["病史信息"],
        "physical_exam": ["体检发现"],
        "additional_notes": ["其他重要信息"]
    },
    "content_richness": {
        "symptom_richness": "丰富/中等/稀少",
        "clinical_detail_level": "详细/中等/简略",
        "overall_quality": "高/中/低"
    }
}

医疗报告内容：
{content}

请仔细分析并返回完整的JSON结果。
"""
    
    def analyze_single_report(self, file_path: str) -> Dict[str, Any]:
        """分析单个报告文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            if not content:
                return {"error": "文件为空"}
                
            # 构建提示词
            prompt = self.get_analysis_prompt().format(content=content)
            
            # 调用API
            response = self.llm_extractor.call_api(prompt)
            
            # 尝试解析JSON
            try:
                analysis_result = json.loads(response)
                analysis_result["file_path"] = file_path
                analysis_result["content_length"] = len(content)
                return analysis_result
            except json.JSONDecodeError:
                # 如果JSON解析失败，返回原始响应
                return {
                    "file_path": file_path,
                    "content_length": len(content),
                    "raw_response": response,
                    "error": "JSON解析失败"
                }
                
        except Exception as e:
            return {
                "file_path": file_path,
                "error": f"分析失败: {str(e)}"
            }
    
    def analyze_multiple_reports(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """分析多个报告文件"""
        results = []
        for i, file_path in enumerate(file_paths):
            print(f"正在分析 ({i+1}/{len(file_paths)}): {file_path}")
            result = self.analyze_single_report(file_path)
            results.append(result)
        return results
    
    def summarize_analysis(self, analysis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """汇总分析结果"""
        summary = {
            "total_files": len(analysis_results),
            "successful_analysis": 0,
            "failed_analysis": 0,
            "document_types": {},
            "symptom_statistics": {
                "files_with_symptoms": 0,
                "common_symptoms": {},
                "symptom_richness_distribution": {"丰富": 0, "中等": 0, "稀少": 0}
            },
            "diagnosis_statistics": {
                "files_with_diagnoses": 0,
                "common_diagnoses": {},
            },
            "treatment_statistics": {
                "files_with_treatments": 0,
                "common_treatments": {}
            },
            "content_quality": {
                "high_quality": 0,
                "medium_quality": 0,
                "low_quality": 0
            }
        }
        
        for result in analysis_results:
            if "error" in result:
                summary["failed_analysis"] += 1
                continue
                
            summary["successful_analysis"] += 1
            
            # 文档类型统计
            doc_type = result.get("document_type", "未知")
            summary["document_types"][doc_type] = summary["document_types"].get(doc_type, 0) + 1
            
            # 症状统计
            symptoms = result.get("symptoms", {})
            if symptoms.get("has_symptoms", False):
                summary["symptom_statistics"]["files_with_symptoms"] += 1
                
                # 统计常见症状
                for symptom in symptoms.get("symptom_list", []):
                    summary["symptom_statistics"]["common_symptoms"][symptom] = \
                        summary["symptom_statistics"]["common_symptoms"].get(symptom, 0) + 1
            
            # 症状丰富度统计
            richness = result.get("content_richness", {}).get("symptom_richness", "")
            if richness in summary["symptom_statistics"]["symptom_richness_distribution"]:
                summary["symptom_statistics"]["symptom_richness_distribution"][richness] += 1
            
            # 诊断统计
            diagnoses = result.get("diagnoses", {})
            if diagnoses.get("has_diagnoses", False):
                summary["diagnosis_statistics"]["files_with_diagnoses"] += 1
                
                for diagnosis in diagnoses.get("diagnosis_list", []):
                    summary["diagnosis_statistics"]["common_diagnoses"][diagnosis] = \
                        summary["diagnosis_statistics"]["common_diagnoses"].get(diagnosis, 0) + 1
            
            # 治疗统计
            treatments = result.get("treatments", {})
            if treatments.get("has_treatments", False):
                summary["treatment_statistics"]["files_with_treatments"] += 1
                
                for treatment in treatments.get("treatment_list", []):
                    summary["treatment_statistics"]["common_treatments"][treatment] = \
                        summary["treatment_statistics"]["common_treatments"].get(treatment, 0) + 1
            
            # 内容质量统计
            quality = result.get("content_richness", {}).get("overall_quality", "")
            if quality == "高":
                summary["content_quality"]["high_quality"] += 1
            elif quality == "中":
                summary["content_quality"]["medium_quality"] += 1
            elif quality == "低":
                summary["content_quality"]["low_quality"] += 1
        
        return summary

def main():
    parser = argparse.ArgumentParser(description="医疗语料结构分析工具")
    parser.add_argument("--files", nargs="+", help="要分析的文件路径", required=True)
    parser.add_argument("--api", default="api_16", help="使用的API密钥名称")
    parser.add_argument("--output", help="输出文件路径（JSON格式）")
    parser.add_argument("--summary-only", action="store_true", help="只显示汇总结果")
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    valid_files = []
    for file_path in args.files:
        if os.path.exists(file_path):
            valid_files.append(file_path)
        else:
            print(f"警告: 文件不存在 {file_path}")
    
    if not valid_files:
        print("错误: 没有找到有效的文件")
        return
    
    print(f"开始分析 {len(valid_files)} 个文件...")
    print(f"使用API: {args.api}")
    
    # 初始化分析器
    analyzer = CorpusAnalyzer(args.api)
    
    # 分析文件
    results = analyzer.analyze_multiple_reports(valid_files)
    
    # 生成汇总
    summary = analyzer.summarize_analysis(results)
    
    # 输出结果
    output_data = {
        "analysis_results": results,
        "summary": summary
    }
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"结果已保存到: {args.output}")
    
    # 显示汇总信息
    print("\n" + "="*50)
    print("语料结构分析汇总")
    print("="*50)
    
    print(f"总文件数: {summary['total_files']}")
    print(f"成功分析: {summary['successful_analysis']}")
    print(f"分析失败: {summary['failed_analysis']}")
    
    print(f"\n文档类型分布:")
    for doc_type, count in summary['document_types'].items():
        print(f"  {doc_type}: {count}")
    
    print(f"\n症状信息统计:")
    print(f"  包含症状的文件: {summary['symptom_statistics']['files_with_symptoms']}")
    print(f"  症状丰富度分布:")
    for richness, count in summary['symptom_statistics']['symptom_richness_distribution'].items():
        print(f"    {richness}: {count}")
    
    print(f"\n诊断信息统计:")
    print(f"  包含诊断的文件: {summary['diagnosis_statistics']['files_with_diagnoses']}")
    
    print(f"\n治疗信息统计:")
    print(f"  包含治疗的文件: {summary['treatment_statistics']['files_with_treatments']}")
    
    print(f"\n内容质量分布:")
    for quality, count in summary['content_quality'].items():
        print(f"  {quality}: {count}")
    
    if not args.summary_only:
        print(f"\n详细结果已包含在输出中")

if __name__ == "__main__":
    main() 