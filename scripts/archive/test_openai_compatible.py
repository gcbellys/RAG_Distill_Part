#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试腾讯云OpenAI兼容格式API
"""

import os
import sys
import json
from loguru import logger

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge_distillation.extractors.llm_extractor import LLMExtractor
from configs.system_config import MULTI_API_CONFIG

def test_openai_compatible_api():
    """测试OpenAI兼容格式的API"""
    logger.info("🔍 测试腾讯云OpenAI兼容格式API")
    logger.info("=" * 60)
    
    # 测试api_2和api_3 (腾讯云API)
    for api_key in ["api_2", "api_3"]:
        config = MULTI_API_CONFIG[api_key]
        
        logger.info(f"\n📡 测试 {api_key}: {config['name']}")
        logger.info(f"   Base URL: {config['base_url']}")
        logger.info(f"   API Key: {config['api_key'][:20]}...")
        logger.info(f"   Model: {config['model']}")
        logger.info(f"   Range: {config['range']}")
        
        try:
            # 创建LLM提取器
            extractor = LLMExtractor(
                model="deepseek",
                api_key=config["api_key"],
                base_url=config["base_url"]
            )
            
            # 测试简单连接
            test_prompt = "Please respond with 'API connection test successful'"
            logger.info("   发送测试请求...")
            
            result = extractor.call_api(test_prompt)
            
            if result["success"]:
                logger.info(f"   ✅ 连接成功")
                logger.info(f"   Model: {result.get('model', 'N/A')}")
                logger.info(f"   Response: {result.get('response', 'N/A')[:100]}...")
                
                # 测试医学信息提取
                logger.info("   测试医学信息提取...")
                medical_text = "Patient complains of chest pain and shortness of breath."
                
                extraction_result = extractor.extract_medical_info(
                    text=medical_text,
                    case_id="test_case",
                    specialty="general"
                )
                
                if extraction_result.get("success", False):
                    extractions = extraction_result.get("extractions", [])
                    logger.info(f"   ✅ 医学提取成功，获得 {len(extractions)} 条信息")
                    for i, extraction in enumerate(extractions[:2]):  # 只显示前2条
                        logger.info(f"     提取 {i+1}: {extraction.get('disease_symptom', 'N/A')} - {extraction.get('organ', 'N/A')}")
                else:
                    logger.warning(f"   ⚠️ 医学提取失败: {extraction_result.get('error', '未知错误')}")
                    
            else:
                logger.error(f"   ❌ 连接失败: {result.get('error', '未知错误')}")
                
        except Exception as e:
            logger.error(f"   ❌ 异常: {str(e)}")
        
        logger.info("")

def main():
    """主函数"""
    logger.info("🚀 腾讯云OpenAI兼容格式API测试")
    logger.info("=" * 60)
    
    try:
        test_openai_compatible_api()
        
        logger.info("\n" + "=" * 60)
        logger.info("📋 配置信息")
        logger.info("=" * 60)
        
        # 显示当前配置
        for api_key in ["api_2", "api_3"]:
            config = MULTI_API_CONFIG[api_key]
            logger.info(f"\n{api_key}:")
            logger.info(f"  名称: {config['name']}")
            logger.info(f"  Base URL: {config['base_url']}")
            logger.info(f"  API Key: {config['api_key'][:20]}...")
            logger.info(f"  模型: {config['model']}")
            logger.info(f"  处理范围: {config['range']}")
            logger.info(f"  是否腾讯格式: {config.get('is_tencent', False)}")
        
    except KeyboardInterrupt:
        logger.info("\n⏹️ 用户中断测试")
    except Exception as e:
        logger.error(f"测试过程中出现异常: {e}")

if __name__ == "__main__":
    main() 