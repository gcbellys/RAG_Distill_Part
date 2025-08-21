#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖安装脚本
用于安装项目所需的所有依赖包
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command: str, description: str) -> bool:
    """运行命令"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✅ {description} 成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} 失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python版本过低，需要Python 3.8或更高版本")
        return False
    print(f"✅ Python版本: {version.major}.{version.minor}.{version.micro}")
    return True

def install_basic_dependencies():
    """安装基础依赖"""
    dependencies = [
        "torch>=1.9.0",
        "transformers>=4.20.0",
        "sentence-transformers>=2.2.0",
        "chromadb>=0.4.0",
        "numpy>=1.21.0",
        "pandas>=1.3.0",
        "requests>=2.25.0",
        "loguru>=0.6.0",
        "tqdm>=4.62.0",
        "click>=8.0.0",
        "rich>=12.0.0"
    ]
    
    for dep in dependencies:
        if not run_command(f"pip install {dep}", f"安装 {dep}"):
            return False
    return True

def install_optional_dependencies():
    """安装可选依赖"""
    optional_deps = [
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "httpx>=0.24.0",
        "scikit-learn>=1.0.0",
        "scipy>=1.7.0"
    ]
    
    print("\n📦 安装可选依赖...")
    for dep in optional_deps:
        run_command(f"pip install {dep}", f"安装 {dep}")
    
    return True

def install_development_dependencies():
    """安装开发依赖"""
    dev_deps = [
        "pytest>=6.2.0",
        "pytest-cov>=2.12.0",
        "black>=21.0.0",
        "flake8>=3.9.0"
    ]
    
    print("\n🔧 安装开发依赖...")
    for dep in dev_deps:
        run_command(f"pip install {dep}", f"安装 {dep}")
    
    return True

def create_sample_data():
    """创建示例数据"""
    print("\n📝 创建示例数据...")
    
    # 创建数据目录
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # 创建示例医学数据
    sample_data = [
        {
            "case_id": "case_001",
            "text": "Patient complains of chest pain for 3 days, pain located behind sternum, crushing in nature, accompanied by palpitations. ECG shows ST segment elevation, troponin elevated. Consider acute myocardial infarction, recommend coronary angiography.",
            "specialty": "cardiac"
        },
        {
            "case_id": "case_002", 
            "text": "Patient presents with cough and sputum for 2 weeks, accompanied by fever. Chest X-ray shows right lower lobe infiltrate. Consider pneumonia, recommend chest CT scan.",
            "specialty": "pulmonary"
        },
        {
            "case_id": "case_003",
            "text": "Patient's liver function tests show elevated ALT and AST, ultrasound shows hypoechoic nodule in right lobe of liver. Consider liver space-occupying lesion, recommend contrast-enhanced CT scan.",
            "specialty": "gastrointestinal"
        },
        {
            "case_id": "case_004",
            "text": "Patient found mass in neck, ultrasound shows left thyroid lobe nodule, approximately 2cm in size. Recommend fine needle aspiration biopsy.",
            "specialty": "endocrine"
        }
    ]
    
    import json
    with open(data_dir / "sample_medical_data.json", "w", encoding="utf-8") as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)
    
    print("✅ 示例数据创建完成: data/sample_medical_data.json")

def create_config_files():
    """创建配置文件"""
    print("\n⚙️ 创建配置文件...")
    
    # 创建.env文件模板
    env_template = """# API密钥配置
DEEPSEEK_API_KEY=your_deepseek_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# 系统配置
LOG_LEVEL=INFO
ENABLE_GPU=true
"""
    
    with open(".env.template", "w", encoding="utf-8") as f:
        f.write(env_template)
    
    print("✅ 配置文件创建完成: .env.template")

def main():
    """主函数"""
    print("🚀 RAG Evidence4Organ 依赖安装")
    print("=" * 50)
    
    # 检查Python版本
    if not check_python_version():
        return
    
    # 升级pip
    run_command("python -m pip install --upgrade pip", "升级pip")
    
    # 安装基础依赖
    print("\n📦 安装基础依赖...")
    if not install_basic_dependencies():
        print("❌ 基础依赖安装失败")
        return
    
    # 安装可选依赖
    install_optional_dependencies()
    
    # 安装开发依赖
    install_development_dependencies()
    
    # 创建示例数据
    create_sample_data()
    
    # 创建配置文件
    create_config_files()
    
    print("\n" + "=" * 50)
    print("✅ 依赖安装完成！")
    print("\n📋 下一步操作:")
    print("1. 复制 .env.template 为 .env 并配置API密钥")
    print("2. 运行知识蒸馏: python scripts/run_distillation.py --input data/sample_medical_data.json --output results/extractions.json")
    print("3. 构建RAG系统: python scripts/run_rag_system.py --corpus results/extractions_rag.json --build")
    print("\n📚 更多信息请查看 README.md")

if __name__ == "__main__":
    main() 