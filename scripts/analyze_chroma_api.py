#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
彻底分析ChromaDB 0.5.23 API结构
"""

import sys
import os

def analyze_chroma_api():
    """彻底分析ChromaDB API"""
    try:
        import chromadb
        print(f"ChromaDB版本: {chromadb.__version__}")
        
        print("\n=== 1. 检查PersistentClient ===")
        print(f"PersistentClient类型: {type(chromadb.PersistentClient)}")
        print(f"PersistentClient是否可调用: {callable(chromadb.PersistentClient)}")
        
        # 检查PersistentClient的签名
        import inspect
        try:
            sig = inspect.signature(chromadb.PersistentClient)
            print(f"PersistentClient签名: {sig}")
        except Exception as e:
            print(f"无法获取签名: {e}")
        
        print("\n=== 2. 检查Client ===")
        print(f"Client类型: {type(chromadb.Client)}")
        print(f"Client是否可调用: {callable(chromadb.Client)}")
        
        try:
            sig = inspect.signature(chromadb.Client)
            print(f"Client签名: {sig}")
        except Exception as e:
            print(f"无法获取Client签名: {e}")
        
        print("\n=== 3. 检查Settings ===")
        if hasattr(chromadb, 'Settings'):
            print("✅ Settings存在")
            print(f"Settings类型: {type(chromadb.Settings)}")
            try:
                sig = inspect.signature(chromadb.Settings)
                print(f"Settings签名: {sig}")
            except Exception as e:
                print(f"无法获取Settings签名: {e}")
        else:
            print("❌ Settings不存在")
        
        print("\n=== 4. 检查config模块 ===")
        if hasattr(chromadb, 'config'):
            print("✅ config模块存在")
            print(f"config内容: {dir(chromadb.config)}")
            
            if hasattr(chromadb.config, 'Settings'):
                print("✅ config.Settings存在")
                try:
                    sig = inspect.signature(chromadb.config.Settings)
                    print(f"config.Settings签名: {sig}")
                except Exception as e:
                    print(f"无法获取config.Settings签名: {e}")
        else:
            print("❌ config模块不存在")
        
        print("\n=== 5. 尝试不同的初始化方式 ===")
        
        # 方式1: 直接使用Client
        print("尝试方式1: chromadb.Client()")
        try:
            client1 = chromadb.Client()
            print("✅ 方式1成功")
        except Exception as e:
            print(f"❌ 方式1失败: {e}")
        
        # 方式2: 使用Settings
        print("尝试方式2: chromadb.Client(Settings())")
        try:
            if hasattr(chromadb, 'Settings'):
                settings = chromadb.Settings()
                client2 = chromadb.Client(settings)
                print("✅ 方式2成功")
            else:
                print("❌ Settings不存在")
        except Exception as e:
            print(f"❌ 方式2失败: {e}")
        
        # 方式3: 使用config.Settings
        print("尝试方式3: chromadb.Client(config.Settings())")
        try:
            if hasattr(chromadb.config, 'Settings'):
                config_settings = chromadb.config.Settings()
                client3 = chromadb.Client(config_settings)
                print("✅ 方式3成功")
            else:
                print("❌ config.Settings不存在")
        except Exception as e:
            print(f"❌ 方式3失败: {e}")
        
        return True
        
    except ImportError as e:
        print(f"❌ ChromaDB导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        return False

if __name__ == "__main__":
    analyze_chroma_api() 