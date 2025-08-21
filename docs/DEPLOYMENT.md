# 部署指南

## 环境要求

### 系统要求
- **操作系统**: Linux (Ubuntu 18.04+), macOS, Windows 10+
- **Python**: 3.8 或更高版本
- **内存**: 最少 8GB RAM，推荐 16GB+
- **存储**: 最少 10GB 可用空间
- **GPU**: 可选，支持 CUDA 11.0+ (用于加速模型推理)

### 硬件推荐
- **CPU**: 4核心以上
- **内存**: 16GB+
- **GPU**: NVIDIA RTX 3060 或更高 (用于Bio-LM模型)
- **存储**: SSD 50GB+

## 安装步骤

### 1. 环境准备

#### 克隆项目
```bash
git clone <repository-url>
cd RAG_Evidence4Organ
```

#### 创建虚拟环境
```bash
# 使用conda
conda create -n rag-evidence python=3.8
conda activate rag-evidence

# 或使用venv
python -m venv rag-evidence
source rag-evidence/bin/activate  # Linux/macOS
# rag-evidence\Scripts\activate  # Windows
```

### 2. 安装依赖

#### 自动安装
```bash
python scripts/install_dependencies.py
```

#### 手动安装
```bash
# 升级pip
python -m pip install --upgrade pip

# 安装基础依赖
pip install -r requirements.txt

# 安装开发依赖（可选）
pip install pytest black flake8
```

### 3. 配置环境

#### 创建配置文件
```bash
# 复制环境变量模板
cp .env.template .env

# 编辑配置文件
nano .env
```

#### 配置API密钥
```bash
# 在.env文件中配置
DEEPSEEK_API_KEY=your_deepseek_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 4. 验证安装

#### 测试配置
```bash
python configs/system_config.py
python configs/model_config.py
```

#### 测试模型
```bash
# 测试Bio-LM模型
python rag_system/models/bio_lm_embedding.py

# 测试BGE模型
python rag_system/models/bge_embedding.py
```

## 快速开始

### 1. 准备数据

#### 创建示例数据
```bash
# 运行安装脚本会自动创建示例数据
python scripts/install_dependencies.py

# 或手动创建
mkdir -p data
```

#### 数据格式
```json
[
    {
        "case_id": "case_001",
        "text": "Patient complains of chest pain for 3 days, pain located behind the sternum, crushing in nature, accompanied by palpitations. ECG shows ST segment elevation, troponin elevated.",
        "specialty": "cardiac"
    }
]
```

### 2. 运行知识蒸馏

#### 基本用法
```bash
python scripts/run_distillation.py \
    --input data/sample_medical_data.json \
    --output results/extractions.json \
    --model deepseek \
    --batch-size 10
```

#### 高级选项
```bash
python scripts/run_distillation.py \
    --input data/medical_texts.json \
    --output results/extractions.json \
    --model deepseek \
    --api-key your_api_key \
    --batch-size 5 \
    --max-cases 100
```

### 3. 构建RAG系统

#### 构建向量数据库
```bash
python scripts/run_rag_system.py \
    --corpus results/extractions_rag.json \
    --model bio_lm \
    --build
```

#### 测试搜索功能
```bash
python scripts/run_rag_system.py \
    --corpus results/extractions_rag.json \
    --model bio_lm \
    --test
```

## 生产环境部署

### 1. Docker部署

#### 创建Dockerfile
```dockerfile
FROM python:3.8-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建必要目录
RUN mkdir -p data logs results

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "scripts/run_distillation.py", "--help"]
```

#### 构建和运行
```bash
# 构建镜像
docker build -t rag-evidence .

# 运行容器
docker run -d \
    --name rag-evidence \
    -p 8000:8000 \
    -v $(pwd)/data:/app/data \
    -v $(pwd)/results:/app/results \
    -e DEEPSEEK_API_KEY=your_key \
    rag-evidence
```

### 2. 云服务器部署

#### AWS EC2部署
```bash
# 连接到EC2实例
ssh -i your-key.pem ubuntu@your-instance-ip

# 安装依赖
sudo apt-get update
sudo apt-get install -y python3-pip git

# 克隆项目
git clone <repository-url>
cd RAG_Evidence4Organ

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
export DEEPSEEK_API_KEY=your_key

# 运行服务
nohup python scripts/run_distillation.py --input data/input.json --output results/output.json &
```

#### 使用systemd服务
```bash
# 创建服务文件
sudo nano /etc/systemd/system/rag-evidence.service
```

```ini
[Unit]
Description=RAG Evidence4Organ Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/RAG_Evidence4Organ
Environment=PATH=/home/ubuntu/RAG_Evidence4Organ/venv/bin
ExecStart=/home/ubuntu/RAG_Evidence4Organ/venv/bin/python scripts/run_distillation.py --input data/input.json --output results/output.json
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# 启动服务
sudo systemctl enable rag-evidence
sudo systemctl start rag-evidence
sudo systemctl status rag-evidence
```

### 3. 负载均衡配置

#### Nginx配置
```nginx
upstream rag_backend {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}

server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://rag_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 监控和维护

### 1. 日志管理

#### 日志配置
```python
# 在代码中配置日志
from loguru import logger

logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO"
)
```

#### 日志监控
```bash
# 实时查看日志
tail -f logs/distillation.log

# 查看错误日志
grep "ERROR" logs/*.log

# 日志分析
python -c "
import json
from collections import Counter
with open('logs/distillation.log') as f:
    lines = f.readlines()
    errors = [line for line in lines if 'ERROR' in line]
    print(f'错误数量: {len(errors)}')
"
```

### 2. 性能监控

#### 资源监控
```bash
# 监控CPU和内存
htop

# 监控GPU使用
nvidia-smi

# 监控磁盘使用
df -h
```

#### 应用性能
```python
import time
import psutil

def monitor_performance():
    start_time = time.time()
    process = psutil.Process()
    
    # 执行任务
    # ...
    
    end_time = time.time()
    memory_usage = process.memory_info().rss / 1024 / 1024  # MB
    
    print(f"执行时间: {end_time - start_time:.2f}秒")
    print(f"内存使用: {memory_usage:.2f}MB")
```

### 3. 备份策略

#### 数据备份
```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/rag_evidence_$DATE"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据
cp -r data/ $BACKUP_DIR/
cp -r results/ $BACKUP_DIR/
cp -r chroma_db/ $BACKUP_DIR/

# 压缩备份
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR

echo "备份完成: $BACKUP_DIR.tar.gz"
```

#### 定时备份
```bash
# 添加到crontab
crontab -e

# 每天凌晨2点备份
0 2 * * * /path/to/backup.sh
```

## 故障排除

### 常见问题

#### 1. 模型下载失败
```bash
# 解决方案：使用镜像源
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple transformers
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple torch
```

#### 2. 内存不足
```bash
# 解决方案：减少批处理大小
python scripts/run_distillation.py --batch-size 5

# 或使用CPU模式
export CUDA_VISIBLE_DEVICES=""
```

#### 3. API调用失败
```bash
# 检查API密钥
echo $DEEPSEEK_API_KEY

# 检查网络连接
curl -I https://api.deepseek.com

# 检查API配额
# 登录DeepSeek控制台查看使用情况
```

#### 4. ChromaDB连接失败
```bash
# 检查端口占用
netstat -tulpn | grep 8000

# 重启ChromaDB
pkill -f chromadb
python scripts/run_rag_system.py --corpus data.json --build
```

### 性能优化

#### 1. 模型优化
```python
# 使用半精度
import torch
model = model.half()

# 使用量化
from transformers import AutoModel
model = AutoModel.from_pretrained("model_name", torch_dtype=torch.float16)
```

#### 2. 批处理优化
```python
# 动态批处理大小
def get_optimal_batch_size():
    import psutil
    memory_gb = psutil.virtual_memory().total / 1024**3
    if memory_gb < 8:
        return 8
    elif memory_gb < 16:
        return 16
    else:
        return 32
```

#### 3. 缓存优化
```python
# 使用Redis缓存
import redis
r = redis.Redis(host='localhost', port=6379, db=0)

def get_cached_embedding(text):
    key = f"embedding:{hash(text)}"
    cached = r.get(key)
    if cached:
        return json.loads(cached)
    else:
        embedding = model.encode(text)
        r.setex(key, 3600, json.dumps(embedding.tolist()))
        return embedding
```

## 安全考虑

### 1. API密钥安全
```bash
# 使用环境变量
export DEEPSEEK_API_KEY="your_key"

# 或使用密钥管理服务
# AWS Secrets Manager, Azure Key Vault等
```

### 2. 数据安全
```bash
# 加密敏感数据
pip install cryptography

# 使用SSL/TLS
# 配置HTTPS证书
```

### 3. 访问控制
```python
# 实现API认证
from functools import wraps
import jwt

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return {'error': 'No token provided'}, 401
        try:
            payload = jwt.decode(token, 'secret', algorithms=['HS256'])
        except:
            return {'error': 'Invalid token'}, 401
        return f(*args, **kwargs)
    return decorated
```

## 扩展部署

### 1. 微服务架构
```yaml
# docker-compose.yml
version: '3.8'
services:
  distillation:
    build: .
    environment:
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
    volumes:
      - ./data:/app/data
      - ./results:/app/results
  
  rag_system:
    build: .
    command: python scripts/run_rag_system.py --corpus results/extractions_rag.json --build
    volumes:
      - ./results:/app/results
      - ./chroma_db:/app/chroma_db
  
  api_server:
    build: .
    command: python rag_system/api/rag_api.py
    ports:
      - "8000:8000"
    depends_on:
      - rag_system
```

### 2. Kubernetes部署
```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-evidence
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rag-evidence
  template:
    metadata:
      labels:
        app: rag-evidence
    spec:
      containers:
      - name: rag-evidence
        image: rag-evidence:latest
        ports:
        - containerPort: 8000
        env:
        - name: DEEPSEEK_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: deepseek-key
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
```

这样，您就有了一个完整的部署指南，涵盖了从本地开发到生产环境的各个方面。 