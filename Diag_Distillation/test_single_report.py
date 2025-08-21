#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单报告测试脚本
用于测试修复后的诊断蒸馏系统
"""

import os
import sys
import json
import time
from datetime import datetime

# 添加项目根目录到Python路径
project_root = "/opt/RAG_Evidence4Organ"
sys.path.insert(0, project_root)

from Question_Distillation_v2.extractors.llm_extractor import LLMExtractor
from Diag_Distillation.prompts.medical_prompts import DiagnosticExtractionPrompts
from Diag_Distillation.process_worker import process_report_with_diagnostic_steps
from configs.system_config import MULTI_API_CONFIG

def test_single_report(report_num: int, api_key: str = "api_16"):
    """测试单个报告处理"""
    
    print(f"🏥 测试报告 {report_num}")
    print("=" * 60)
    
    try:
        # 初始化API
        if api_key not in MULTI_API_CONFIG:
            raise Exception(f"API密钥 {api_key} 不存在于配置中")
            
        api_config = MULTI_API_CONFIG[api_key]
        extractor = LLMExtractor(
            model=api_config["model"],
            api_key=api_config["api_key"],
            base_url=api_config["base_url"]
        )
        print(f"✅ API初始化成功: {api_key}")
        
        # 加载报告
        dataset_dir = "/opt/RAG_Evidence4Organ/dataset"
        txt_file = os.path.join(dataset_dir, f"report_{report_num}.txt")
        json_file = os.path.join(dataset_dir, f"report_{report_num}.json")
        
        if os.path.exists(txt_file):
            with open(txt_file, 'r', encoding='utf-8') as f:
                report_text = f.read()
            print(f"✅ 加载txt文件: {txt_file}")
        elif os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                report_text = data.get('text', '') or data.get('medical_record_content', '')
            print(f"✅ 加载json文件: {json_file}")
        else:
            raise FileNotFoundError(f"报告 {report_num} 不存在")
        
        print(f"📄 报告内容长度: {len(report_text)} 字符")
        
        # 准备报告数据
        report_data = {
            'text': report_text,
            'case_id': str(report_num),
            'filename': f'report_{report_num}.txt'
        }
        
        # 初始化提示词
        prompts = DiagnosticExtractionPrompts()
        
        # 处理报告
        start_time = time.time()
        print("\n🚀 开始处理...")
        
        result = process_report_with_diagnostic_steps(
            extractor, report_data, report_num, prompts, api_key
        )
        
        processing_time = time.time() - start_time
        
        if not result:
            raise Exception("处理失败：无返回结果")
        
        # 分析结果
        normalized = result.get("normalized", [])
        raw = result.get("raw", {})
        
        print(f"\n📊 处理结果:")
        print(f"   ⏱️ 处理时间: {processing_time:.1f}秒")
        
        if isinstance(normalized, list):
            print(f"   📋 标准化结果: {len(normalized)} 个条目")
            
            if normalized:
                total_units = sum(len(item.get('U_unit_set', [])) for item in normalized if isinstance(item, dict))
                unique_organs = set()
                for item in normalized:
                    if isinstance(item, dict):
                        for unit_wrapper in item.get('U_unit_set', []):
                            if isinstance(unit_wrapper, dict):
                                u_unit = unit_wrapper.get('u_unit', {})
                                if isinstance(u_unit, dict):
                                    organ_name = u_unit.get('o_organ', {}).get('organName')
                                    if organ_name:
                                        unique_organs.add(organ_name)
                
                print(f"   🧬 诊断单元总数: {total_units}")
                print(f"   🫀 涉及器官数: {len(unique_organs)}")
                if unique_organs:
                    print(f"   📝 涉及器官: {', '.join(sorted(unique_organs))}")
                    
                # 显示前3个症状示例
                print(f"\n🔍 症状示例 (前3个):")
                for i, item in enumerate(normalized[:3]):
                    if isinstance(item, dict):
                        symptom = item.get('s_symptom', 'Unknown')
                        unit_count = len(item.get('U_unit_set', []))
                        print(f"   {i+1}. '{symptom}' -> {unit_count} 个诊断单元")
            else:
                print("   ⚠️ 标准化结果为空")
        else:
            print(f"   ⚠️ 标准化结果类型异常: {type(normalized)}")
            print(f"   📄 内容: {normalized}")
        
        # 保存结果到测试目录
        test_dir = "/opt/RAG_Evidence4Organ/Diag_Distillation/test_single"
        os.makedirs(test_dir, exist_ok=True)
        
        raw_file = f"{test_dir}/report_{report_num}_raw.json"
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        
        normalized_file = f"{test_dir}/report_{report_num}_normalized.json"
        with open(normalized_file, 'w', encoding='utf-8') as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 结果已保存:")
        print(f"   Raw: {raw_file}")
        print(f"   Normalized: {normalized_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='单报告测试')
    parser.add_argument('--report', type=int, default=10061, help='报告编号')
    parser.add_argument('--api', type=str, default='api_16', help='API密钥')
    
    args = parser.parse_args()
    
    success = test_single_report(args.report, args.api)
    
    if success:
        print("\n✅ 测试成功完成！")
    else:
        print("\n❌ 测试失败！")

if __name__ == "__main__":
    main() 