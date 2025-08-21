#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置测试脚本
验证DeepSeek API配置是否正确
"""

import os
import sys
from loguru import logger

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_api_config():
    """测试API配置"""
    logger.info("测试API配置...")
    
    try:
        from configs.system_config import API_KEYS
        logger.info(f"API密钥配置: {list(API_KEYS.keys())}")
        
        if API_KEYS.get("deepseek"):
            logger.info("✓ DeepSeek API密钥已配置")
        else:
            logger.warning("✗ DeepSeek API密钥未配置")
            
    except ImportError as e:
        logger.error(f"导入配置失败: {e}")
        return False
    
    return True

def test_llm_extractor():
    """测试LLM提取器"""
    logger.info("测试LLM提取器...")
    
    try:
        from knowledge_distillation.extractors.llm_extractor import LLMExtractor
        
        # 创建提取器
        extractor = LLMExtractor(model="deepseek")
        
        if extractor.api_key:
            logger.info("✓ LLM提取器初始化成功")
            logger.info(f"API密钥: {extractor.api_key[:10]}...")
        else:
            logger.warning("✗ LLM提取器API密钥为空")
            
    except Exception as e:
        logger.error(f"LLM提取器测试失败: {e}")
        return False
    
    return True

def test_simple_extraction():
    """测试简单提取"""
    logger.info("测试简单提取...")
    
    try:
        from knowledge_distillation.extractors.llm_extractor import LLMExtractor
        
        # 创建提取器
        extractor = LLMExtractor(model="deepseek")
        
        # 测试文本
        test_text = "Patient complains of chest pain for 3 days, pain located behind the sternum, crushing in nature, accompanied by palpitations. ECG shows ST segment elevation."
        
        logger.info("正在测试API调用...")
        result = extractor.extract_medical_info(test_text, "test_case", "general")
        
        if result.get("success"):
            logger.info("✓ API调用成功")
            extractions = result.get("extractions", [])
            logger.info(f"提取到 {len(extractions)} 条信息")
        else:
            logger.warning(f"✗ API调用失败: {result.get('error', '未知错误')}")
            
    except Exception as e:
        logger.error(f"简单提取测试失败: {e}")
        return False
    
    return True

def main():
    """主函数"""
    logger.info("开始配置测试...")
    
    # 测试API配置
    if not test_api_config():
        logger.error("API配置测试失败")
        return
    
    # 测试LLM提取器
    if not test_llm_extractor():
        logger.error("LLM提取器测试失败")
        return
    
    # 测试简单提取（可选）
    logger.info("是否要测试API调用？这可能会消耗API配额 (y/n): ", end="")
    try:
        response = input().lower().strip()
        if response == 'y':
            test_simple_extraction()
    except KeyboardInterrupt:
        logger.info("跳过API调用测试")
    
    logger.info("配置测试完成！")

if __name__ == "__main__":
    main() 