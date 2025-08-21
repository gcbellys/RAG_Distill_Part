#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
腾讯云DeepSeek API提取器
"""

import json
import requests
from typing import Dict, Any, List
from loguru import logger

from tencentcloud.common.common_client import CommonClient
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile

class NonStreamResponse(object):
    def __init__(self):
        self.response = ""

    def _deserialize(self, obj):
        self.response = json.dumps(obj)

class TencentExtractor:
    """腾讯云DeepSeek API提取器"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.lkeap.cloud.tencent.com/v1"):
        """
        初始化腾讯云提取器
        
        Args:
            api_key: 腾讯云API密钥
            base_url: API基础URL
        """
        self.api_key = api_key
        self.base_url = base_url
        self.config = self._get_default_config()
        
        # 初始化腾讯云客户端
        self._init_tencent_client()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "max_tokens": 2000,
            "temperature": 0.1,
            "top_p": 0.9,
            "timeout": 60,
            "retry_times": 3,
            "delay": 2.0,
            "retry_delay": 5.0
        }
    
    def _init_tencent_client(self):
        """初始化腾讯云客户端"""
        try:
            # 解析API密钥 (假设格式为 "secret_id:secret_key")
            if ":" in self.api_key:
                secret_id, secret_key = self.api_key.split(":", 1)
            else:
                # 如果只有一个密钥，假设是secret_key
                secret_id = ""
                secret_key = self.api_key
            
            self.cred = credential.Credential(secret_id, secret_key)
            
            httpProfile = HttpProfile()
            httpProfile.endpoint = "lkeap.tencentcloudapi.com"
            httpProfile.reqTimeout = self.config["timeout"] * 1000  # 转换为毫秒
            
            self.clientProfile = ClientProfile()
            self.clientProfile.httpProfile = httpProfile
            
            self.common_client = CommonClient(
                "lkeap", 
                "2024-05-22", 
                self.cred, 
                "ap-guangzhou", 
                profile=self.clientProfile
            )
            
            logger.info("腾讯云客户端初始化成功")
            
        except Exception as e:
            logger.error(f"腾讯云客户端初始化失败: {e}")
            raise
    
    def call_tencent_api(self, prompt: str) -> Dict[str, Any]:
        """调用腾讯云API"""
        retry_times = self.config.get("retry_times", 3)
        retry_delay = self.config.get("retry_delay", 5.0)
        
        for attempt in range(retry_times):
            try:
                params = {
                    "Model": "deepseek-r1",
                    "Messages": [{"Role": "user", "Content": prompt}],
                    "Stream": False,
                    "MaxTokens": self.config["max_tokens"],
                    "Temperature": self.config["temperature"],
                    "TopP": self.config["top_p"]
                }
                
                resp = self.common_client._call_and_deserialize(
                    "ChatCompletions", 
                    params, 
                    NonStreamResponse
                )
                
                if isinstance(resp, NonStreamResponse):
                    result = json.loads(resp.response)
                    return {
                        "success": True,
                        "response": result.get("choices", [{}])[0].get("message", {}).get("content", ""),
                        "usage": result.get("usage", {}),
                        "model": "deepseek-r1"
                    }
                else:
                    error_msg = "腾讯云API返回格式异常"
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
                        
            except TencentCloudSDKException as e:
                error_msg = str(e)
                if attempt < retry_times - 1:
                    logger.warning(f"第{attempt + 1}次尝试异常: {error_msg}, {retry_delay}秒后重试...")
                    import time
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"腾讯云API调用异常: {error_msg}")
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
                    logger.error(f"腾讯云API调用异常: {error_msg}")
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
            from knowledge_distillation.prompts.medical_prompts import get_prompt_by_specialty
            prompt = get_prompt_by_specialty(specialty)
            full_prompt = prompt + f"\n\nMedical Text:\n{text}\n\nPlease extract relevant information:"
            
            # 调用API
            result = self.call_tencent_api(full_prompt)
            
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
                "model": result.get("model", "deepseek-r1")
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
            # 尝试直接解析JSON
            if response_text.strip().startswith("["):
                return json.loads(response_text)
            elif response_text.strip().startswith("{"):
                return [json.loads(response_text)]
            
            # 尝试提取JSON部分
            import re
            json_pattern = r'\[.*\]'
            match = re.search(json_pattern, response_text, re.DOTALL)
            
            if match:
                json_str = match.group()
                return json.loads(json_str)
            
            # 如果都失败，返回空列表
            logger.warning(f"无法解析响应: {response_text[:100]}...")
            return []
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"响应解析异常: {str(e)}")
            return []

def create_tencent_extractor(api_key: str, base_url: str = None) -> TencentExtractor:
    """创建腾讯云提取器实例"""
    return TencentExtractor(api_key=api_key, base_url=base_url) 