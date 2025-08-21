#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
所有API连接测试脚本
测试5个API的连接性和响应情况
"""

import os
import sys
import time
from typing import Dict, Any
from loguru import logger

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge_distillation.extractors.llm_extractor import LLMExtractor
from knowledge_distillation.extractors.tencent_extractor import TencentExtractor
from configs.system_config import MULTI_API_CONFIG

def test_deepseek_api(api_config: Dict[str, Any]) -> Dict[str, Any]:
    """测试DeepSeek API"""
    logger.info(f"测试 {api_config['name']}...")
    
    try:
        # 创建提取器
        extractor = LLMExtractor(
            model="deepseek",
            api_key=api_config["api_key"]
        )
        
        # 测试简单查询
        test_text = "Patient complains of chest pain and shortness of breath."
        start_time = time.time()
        
        result = extractor.extract_medical_info(
            text=test_text,
            case_id="test_case",
            specialty="general"
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        if result.get("success", False):
            extractions = result.get("extractions", [])
            return {
                "status": "✅ 成功",
                "response_time": f"{response_time:.2f}秒",
                "extractions_count": len(extractions),
                "model": result.get("model", "unknown"),
                "error": None
            }
        else:
            return {
                "status": "❌ 失败",
                "response_time": f"{response_time:.2f}秒",
                "extractions_count": 0,
                "model": "unknown",
                "error": result.get("error", "未知错误")
            }
            
    except Exception as e:
        return {
            "status": "❌ 异常",
            "response_time": "N/A",
            "extractions_count": 0,
            "model": "unknown",
            "error": str(e)
        }

def test_tencent_api(api_config: Dict[str, Any]) -> Dict[str, Any]:
    """测试腾讯云API (OpenAI兼容格式)"""
    logger.info(f"测试 {api_config['name']}...")
    
    try:
        # 创建提取器 (使用OpenAI兼容格式)
        extractor = LLMExtractor(
            model="deepseek",
            api_key=api_config["api_key"],
            base_url=api_config["base_url"]
        )
        
        # 测试简单查询
        test_text = "Patient complains of chest pain and shortness of breath."
        start_time = time.time()
        
        result = extractor.extract_medical_info(
            text=test_text,
            case_id="test_case",
            specialty="general"
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        if result.get("success", False):
            extractions = result.get("extractions", [])
            return {
                "status": "✅ 成功",
                "response_time": f"{response_time:.2f}秒",
                "extractions_count": len(extractions),
                "model": result.get("model", "unknown"),
                "error": None
            }
        else:
            return {
                "status": "❌ 失败",
                "response_time": f"{response_time:.2f}秒",
                "extractions_count": 0,
                "model": "unknown",
                "error": result.get("error", "未知错误")
            }
            
    except Exception as e:
        return {
            "status": "❌ 异常",
            "response_time": "N/A",
            "extractions_count": 0,
            "model": "unknown",
            "error": str(e)
        }

def test_api_connectivity():
    """测试所有API连接性"""
    logger.info("🔍 开始测试所有API连接性...")
    logger.info("=" * 60)
    
    results = {}
    
    for api_key, api_config in MULTI_API_CONFIG.items():
        logger.info(f"\n📡 测试 {api_key}: {api_config['name']}")
        logger.info(f"   处理范围: {api_config['range']}")
        logger.info(f"   模型: {api_config['model']}")
        
        if api_config.get("is_tencent", False):
            result = test_tencent_api(api_config)
        else:
            result = test_deepseek_api(api_config)
        
        results[api_key] = result
        
        logger.info(f"   状态: {result['status']}")
        logger.info(f"   响应时间: {result['response_time']}")
        logger.info(f"   提取数量: {result['extractions_count']}")
        if result['error']:
            logger.error(f"   错误: {result['error']}")
    
    # 输出汇总报告
    logger.info("\n" + "=" * 60)
    logger.info("📊 API连接测试汇总报告")
    logger.info("=" * 60)
    
    success_count = 0
    total_count = len(results)
    
    for api_key, result in results.items():
        api_config = MULTI_API_CONFIG[api_key]
        status_icon = "✅" if result['status'] == "✅ 成功" else "❌"
        
        logger.info(f"{status_icon} {api_key}: {api_config['name']}")
        logger.info(f"   状态: {result['status']}")
        logger.info(f"   响应时间: {result['response_time']}")
        logger.info(f"   提取数量: {result['extractions_count']}")
        
        if result['status'] == "✅ 成功":
            success_count += 1
        
        if result['error']:
            logger.error(f"   错误: {result['error']}")
        
        logger.info("")
    
    # 统计信息
    success_rate = (success_count / total_count) * 100
    logger.info(f"📈 成功率: {success_count}/{total_count} ({success_rate:.1f}%)")
    
    if success_count == total_count:
        logger.info("🎉 所有API连接正常，可以开始并行处理！")
    else:
        logger.warning("⚠️ 部分API连接失败，请检查配置和网络连接")
    
    return results

def main():
    """主函数"""
    logger.info("🚀 API连接性测试工具")
    logger.info("=" * 60)
    
    try:
        results = test_api_connectivity()
        
        # 保存测试结果
        import json
        test_results_file = "api_test_results.json"
        with open(test_results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n📄 测试结果已保存到: {test_results_file}")
        
    except KeyboardInterrupt:
        logger.info("\n⏹️ 用户中断测试")
    except Exception as e:
        logger.error(f"测试过程中出现异常: {e}")

if __name__ == "__main__":
    main() 