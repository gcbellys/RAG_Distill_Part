#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络连接测试脚本
用于诊断API连接问题
"""

import requests
import time
from loguru import logger

def test_deepseek_connectivity():
    """测试DeepSeek API连接"""
    logger.info("测试DeepSeek API连接...")
    
    # 测试基本连接
    try:
        response = requests.get("https://api.deepseek.com", timeout=10)
        logger.info(f"✅ DeepSeek API基础连接成功: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ DeepSeek API基础连接失败: {e}")
        return False
    
    # 测试DNS解析
    try:
        import socket
        ip = socket.gethostbyname("api.deepseek.com")
        logger.info(f"✅ DNS解析成功: api.deepseek.com -> {ip}")
    except Exception as e:
        logger.error(f"❌ DNS解析失败: {e}")
        return False
    
    return True

def test_api_response_time():
    """测试API响应时间"""
    logger.info("测试API响应时间...")
    
    start_time = time.time()
    try:
        response = requests.get("https://api.deepseek.com", timeout=30)
        end_time = time.time()
        response_time = end_time - start_time
        logger.info(f"✅ API响应时间: {response_time:.2f}秒")
        return response_time
    except Exception as e:
        logger.error(f"❌ API响应时间测试失败: {e}")
        return None

def test_proxy_settings():
    """测试代理设置"""
    logger.info("检查代理设置...")
    
    # 检查环境变量
    import os
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
    
    for var in proxy_vars:
        value = os.getenv(var)
        if value:
            logger.info(f"发现代理设置: {var} = {value}")
        else:
            logger.info(f"未设置代理: {var}")
    
    # 检查requests的代理设置
    try:
        session = requests.Session()
        if session.proxies:
            logger.info(f"Requests代理设置: {session.proxies}")
        else:
            logger.info("Requests未设置代理")
    except Exception as e:
        logger.error(f"检查Requests代理设置失败: {e}")

def test_network_quality():
    """测试网络质量"""
    logger.info("测试网络质量...")
    
    # 多次测试响应时间
    response_times = []
    for i in range(5):
        response_time = test_api_response_time()
        if response_time:
            response_times.append(response_time)
        time.sleep(1)
    
    if response_times:
        avg_time = sum(response_times) / len(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        
        logger.info(f"网络质量统计:")
        logger.info(f"  平均响应时间: {avg_time:.2f}秒")
        logger.info(f"  最快响应时间: {min_time:.2f}秒")
        logger.info(f"  最慢响应时间: {max_time:.2f}秒")
        
        if avg_time > 10:
            logger.warning("⚠️ 网络响应时间较长，建议检查网络连接")
        elif avg_time > 5:
            logger.info("⚠️ 网络响应时间中等")
        else:
            logger.info("✅ 网络响应时间良好")

def main():
    """主函数"""
    logger.info("🌐 网络连接诊断")
    logger.info("=" * 50)
    
    # 测试基本连接
    if not test_deepseek_connectivity():
        logger.error("基础连接测试失败，请检查网络设置")
        return
    
    # 检查代理设置
    test_proxy_settings()
    
    # 测试网络质量
    test_network_quality()
    
    logger.info("=" * 50)
    logger.info("网络诊断完成！")

if __name__ == "__main__":
    main() 