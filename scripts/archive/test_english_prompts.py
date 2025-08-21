#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
英文提示词测试脚本
验证所有提示词是否已正确转换为英文
"""

import os
import sys
from loguru import logger

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_prompts():
    """测试所有提示词"""
    logger.info("测试英文提示词...")
    
    try:
        from knowledge_distillation.prompts.medical_prompts import (
            MedicalExtractionPrompts,
            get_prompt_by_specialty,
            create_extraction_pipeline
        )
        
        # 测试各专科提示词
        specialties = ["cardiac", "pulmonary", "liver", "thyroid", "general"]
        
        for specialty in specialties:
            prompt = get_prompt_by_specialty(specialty)
            logger.info(f"✓ {specialty.upper()} prompt: {len(prompt)} characters")
            
            # 检查是否包含中文
            chinese_chars = [char for char in prompt if '\u4e00' <= char <= '\u9fff']
            if chinese_chars:
                logger.warning(f"✗ {specialty} prompt contains Chinese characters: {chinese_chars[:10]}")
            else:
                logger.info(f"✓ {specialty} prompt is fully in English")
        
        # 测试完整流程
        pipeline = create_extraction_pipeline()
        logger.info(f"✓ Complete pipeline contains {len(pipeline)} prompts")
        
        for stage, prompt in pipeline.items():
            chinese_chars = [char for char in prompt if '\u4e00' <= char <= '\u9fff']
            if chinese_chars:
                logger.warning(f"✗ {stage} prompt contains Chinese characters")
            else:
                logger.info(f"✓ {stage} prompt is fully in English")
        
        return True
        
    except Exception as e:
        logger.error(f"测试提示词失败: {e}")
        return False

def test_extractor():
    """测试提取器"""
    logger.info("测试LLM提取器...")
    
    try:
        from knowledge_distillation.extractors.llm_extractor import LLMExtractor
        
        # 创建提取器
        extractor = LLMExtractor(model="deepseek")
        
        # 测试英文文本
        test_text = "Patient complains of chest pain for 3 days, pain located behind the sternum, crushing in nature, accompanied by palpitations. ECG shows ST segment elevation."
        
        logger.info("正在测试英文文本提取...")
        result = extractor.extract_medical_info(test_text, "test_case", "cardiac")
        
        if result.get("success"):
            logger.info("✓ English text extraction successful")
            extractions = result.get("extractions", [])
            logger.info(f"Extracted {len(extractions)} items")
            
            # 检查提取结果是否使用英文
            for extraction in extractions:
                organ = extraction.get("organ", "")
                if organ in ["heart", "lung", "liver", "thyroid"]:
                    logger.info(f"✓ Organ correctly extracted as: {organ}")
                else:
                    logger.warning(f"✗ Unexpected organ: {organ}")
        else:
            logger.warning(f"✗ English text extraction failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"提取器测试失败: {e}")
        return False
    
    return True

def test_prompt_content():
    """测试提示词内容"""
    logger.info("测试提示词内容...")
    
    try:
        from knowledge_distillation.prompts.medical_prompts import get_prompt_by_specialty
        
        # Test cardiac specialty prompt
        cardiac_prompt = get_prompt_by_specialty("cardiac")
        
        # 检查关键英文术语
        key_terms = [
            "cardiologist", "cardiovascular", "chest pain", "palpitations", 
            "dyspnea", "syncope", "left atrium", "right ventricle", 
            "coronary arteries", "valves", "ECG", "echocardiogram"
        ]
        
        missing_terms = []
        for term in key_terms:
            if term.lower() not in cardiac_prompt.lower():
                missing_terms.append(term)
        
        if missing_terms:
            logger.warning(f"✗ Missing key terms in cardiac prompt: {missing_terms}")
        else:
            logger.info("✓ All key cardiac terms found in prompt")
        
        # Test pulmonary specialty prompt
        pulmonary_prompt = get_prompt_by_specialty("pulmonary")
        
        pulmonary_terms = [
            "pulmonologist", "respiratory", "cough", "sputum", "dyspnea",
            "hemoptysis", "left lung", "right lung", "upper lobe", 
            "pneumonia", "pulmonary embolism", "pleural effusion"
        ]
        
        missing_pulmonary_terms = []
        for term in pulmonary_terms:
            if term.lower() not in pulmonary_prompt.lower():
                missing_pulmonary_terms.append(term)
        
        if missing_pulmonary_terms:
            logger.warning(f"✗ Missing key terms in pulmonary prompt: {missing_pulmonary_terms}")
        else:
            logger.info("✓ All key pulmonary terms found in prompt")
        
        return True
        
    except Exception as e:
        logger.error(f"提示词内容测试失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("开始英文提示词测试...")
    
    # 测试提示词
    if not test_prompts():
        logger.error("提示词测试失败")
        return
    
    # 测试提示词内容
    if not test_prompt_content():
        logger.error("提示词内容测试失败")
        return
    
    # 测试提取器（可选）
    logger.info("是否要测试提取器？这可能会消耗API配额 (y/n): ", end="")
    try:
        response = input().lower().strip()
        if response == 'y':
            test_extractor()
    except KeyboardInterrupt:
        logger.info("跳过提取器测试")
    
    logger.info("英文提示词测试完成！")

if __name__ == "__main__":
    main() 