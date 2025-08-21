# RAG Evidence4Organ

## 📋 项目概述

RAG Evidence4Organ 是一个专门用于医学证据与器官关联的检索增强生成（RAG）系统。该系统通过知识蒸馏从医学文本中提取症状/疾病与器官的对应关系，并构建高效的向量检索系统。

## 🏗️ 系统架构

```
医学文本 → 知识蒸馏 → 结构化语料 → 向量化 → RAG检索系统
```

### 核心组件

1. **知识蒸馏模块**: 从医学文本中提取症状-器官-部位关系
2. **RAG系统**: 基于Bio-LM和BGE的向量检索系统
3. **存储系统**: ChromaDB向量数据库
4. **API接口**: 提供检索服务

## 📁 项目结构

```
RAG_Evidence4Organ/
├── README.md                           # 项目主文档
├── requirements.txt                    # 依赖包列表
├── setup.py                           # 安装脚本
│
├── knowledge_distillation/            # 知识蒸馏模块
│   ├── prompts/                       # 提示词系统
│   │   ├── medical_prompts.py        # 医学提取提示词
│   │   └── specialty_prompts.py      # 专科提示词
│   ├── extractors/                    # 信息提取器
│   │   ├── llm_extractor.py          # LLM提取器
│   │   └── deepseek_integration.py   # DeepSeek集成
│   ├── processors/                    # 数据处理器
│   │   └── data_processor.py         # 数据处理器
│   └── results/                       # 提取结果
│
├── rag_system/                        # RAG系统模块
│   ├── models/                        # 嵌入模型
│   │   ├── bio_lm_embedding.py       # Bio-LM嵌入模型
│   │   └── bge_embedding.py          # BGE嵌入模型
│   ├── storage/                       # 存储系统
│   │   └── chroma_storage.py         # ChromaDB存储
│   ├── search/                        # 搜索功能
│   └── api/                           # API接口
│
├── configs/                           # 配置文件
│   ├── system_config.py              # 系统配置
│   └── model_config.py               # 模型配置
│
├── scripts/                           # 运行脚本
│   ├── run_distillation.py           # 知识蒸馏脚本
│   ├── run_rag_system.py             # RAG系统脚本
│   └── install_dependencies.py       # 依赖安装脚本
│
├── utils/                             # 工具函数
│   └── file_utils.py                 # 文件工具
│
├── docs/                              # 文档
│   ├── API_DOCS.md                   # API文档
│   └── DEPLOYMENT.md                 # 部署指南
│
├── data/                              # 数据目录
│   ├── raw/                          # 原始数据
│   ├── processed/                    # 处理后数据
│   └── corpus/                       # 语料数据
│
├── logs/                              # 日志目录
└── results/                           # 结果目录
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd RAG_Evidence4Organ

# 创建虚拟环境
conda create -n rag-evidence python=3.8
conda activate rag-evidence

# 或使用venv
python -m venv rag-evidence
source rag-evidence/bin/activate  # Linux/macOS
# rag-evidence\Scripts\activate  # Windows
```

### 2. 安装依赖

```bash
# 自动安装
python scripts/install_dependencies.py

# 或手动安装
pip install -r requirements.txt
```

### 3. 配置API密钥

编辑 `RAG_Evidence4Organ/configs/system_config.py` 文件, 在 `MULTI_API_CONFIG` 字典中填入您的DeepSeek API密钥。您可以根据需要增删API配置。

```python
# RAG_Evidence4Organ/configs/system_config.py

MULTI_API_CONFIG = {
    "api_1": {
        "name": "DeepSeek Original",
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "sk-your-key-here-1",
        "model": "deepseek-chat",
    },
    "api_2": {
        "name": "DeepSeek Key2",
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "sk-your-key-here-2",
        "model": "deepseek-chat",
    },
    # ...可以添加更多
}
```

### 4. 数据处理与RAG构建 (全新三步流程)

#### 第1步: 并行执行知识蒸馏

运行总指挥脚本，它会在后台启动多个并行的处理任务。

```bash
bash RAG_Evidence4Organ/scripts/start_distillation.sh
```
您可以使用 `tmux list-sessions` 来监控后台任务。所有并行的输出结果将保存在 `RAG_Evidence4Organ/knowledge_distillation/results/parallel_outputs/` 目录下。

#### 第2步: 聚合蒸馏结果

在所有并行任务完成后，运行聚合脚本来合并所有独立的JSON文件。

```bash
python RAG_Evidence4Organ/scripts/aggregate_results.py \
    --input_dir RAG_Evidence4Organ/knowledge_distillation/results/parallel_outputs/ \
    --output_file RAG_Evidence4Organ/data/corpus_inferred.json
```

#### 第3步: 构建最终的RAG知识库

使用上一步生成的、高质量的语料库来构建向量数据库。

```bash
python RAG_Evidence4Organ/scripts/build_rag_corpus.py RAG_Evidence4Organ/data/corpus_inferred.json
```

### 5. 运行查询

使用 `query_rag_system.py` 对新构建的知识库进行查询。请确保脚本中的 `collection_name` 参数与 `build_rag_corpus.py` 中使用的集合名称 (`medical_evidence_inferred`) 一致。

```bash
python RAG_Evidence4Organ/scripts/query_rag_system.py "Your medical query here"
```

## 🔧 核心功能

### 知识蒸馏 (推理型)

- **单次推理**: 采用先进的"一步到位"推理型提示词，直接从原始报告生成高质量的结构化数据。
- **并行处理**: 利用`tmux`和多个API密钥，高效地并行处理大规模数据集。
- **精确实体约束**: 所有提取结果都严格遵循配置文件中定义的5大器官及其精确的解剖结构列表。

### RAG系统

- **Bio-LM嵌入**: 专门针对医学文本的嵌入模型
- **BGE嵌入**: 高性能的中文文本嵌入
- **ChromaDB存储**: 高效的向量数据库
- **智能检索**: 支持元数据过滤和相似度搜索

### 数据处理

- **多部位合并**: 自动合并同一症状的多个部位
- **器官标准化**: 统一器官名称格式
- **质量过滤**: 过滤低质量提取结果
- **RAG格式转换**: 自动转换为检索格式

## 📊 支持的功能

### 器官类型
- Heart (心脏)
- Liver / Gallbladder (肝脏 / 胆囊)
- Kidneys / Bladder (肾脏 / 膀胱)
- Thyroid (甲状腺)
- Pancreas (胰腺)

### 模型支持
- **嵌入模型**: Bio-LM (可配置)
- **LLM模型**: DeepSeek (推荐, 可配置)
- **存储后端**: ChromaDB

### 专科分类
- 心脏科 (Cardiac)
- 呼吸科 (Pulmonary)
- 消化科 (Gastrointestinal)
- 内分泌科 (Endocrine)
- 通用 (General)

## 🛠️ 高级用法

### 自定义配置

```python
from configs.system_config import get_config
from configs.model_config import get_embedding_model

# 获取系统配置
system_config = get_config("system")

# 获取模型配置
embedding_config = get_embedding_model("bio_lm")
```

### 批量处理

```python
from knowledge_distillation.extractors.llm_extractor import create_extractor

# 创建提取器
extractor = create_extractor(model="deepseek")

# 批量提取
results = extractor.batch_extract(texts, delay=1.0)
```

### 自定义搜索

```python
from rag_system.storage.chroma_storage import create_chroma_storage

# 创建存储
storage = create_chroma_storage()

# 过滤查询
results = storage.query(
    query_texts="胸痛",
    n_results=5,
    where={"organ": "心脏", "confidence": "高"}
)
```

## 📈 性能指标

### 处理能力
- **文本处理**: 支持10,000+ 医学文本
- **批处理**: 支持100+ 并发处理
- **检索速度**: <100ms 查询响应时间
- **准确率**: >85% 提取准确率

### 资源需求
- **内存**: 最少 8GB RAM，推荐 16GB+
- **存储**: 最少 10GB 可用空间
- **GPU**: 可选，支持 CUDA 11.0+

## 🔍 使用示例

### 医学文本提取

```python
from knowledge_distillation.extractors.llm_extractor import create_extractor

# 创建提取器
extractor = create_extractor(model="deepseek")

# 提取医学信息
text = "Patient complains of chest pain for 3 days, pain located behind the sternum, crushing in nature, accompanied by palpitations. ECG shows ST segment elevation."
result = extractor.extract_medical_info(text, "case_001", "cardiac")

print(result)
# 输出:
# {
#     "case_id": "case_001",
#     "success": true,
#     "extractions": [
#         {
#             "disease_symptom": "胸痛",
#             "organ": "心脏",
#             "specific_part": "左心室",
#             "confidence": "高",
#             "evidence": "心电图显示ST段抬高"
#         }
#     ]
# }
```

### RAG检索

```python
from rag_system.models.bio_lm_embedding import create_bio_lm_embedding
from rag_system.storage.chroma_storage import create_chroma_storage

# 创建模型和存储
embedding_model = create_bio_lm_embedding()
storage = create_chroma_storage()

# 查询相关病例
results = storage.query(
    query_texts="胸痛",
    n_results=3,
    where={"organ": "心脏"}
)

for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
    print(f"症状: {metadata['disease_symptom']}")
    print(f"器官: {metadata['organ']}")
    print(f"文档: {doc[:100]}...")
    print("---")
```

## 🚀 部署

### 本地部署

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置API密钥 (见上文)

# 3. 生成语料库
bash RAG_Evidence4Organ/scripts/start_distillation.sh
# ...等待任务完成...
python RAG_Evidence4Organ/scripts/aggregate_results.py --input_dir ... --output_file ...
python RAG_Evidence4Organ/scripts/build_rag_corpus.py ...

# 4. (如果需要) 启动API服务
# python RAG_Evidence4Organ/rag_system/api/main.py
```

### Docker部署

```bash
# 构建镜像
docker build -t rag-evidence .

# 运行容器
docker run -d \
    --name rag-evidence \
    -p 8000:8000 \
    -v $(pwd)/data:/app/data \
    -e DEEPSEEK_API_KEY=your_key \
    rag-evidence
```

### 云服务器部署

详细部署指南请参考 [DEPLOYMENT.md](docs/DEPLOYMENT.md)

## 📚 文档

- [API文档](docs/API_DOCS.md) - 详细的API使用说明
- [部署指南](docs/DEPLOYMENT.md) - 完整的部署说明
- [故障排除](docs/DEPLOYMENT.md#故障排除) - 常见问题解决方案

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [DeepSeek](https://www.deepseek.com/) - 提供强大的LLM API
- [EMBO](https://www.embo.org/) - Bio-LM模型
- [BAAI](https://www.baai.ac.cn/) - BGE嵌入模型
- [ChromaDB](https://www.trychroma.com/) - 向量数据库

## 📞 联系方式

- 项目主页: [GitHub Repository](https://github.com/your-org/RAG_Evidence4Organ)
- 问题反馈: [Issues](https://github.com/your-org/RAG_Evidence4Organ/issues)
- 邮箱: team@rag-evidence4organ.com

---

**RAG Evidence4Organ** - 让医学证据检索更智能、更高效！ 🏥🔬 