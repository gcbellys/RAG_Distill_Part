import os
import requests
from typing import List, Dict, Any, Optional
from RAG_Evidence4Organ.configs.evaluation_llm_config import EVAL_LLM_CONFIG as llm_providers
import json

def load_llm_configs() -> List[Dict[str, Any]]:
    """
    从 evaluation_llm_config.py 加载所有LLM提供商的配置。
    此函数经过修改，以适配 EVAL_LLM_CONFIG 的结构。
    """
    configs = []
    for api_name, details in llm_providers.items():
        # 假设只要配置存在就是启用的，并直接使用其中包含的api_key
        if "api_key" in details and "model" in details:
            # 确定 provider 的名称，通常是 api_name 的第一部分
            provider = "unknown"
            if "anthropic" in api_name:
                provider = "anthropic"
            elif "google" in api_name or "gemini" in api_name:
                provider = "google"
            elif "openai" in api_name or "moonshot" in api_name or "qwen" in api_name:
                provider = "openai_compatible" # 泛指使用Bearer token的OpenAI格式
            
            configs.append({
                "api_name": api_name,
                "model_name": details["model"],
                "base_url": details.get("base_url", ""),
                "api_key": details["api_key"],
                "provider": provider
            })
        else:
            print(f"Warning: Skipping configuration for '{api_name}' due to missing 'api_key' or 'model'.")
            
    return configs

class LLMService:
    """一个通用的LLM服务类，可以处理来自不同提供商的API调用。"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_name = config["api_name"]
        self.model = config["model_name"]
        self.base_url = config["base_url"]
        self.api_key = config["api_key"]
        self.provider = config["provider"]

    def _prepare_request_data(self, prompt: str, user_query: str) -> Dict[str, Any]:
        """根据提供商准备请求体。"""
        # Claude需要将system prompt和user message分开
        if self.provider == "anthropic":
            return {
                "model": self.model,
                "system": prompt,
                "messages": [{"role": "user", "content": user_query}],
                "max_tokens": 4096,
                "temperature": 0.1,
            }
        
        # 默认使用OpenAI兼容的格式
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_query}
            ],
            "temperature": 0.1,
            "stream": False,
        }

    def _prepare_headers(self) -> Dict[str, str]:
        """根据提供商准备请求头。"""
        headers = {"Content-Type": "application/json"}
        if self.provider == "anthropic":
            headers["x-api-key"] = self.api_key
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _call_llm(self, request_data: Dict[str, Any], headers: Dict[str, str]) -> str:
        """执行对LLM API的调用。"""
        api_url = f"{self.base_url}/chat/completions"
        if self.provider == "anthropic":
            api_url = f"{self.base_url}/messages"
        elif self.provider == "google":
             # Gemini有特殊的URL结构, self.model 已经包含了 'models/' 前缀
             api_url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
             # Gemini的请求体也完全不同
             gemini_data = {
                 "contents": request_data["messages"][1:], # 发送所有user message
                 "system_instruction": {"parts": [{"text": request_data["messages"][0]["content"]}]} # system prompt
             }
             request_data = gemini_data


        try:
            response = requests.post(api_url, headers=headers, json=request_data, timeout=180)
            response.raise_for_status()
            result = response.json()

            # 解析不同提供商的响应
            if self.provider == "anthropic":
                return result.get("content", [{}])[0].get("text", "")
            elif self.provider == "google":
                return result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

            # 默认OpenAI兼容格式
            return result["choices"][0]["message"]["content"]
        except requests.RequestException as e:
            error_message = f"API call failed for {self.api_name}: {e}"
            if e.response is not None:
                error_message += f" | Response: {e.response.text}"
            print(error_message)
            return f'{{"error": "{error_message}"}}'
        except (KeyError, IndexError) as e:
            error_message = f"Failed to parse response for {self.api_name}: {e}. Response: {result}"
            print(error_message)
            return f'{{"error": "{error_message}"}}'

    async def get_response(self, system_prompt: str, user_query: str) -> Dict[str, Any]:
        """获取LLM的响应并格式化为标准字典。"""
        request_data = self._prepare_request_data(system_prompt, user_query)
        headers = self._prepare_headers()
        
        answer = self._call_llm(request_data, headers)
        
        return {
            "api_name": self.api_name,
            "model": self.model,
            "answer": answer,
            "prompt": system_prompt,
            "error": None if '"error":' not in answer else answer
        } 