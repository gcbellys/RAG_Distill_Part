#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM提取器
用于调用大语言模型进行医学信息提取
"""

import json
import time
import requests
import os
from typing import Dict, Any, List, Optional
from loguru import logger



# 导入提示词系统
import sys
project_root = "/opt/RAG_Evidence4Organ"
sys.path.insert(0, project_root)
from Question_Distillation_v2.prompts.medical_prompts import MedicalExtractionPrompts, get_prompt_by_specialty

class LLMExtractor:
    """LLM提取器类"""
    
    def __init__(self, model: str, api_key: str, base_url: str, config: Dict[str, Any] = None):
        """
        初始化LLM提取器
        
        Args:
            model: 要使用的模型名称 (e.g., "deepseek-chat")
            api_key: API密钥
            base_url: API的基础URL
            config: 其他配置参数
        """
        self.model_name = model # 直接使用传入的model名
        self.api_key = api_key
        self.base_url = base_url
        self.config = config or self._get_default_config()
        
        if not self.api_key:
            logger.warning(f"未提供 API 密钥")
        if not self.base_url:
            logger.warning(f"未提供 base_url")

    def _load_api_key(self) -> str:
        # This method is no longer primary, but can be kept as a fallback.
        # For simplicity in this fix, we assume direct passing of keys.
        return ""
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "max_tokens": 4000,  # 增加到4000以处理长医学报告
            "temperature": 0.1,
            "top_p": 0.9,
            "timeout": 60,
            "retry_times": 3,
            "delay": 2.0,
            "retry_delay": 5.0
        }
    
    def call_deepseek_api(self, prompt: str) -> Dict[str, Any]:
        """调用DeepSeek API"""
        retry_times = self.config.get("retry_times", 3)
        retry_delay = self.config.get("retry_delay", 5.0)
        
        for attempt in range(retry_times):
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": self.model_name, # 直接使用初始化时传入的模型名称
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": self.config["max_tokens"],
                    "temperature": self.config["temperature"],
                    "top_p": self.config["top_p"],
                    "stream": False
                }
                
                api_url = f"{self.base_url}/chat/completions"
                
                response = requests.post(
                    api_url,
                    headers=headers,
                    json=data,
                    timeout=self.config["timeout"]
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "response": result["choices"][0]["message"]["content"],
                        "usage": result.get("usage", {}),
                        "model": self.model_name # 返回正确的模型名
                    }
                else:
                    error_msg = f"DeepSeek API调用失败: {response.status_code} - {response.text}"
                    if attempt < retry_times - 1:
                        logger.warning(f"第{attempt + 1}次尝试失败: {error_msg}, {retry_delay}秒后重试...")
                        import time
                        time.sleep(retry_delay)
                        continue
                    else:
                        return {
                            "success": False,
                            "error": error_msg,
                            "response": None
                        }
                        
            except Exception as e:
                error_msg = str(e)
                if attempt < retry_times - 1:
                    logger.warning(f"第{attempt + 1}次尝试异常: {error_msg}, {retry_delay}秒后重试...")
                    import time
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"DeepSeek API调用异常: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg,
                        "response": None
                    }
        
        return {
            "success": False,
            "error": "所有重试都失败了",
            "response": None
        }
    
    def _call_with_openai_sdk(self, prompt: str) -> Dict[str, Any]:
        """使用OpenAI SDK调用API"""
        try:
            # 创建OpenAI客户端
            client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            
            # 调用API
            completion = client.chat.completions.create(
                model="deepseek-r1",  # 腾讯云使用deepseek-r1模型
                messages=[
                    {'role': 'user', 'content': prompt}
                ],
                max_tokens=self.config["max_tokens"],
                temperature=self.config["temperature"],
                top_p=self.config["top_p"]
            )
            
            # 获取响应内容
            response_content = completion.choices[0].message.content
            
            # 获取使用情况
            usage = {
                "prompt_tokens": completion.usage.prompt_tokens if completion.usage else 0,
                "completion_tokens": completion.usage.completion_tokens if completion.usage else 0,
                "total_tokens": completion.usage.total_tokens if completion.usage else 0
            }
            
            return {
                "success": True,
                "response": response_content,
                "usage": usage,
                "model": "deepseek-r1"
            }
            
        except Exception as e:
            logger.error(f"OpenAI SDK调用异常: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "response": None
            }
    
    def call_openai_api(self, prompt: str) -> Dict[str, Any]:
        """调用OpenAI API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": self.config["max_tokens"],
                "temperature": self.config["temperature"],
                "top_p": self.config["top_p"]
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=self.config["timeout"]
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "response": result["choices"][0]["message"]["content"],
                    "usage": result.get("usage", {}),
                    "model": "gpt-3.5-turbo"
                }
            else:
                return {
                    "success": False,
                    "error": f"OpenAI API调用失败: {response.status_code} - {response.text}",
                    "response": None
                }
                
        except Exception as e:
            logger.error(f"OpenAI API调用异常: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "response": None
            }
    
    def call_api(self, prompt: str) -> Dict[str, Any]:
        """主API调用方法"""
        # 简化: 当前只支持 openai 兼容的接口
        return self.call_deepseek_api(prompt)
    
    def extract_medical_info(self, text: str, case_id: str = "", specialty: str = "general") -> Dict[str, Any]:
        """
        提取医学信息
        
        Args:
            text: 医学文本
            case_id: 病例ID
            specialty: 专科类型
            
        Returns:
            提取结果
        """
        try:
            # 获取对应的提示词
            prompt = get_prompt_by_specialty(specialty)
            full_prompt = prompt + f"\n\nMedical Text:\n{text}\n\nPlease extract relevant information:"
            
            # 调用API
            result = self.call_api(full_prompt)
            
            if not result["success"]:
                return {
                    "case_id": case_id,
                    "success": False,
                    "error": result["error"],
                    "extractions": [],
                    "specialty": specialty
                }
            
            # 解析响应
            extractions = self._parse_response(result["response"])
            
            return {
                "case_id": case_id,
                "success": True,
                "extractions": extractions,
                "specialty": specialty,
                "usage": result.get("usage", {}),
                "model": result.get("model", self.model_name)
            }
            
        except Exception as e:
            logger.error(f"提取医学信息异常: {str(e)}")
            return {
                "case_id": case_id,
                "success": False,
                "error": str(e),
                "extractions": [],
                "specialty": specialty
            }
    
    def _parse_response(self, response_text: str) -> List[Dict[str, Any]]:
        """解析API响应"""
        try:
            # 清理响应文本，移除多余的空行和注释
            cleaned_text = response_text.strip()
            
            # 尝试直接解析JSON
            if cleaned_text.startswith("["):
                # 找到第一个完整的JSON数组
                import re
                json_pattern = r'^\[.*?\]'
                match = re.search(json_pattern, cleaned_text, re.DOTALL)
                if match:
                    json_str = match.group()
                    return json.loads(json_str)
                else:
                    return json.loads(cleaned_text)
            elif cleaned_text.startswith("{"):
                # 找到第一个完整的JSON对象
                import re
                json_pattern = r'^\{.*?\}'
                match = re.search(json_pattern, cleaned_text, re.DOTALL)
                if match:
                    json_str = match.group()
                    return [json.loads(json_str)]
                else:
                    return [json.loads(cleaned_text)]
            
            # 尝试提取JSON部分
            import re
            json_pattern = r'\[.*?\]'
            match = re.search(json_pattern, cleaned_text, re.DOTALL)
            
            if match:
                json_str = match.group()
                return json.loads(json_str)
            
            # 如果都失败，尝试解析非标准格式
            return self._parse_non_json_response(cleaned_text)
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {str(e)}")
            return self._parse_non_json_response(cleaned_text)
        except Exception as e:
            logger.error(f"响应解析异常: {str(e)}")
            return []
    
    def _parse_non_json_response(self, response_text: str) -> List[Dict[str, Any]]:
        """解析非JSON格式的响应"""
        extractions = []
        
        try:
            # 简单的文本解析逻辑
            lines = response_text.split('\n')
            current_extraction = {}
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 尝试提取字段
                if "disease_symptom" in line.lower() or "症状" in line or "疾病" in line:
                    current_extraction["disease_symptom"] = line.split(":")[-1].strip()
                elif "organ" in line.lower() or "器官" in line:
                    current_extraction["organ"] = line.split(":")[-1].strip()
                elif "specific_part" in line.lower() or "部位" in line:
                    current_extraction["specific_part"] = line.split(":")[-1].strip()
                elif "confidence" in line.lower() or "置信度" in line:
                    current_extraction["confidence"] = line.split(":")[-1].strip()
                elif "evidence" in line.lower() or "证据" in line:
                    current_extraction["evidence"] = line.split(":")[-1].strip()
                
                # 如果收集到足够信息，添加到结果中
                if len(current_extraction) >= 3:
                    extractions.append(current_extraction.copy())
                    current_extraction = {}
            
            # 添加最后一个提取结果
            if current_extraction:
                extractions.append(current_extraction)
                
        except Exception as e:
            logger.error(f"非JSON响应解析异常: {str(e)}")
        
        return extractions
    
    def batch_extract(self, texts: List[Dict[str, str]], delay: float = None) -> List[Dict[str, Any]]:
        """
        批量提取医学信息
        
        Args:
            texts: 文本列表，每个元素包含text和case_id
            delay: 请求间隔
            
        Returns:
            批量提取结果
        """
        if delay is None:
            delay = self.config["delay"]
        
        results = []
        
        for i, item in enumerate(texts):
            logger.info(f"处理第 {i+1}/{len(texts)} 个病例")
            
            # 提取信息
            result = self.extract_medical_info(
                text=item["text"],
                case_id=item.get("case_id", f"case_{i}"),
                specialty=item.get("specialty", "general")
            )
            
            results.append(result)
            
            # 添加延迟
            if i < len(texts) - 1:
                time.sleep(delay)
        
        return results
    
    def validate_extraction(self, extraction: Dict[str, Any]) -> Dict[str, Any]:
        """验证提取结果"""
        # 基本验证
        required_fields = ["disease_symptom", "organ", "specific_part"]
        missing_fields = [field for field in required_fields if not extraction.get(field)]
        
        if missing_fields:
            return {
                "valid": False,
                "errors": f"缺少必要字段: {missing_fields}",
                "extraction": extraction
            }
        
        # 器官验证
        from configs.model_config import is_allowed_organ
        if not is_allowed_organ(extraction["organ"]):
            return {
                "valid": False,
                "errors": f"不支持的器官: {extraction['organ']}",
                "extraction": extraction
            }
        
        return {
            "valid": True,
            "extraction": extraction
        }

def create_extractor(model: str, api_key: str, base_url: str) -> LLMExtractor:
    """
    工厂函数，用于创建LLMExtractor实例
    """
    return LLMExtractor(model=model, api_key=api_key, base_url=base_url)

if __name__ == "__main__":
    # 测试LLM提取器
    print("LLM提取器测试")
    print("=" * 40)
    
    # 创建提取器
    extractor = create_extractor()
    
    # 测试文本
    test_text = """
    患者主诉胸痛3天，疼痛位于胸骨后，呈压榨性，伴有心悸。
    心电图显示ST段抬高，肌钙蛋白升高。
    考虑急性心肌梗死，建议行冠状动脉造影检查。
    """
    
    # 提取信息
    result = extractor.extract_medical_info(
        text=test_text,
        case_id="test_case_001",
        specialty="cardiac"
    )
    
    print(f"提取结果: {json.dumps(result, ensure_ascii=False, indent=2)}") 