#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试腾讯云API响应
"""

import os
import sys
import json
from loguru import logger

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge_distillation.extractors.llm_extractor import LLMExtractor
from configs.system_config import MULTI_API_CONFIG

def debug_tencent_api_response():
    """调试腾讯云API响应"""
    logger.info("🔍 调试腾讯云API响应")
    logger.info("=" * 60)
    
    # 测试api_2
    config = MULTI_API_CONFIG["api_2"]
    
    logger.info(f"📡 测试 {config['name']}")
    logger.info(f"   Base URL: {config['base_url']}")
    logger.info(f"   API Key: {config['api_key'][:20]}...")
    
    try:
        # 创建LLM提取器
        extractor = LLMExtractor(
            model="deepseek",
            api_key=config["api_key"],
            base_url=config["base_url"]
        )
        
        # 测试简单连接
        test_prompt = "Please respond with 'API connection test successful'"
        logger.info("   发送简单测试请求...")
        
        result = extractor.call_api(test_prompt)
        
        if result["success"]:
            logger.info(f"   ✅ 连接成功")
            logger.info(f"   Model: {result.get('model', 'N/A')}")
            logger.info(f"   Response: {result.get('response', 'N/A')}")
            
            # 测试医学信息提取
            logger.info("\n   测试医学信息提取...")
            medical_text = "Patient complains of chest pain and shortness of breath."
            
            # 获取提示词
            from knowledge_distillation.prompts.medical_prompts import get_prompt_by_specialty
            prompt = get_prompt_by_specialty("general")
            full_prompt = prompt + f"\n\nMedical Text:\n{medical_text}\n\nPlease extract relevant information:"
            
            logger.info(f"   提示词长度: {len(full_prompt)} 字符")
            logger.info(f"   提示词前200字符: {full_prompt[:200]}...")
            
            # 调用API
            extraction_result = extractor.call_api(full_prompt)
            
            if extraction_result["success"]:
                logger.info(f"   ✅ API调用成功")
                logger.info(f"   Model: {extraction_result.get('model', 'N/A')}")
                logger.info(f"   Response: {extraction_result.get('response', 'N/A')}")
                
                # 尝试解析
                extractions = extractor._parse_response(extraction_result["response"])
                logger.info(f"   解析结果: {len(extractions)} 条")
                for i, extraction in enumerate(extractions):
                    logger.info(f"     提取 {i+1}: {extraction}")
                    
            else:
                logger.error(f"   ❌ API调用失败: {extraction_result.get('error', '未知错误')}")
                
        else:
            logger.error(f"   ❌ 连接失败: {result.get('error', '未知错误')}")
            
    except Exception as e:
        logger.error(f"   ❌ 异常: {str(e)}")

def main():
    """主函数"""
    logger.info("🚀 腾讯云API响应调试")
    logger.info("=" * 60)
    
    try:
        debug_tencent_api_response()
        
    except KeyboardInterrupt:
        logger.info("\n⏹️ 用户中断测试")
    except Exception as e:
        logger.error(f"测试过程中出现异常: {e}")

if __name__ == "__main__":
    main() 