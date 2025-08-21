# 🌐 云服务器部署配置指南

## 📋 **1. 环境准备**

### Python环境安装
```bash
# 检查Python版本
python3 --version

# 如果没有Python 3.8+，安装Python
# Ubuntu/Debian:
sudo apt update
sudo apt install python3.8 python3.8-pip python3.8-venv

# CentOS/RHEL:
sudo yum install python38 python38-pip
```

### 安装项目依赖
```bash
cd /opt/RAG_Evidence4Organ

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 如果没有requirements.txt，手动安装主要依赖：
pip install openai requests python-dotenv
```

## 🔑 **2. API密钥配置**

### 创建环境变量文件
```bash
cd /opt/RAG_Evidence4Organ

# 创建.env文件
cat > .env << 'EOF'
# DeepSeek API 配置
DEEPSEEK_API_KEY_1=your_api_key_1
DEEPSEEK_API_KEY_2=your_api_key_2
DEEPSEEK_API_KEY_3=your_api_key_3
DEEPSEEK_API_KEY_4=your_api_key_4
DEEPSEEK_API_KEY_5=your_api_key_5
DEEPSEEK_API_KEY_6=your_api_key_6
DEEPSEEK_API_KEY_7=your_api_key_7
DEEPSEEK_API_KEY_8=your_api_key_8
DEEPSEEK_API_KEY_9=your_api_key_9
DEEPSEEK_API_KEY_10=your_api_key_10

# 其他配置
PYTHONPATH=/opt/RAG_Evidence4Organ
EOF

# 设置权限
chmod 600 .env
```

### 或者直接修改configs/api_keys.py
```bash
# 编辑API密钥文件
vim configs/api_keys.py
```

## 📂 **3. 路径配置修改**

### 修改系统配置文件
```bash
vim configs/system_config.py
```

**需要修改的内容：**
```python
# 原来可能是相对路径，改为绝对路径
BASE_DIR = "/opt/RAG_Evidence4Organ"

# 数据路径
DATA_PATHS = {
    "dataset": f"{BASE_DIR}/dataset",
    "results": f"{BASE_DIR}/Question_Distillation_v2/results",
    "logs": f"{BASE_DIR}/logs"
}

# 确保所有路径都是绝对路径
```

### 修改启动脚本
```bash
vim scripts/distillation/start_universal_v3_distillation.sh
```

**需要修改的内容：**
```bash
#!/bin/bash

# 设置工作目录为绝对路径
WORK_DIR="/opt/RAG_Evidence4Organ"
cd $WORK_DIR

# 设置Python路径
export PYTHONPATH=$WORK_DIR:$PYTHONPATH

# 加载环境变量
source $WORK_DIR/.env

# 激活虚拟环境
source $WORK_DIR/venv/bin/activate

# 其余内容保持不变...
```

## 🛠️ **4. 权限和目录设置**

```bash
# 创建必要目录
mkdir -p /opt/RAG_Evidence4Organ/logs
mkdir -p /opt/RAG_Evidence4Organ/Question_Distillation_v2/results
mkdir -p /opt/RAG_Evidence4Organ/test_output

# 设置权限
chown -R root:root /opt/RAG_Evidence4Organ
chmod -R 755 /opt/RAG_Evidence4Organ

# 给脚本执行权限
chmod +x /opt/RAG_Evidence4Organ/scripts/distillation/*.sh
chmod +x /opt/RAG_Evidence4Organ/*.sh
```

## 🧪 **5. 测试配置**

### 测试Python环境
```bash
cd /opt/RAG_Evidence4Organ
source venv/bin/activate

# 测试导入
python3 -c "
import sys
sys.path.append('/opt/RAG_Evidence4Organ')
from Question_Distillation_v2.extractors.llm_extractor import LLMExtractor
print('✅ 导入成功')
"
```

### 测试API连接
```bash
# 运行简单测试
./quick_test_distillation.sh
```

## 🚀 **6. 启动蒸馏任务**

### 单个测试
```bash
cd /opt/RAG_Evidence4Organ
source venv/bin/activate

# 测试单个文件
python3 -m Question_Distillation_v2.process_worker \
    --input_file dataset/your_test_file.txt \
    --api_key_index 1 \
    --output_dir test_output/worker_api_1
```

### 批量蒸馏
```bash
# 启动多worker蒸馏
./scripts/distillation/start_universal_v3_distillation.sh
```

## 📊 **7. 监控和日志**

### 查看运行状态
```bash
# 查看tmux会话
tmux list-sessions

# 进入特定会话
tmux attach-session -t distillation_worker_1

# 查看日志
tail -f logs/distillation.log
tail -f Question_Distillation_v2/results/processing.log
```

### 常见问题排查
```bash
# 检查进程
ps aux | grep python

# 检查端口占用
netstat -tlnp | grep python

# 检查磁盘空间
df -h

# 检查内存使用
free -h
```

## ⚠️ **8. 注意事项**

1. **防火墙设置**：确保必要端口开放
2. **资源监控**：定期检查CPU、内存、磁盘使用情况
3. **日志管理**：定期清理日志文件，避免磁盘满
4. **备份策略**：重要结果定期备份
5. **API限流**：注意API调用频率限制

## 🔄 **9. 更新部署**

```bash
# 停止当前任务
tmux kill-server

# 备份当前结果
cp -r Question_Distillation_v2/results Question_Distillation_v2/results_backup_$(date +%Y%m%d)

# 重新上传并解压新版本
# 然后重复上述配置步骤
``` 