#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试Diag_Distillation系统的脚本
"""

import sys
import json
import traceback
sys.path.append('/opt/RAG_Evidence4Organ')

from configs.system_config import MULTI_API_CONFIG
from Question_Distillation_v2.extractors.llm_extractor import LLMExtractor
from Diag_Distillation.prompts.medical_prompts import DiagnosticExtractionPrompts

def test_api_response():
    # 读取测试文件
    with open('dataset/report_10001.txt', 'r', encoding='utf-8') as f:
        test_text = f.read()
    
    # 截取前1000字符作为测试
    test_chunk = test_text[:1000]
    print(f"测试文本长度: {len(test_chunk)} 字符")
    print(f"测试文本前200字符: {test_chunk[:200]}")
    print("-" * 60)
    
    # 初始化API
    api_config = MULTI_API_CONFIG['api_13']
    extractor = LLMExtractor(
        model=api_config['model'],
        api_key=api_config['api_key'],
        base_url=api_config['base_url']
    )
    
    # 初始化提示词
    prompts = DiagnosticExtractionPrompts()
    
    # 测试步骤1：患者症状提取
    print("🔍 测试步骤1：患者症状提取")
    try:
        # 先获取提示词模板
        prompt_template = prompts.get_step1_complaint_extraction_prompt(test_chunk)
        print(f"提示词模板长度: {len(prompt_template)} 字符")
        print(f"提示词模板末尾200字符: ...{prompt_template[-200:]}")
        
        # 然后格式化
        prompt1 = prompt_template.format(text_content=test_chunk)
        print(f"格式化后提示词长度: {len(prompt1)} 字符")
        
        response1 = extractor.call_api(prompt1)
        print(f"API响应类型: {type(response1)}")
        print(f"API响应: {response1}")
        
        if isinstance(response1, dict) and 'response' in response1:
            raw_text = response1['response']
            print(f"原始响应文本长度: {len(raw_text)}")
            print(f"原始响应前500字符: {raw_text[:500]}")
            
            # 尝试解析JSON
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', raw_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                print(f"提取的JSON长度: {len(json_str)}")
                print(f"提取的JSON前300字符: {json_str[:300]}")
                try:
                    parsed = json.loads(json_str)
                    print(f"解析成功: {type(parsed)}")
                except json.JSONDecodeError as e:
                    print(f"JSON解析失败: {e}")
            else:
                print("未找到JSON格式，尝试直接解析")
                try:
                    parsed = json.loads(raw_text)
                    print(f"直接解析成功: {type(parsed)}")
                except json.JSONDecodeError as e:
                    print(f"直接解析失败: {e}")
        
    except Exception as e:
        print(f"步骤1测试失败: {e}")
        traceback.print_exc()
    
    print("=" * 60)
    
    # 测试整合提示词
    print("🔍 测试整合提示词")
    try:
        prompt_template = prompts.get_integrated_diagnostic_prompt(test_chunk)
        print(f"整合提示词模板长度: {len(prompt_template)} 字符")
        
        prompt_integrated = prompt_template.format(text_content=test_chunk)
        print(f"整合提示词格式化后长度: {len(prompt_integrated)} 字符")
        
        response_integrated = extractor.call_api(prompt_integrated)
        print(f"整合API响应类型: {type(response_integrated)}")
        print(f"整合API响应: {response_integrated}")
        
    except Exception as e:
        print(f"整合提示词测试失败: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_api_response() 