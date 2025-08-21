#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件工具函数
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger

def ensure_directory(path: str) -> Path:
    """确保目录存在"""
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj

def load_json(file_path: str) -> Optional[Dict[str, Any]]:
    """加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载JSON文件失败 {file_path}: {e}")
        return None

def save_json(data: Dict[str, Any], file_path: str, indent: int = 2) -> bool:
    """保存JSON文件"""
    try:
        # 确保目录存在
        ensure_directory(os.path.dirname(file_path))
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        
        logger.info(f"JSON文件保存成功: {file_path}")
        return True
    except Exception as e:
        logger.error(f"保存JSON文件失败 {file_path}: {e}")
        return False

def load_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """加载JSONL文件"""
    data = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    data.append(json.loads(line))
        logger.info(f"JSONL文件加载成功: {file_path}, {len(data)} 条记录")
    except Exception as e:
        logger.error(f"加载JSONL文件失败 {file_path}: {e}")
    
    return data

def save_jsonl(data: List[Dict[str, Any]], file_path: str) -> bool:
    """保存JSONL文件"""
    try:
        # 确保目录存在
        ensure_directory(os.path.dirname(file_path))
        
        with open(file_path, 'w', encoding='utf-8') as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        logger.info(f"JSONL文件保存成功: {file_path}, {len(data)} 条记录")
        return True
    except Exception as e:
        logger.error(f"保存JSONL文件失败 {file_path}: {e}")
        return False

def get_file_size(file_path: str) -> int:
    """获取文件大小（字节）"""
    try:
        return os.path.getsize(file_path)
    except Exception as e:
        logger.error(f"获取文件大小失败 {file_path}: {e}")
        return 0

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.2f}{size_names[i]}"

def list_files(directory: str, pattern: str = "*") -> List[str]:
    """列出目录中的文件"""
    try:
        path = Path(directory)
        if not path.exists():
            return []
        
        files = list(path.glob(pattern))
        return [str(f) for f in files if f.is_file()]
    except Exception as e:
        logger.error(f"列出文件失败 {directory}: {e}")
        return []

def backup_file(file_path: str, backup_suffix: str = ".backup") -> bool:
    """备份文件"""
    try:
        if not os.path.exists(file_path):
            return False
        
        backup_path = file_path + backup_suffix
        import shutil
        shutil.copy2(file_path, backup_path)
        logger.info(f"文件备份成功: {file_path} -> {backup_path}")
        return True
    except Exception as e:
        logger.error(f"文件备份失败 {file_path}: {e}")
        return False 