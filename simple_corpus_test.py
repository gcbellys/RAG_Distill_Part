#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的语料分析测试脚本
"""

import json
import sys
import os

sys.path.append('/opt/RAG_Evidence4Organ')

from Question_Distillation_v2.extractors.llm_extractor import LLMExtractor
from configs.system_config import MULTI_API_CONFIG

def test_api_call():
    """测试API调用是否正常"""
    
    # 使用api_16
    api_config = MULTI_API_CONFIG['api_16']
    extractor = LLMExtractor(
        model=api_config['model'],
        api_key=api_config['api_key'],
        base_url=api_config['base_url']
    )
    
    # 简单的测试提示词
    simple_prompt = """
请分析以下医疗文本，并以JSON格式返回：

{
  "document_type": "报告类型",
  "has_symptoms": true/false,
  "has_diagnosis": true/false,
  "brief_summary": "简要总结"
}

医疗文本：
58f w/rheumatoid arthritis on periodic prednisone, htn who presented to osh on w/sob, f/c, productive cough x 1 wk.

请返回JSON格式的分析结果。
"""
    
    try:
        print("开始测试API调用...")
        response = extractor.call_api(simple_prompt)
        print("API响应成功:")
        print(response)
        print("\n" + "="*50)
        
        # 尝试解析JSON
        try:
            result = json.loads(response)
            print("JSON解析成功:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            print("原始响应:")
            print(repr(response))
            
    except Exception as e:
        print(f"API调用失败: {e}")

def analyze_sample_text():
    """分析样本文本结构"""
    
    # 读取样本文件
    with open('dataset/report_6001.txt', 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    print("样本文本内容 (前500字符):")
    print(content[:500])
    print("\n" + "="*50)
    
    print(f"文本长度: {len(content)} 字符")
    print(f"文本行数: {len(content.splitlines())}")
    
    # 分析文本结构
    lines = content.split('\n')
    print(f"\n文本结构分析:")
    print(f"总行数: {len(lines)}")
    
    for i, line in enumerate(lines[:10]):  # 只显示前10行
        print(f"行 {i+1}: {line[:100]}...")
        
    # 检查是否包含常见医疗关键词
    keywords = {
        'symptoms': ['pain', 'cough', 'fever', 'nausea', 'shortness of breath', 'sob', 'fatigue'],
        'diagnoses': ['diagnosis', 'pneumonia', 'arthritis', 'hypertension', 'htn'],
        'treatments': ['treatment', 'medication', 'surgery', 'therapy'],
        'procedures': ['procedure', 'catheterization', 'intubation']
    }
    
    print(f"\n关键词分析:")
    for category, words in keywords.items():
        found_words = [word for word in words if word.lower() in content.lower()]
        print(f"{category}: {found_words}")

if __name__ == "__main__":
    print("🔍 语料结构诊断测试")
    print("="*50)
    
    print("\n1. 分析样本文本结构:")
    analyze_sample_text()
    
    print("\n2. 测试API调用:")
    test_api_call() 