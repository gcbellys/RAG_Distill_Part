# API 文档

## 概述

RAG Evidence4Organ 提供了完整的API接口，用于医学证据的检索和查询。

## 核心API

### 1. 知识蒸馏API

#### LLM提取器 (LLMExtractor)

```python
from knowledge_distillation.extractors.llm_extractor import create_extractor

# 创建提取器
extractor = create_extractor(model="deepseek", api_key="your_api_key")

# 提取医学信息
result = extractor.extract_medical_info(
    text="Patient complains of chest pain, ECG shows ST segment elevation",
    case_id="case_001",
    specialty="cardiac"
)
```

**参数:**
- `model`: 模型类型 ("deepseek", "openai", "claude")
- `api_key`: API密钥
- `text`: 医学文本
- `case_id`: 病例ID
- `specialty`: 专科类型

**返回:**
```json
{
    "case_id": "case_001",
    "success": true,
    "extractions": [
        {
            "disease_symptom": "胸痛",
            "organ": "心脏",
            "specific_part": "左心室",
            "confidence": "高",
            "evidence": "心电图显示ST段抬高"
        }
    ],
    "specialty": "cardiac"
}
```

#### 数据处理器 (DataProcessor)

```python
from knowledge_distillation.processors.data_processor import create_processor

# 创建处理器
processor = create_processor()

# 处理提取结果
processed_results = processor.process_extraction_results(results)

# 合并多部位提取结果
merged_results = processor.merge_multi_part_extractions(extractions)

# 转换为RAG格式
rag_corpus = processor.convert_to_rag_format(processed_results)
```

### 2. RAG系统API

#### Bio-LM嵌入模型 (BioLMEmbedding)

```python
from rag_system.models.bio_lm_embedding import create_bio_lm_embedding

# 创建Bio-LM嵌入模型
embedding_model = create_bio_lm_embedding()

# 编码文本
embeddings = embedding_model.encode(["Patient complains of chest pain", "ECG abnormality"])

# 计算相似度
similarity = embedding_model.similarity("chest pain", "cardiac pain")

# 批量相似度计算
similarities = embedding_model.batch_similarity("胸痛", texts)
```

#### BGE嵌入模型 (BGEEmbedding)

```python
from rag_system.models.bge_embedding import create_bge_embedding

# 创建BGE嵌入模型
embedding_model = create_bge_embedding()

# 编码文本
embeddings = embedding_model.encode(["Patient complains of chest pain", "ECG abnormality"])

# Top-K搜索
top_results = embedding_model.top_k_similar("chest pain", texts, k=5)
```

#### ChromaDB存储 (ChromaStorage)

```python
from rag_system.storage.chroma_storage import create_chroma_storage

# 创建存储
storage = create_chroma_storage(
    persist_directory="./chroma_db",
    collection_name="medical_evidence"
)

# 添加文档
storage.add_documents(
    documents=["Patient complains of chest pain"],
    metadatas=[{"organ": "heart"}],
    ids=["doc_1"]
)

# 查询文档
results = storage.query(
    query_texts="chest pain",
    n_results=5,
    where={"organ": "heart"}
)

# 通过嵌入向量查询
results = storage.query_by_embedding(
    query_embeddings=[[0.1, 0.2, ...]],
    n_results=5
)
```

## 配置API

### 系统配置

```python
from configs.system_config import get_config, ensure_directories

# 获取配置
system_config = get_config("system")
rag_config = get_config("rag")

# 确保目录存在
ensure_directories()
```

### 模型配置

```python
from configs.model_config import (
    get_embedding_model, 
    get_llm_model, 
    normalize_organ,
    is_allowed_organ
)

# 获取模型配置
embedding_config = get_embedding_model("bio_lm")
llm_config = get_llm_model("deepseek")

# 器官处理
normalized_organ = normalize_organ("heart")
is_valid = is_allowed_organ("心脏")
```

## 工具API

### 文件工具

```python
from utils.file_utils import (
    load_json, 
    save_json, 
    ensure_directory,
    format_file_size
)

# 加载JSON文件
data = load_json("data.json")

# 保存JSON文件
save_json(data, "output.json")

# 确保目录存在
ensure_directory("./results")

# 格式化文件大小
size_str = format_file_size(1024)  # "1.00KB"
```

## 使用示例

### 完整知识蒸馏流程

```python
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from knowledge_distillation.extractors.llm_extractor import create_extractor
from knowledge_distillation.processors.data_processor import create_processor
from utils.file_utils import load_json, save_json

# 1. 加载数据
data = load_json("data/medical_texts.json")

# 2. 创建提取器
extractor = create_extractor(model="deepseek")

# 3. 批量提取
results = []
for item in data:
    result = extractor.extract_medical_info(
        text=item["text"],
        case_id=item["case_id"],
        specialty=item.get("specialty", "general")
    )
    results.append(result)

# 4. 处理结果
processor = create_processor()
processed_results = processor.process_extraction_results(results)

# 5. 转换为RAG格式
rag_corpus = processor.convert_to_rag_format(processed_results)

# 6. 保存结果
save_json(processed_results, "results/extractions.json")
save_json(rag_corpus, "results/rag_corpus.json")
```

### 完整RAG系统流程

```python
from rag_system.models.bio_lm_embedding import create_bio_lm_embedding
from rag_system.storage.chroma_storage import create_chroma_storage
from utils.file_utils import load_json

# 1. 加载RAG语料
corpus = load_json("results/rag_corpus.json")

# 2. 创建嵌入模型
embedding_model = create_bio_lm_embedding()

# 3. 创建存储
storage = create_chroma_storage()

# 4. 准备数据
documents = [item["document"] for item in corpus]
metadatas = [
    {
        "case_id": item["case_id"],
        "organ": item["organ"],
        "disease_symptom": item["disease_symptom"]
    }
    for item in corpus
]

# 5. 计算嵌入向量
embeddings = embedding_model.encode(documents)

# 6. 添加到数据库
storage.add_embeddings(
    embeddings=embeddings.tolist(),
    documents=documents,
    metadatas=metadatas
)

# 7. 查询
results = storage.query(
    query_texts="胸痛",
    n_results=5,
    where={"organ": "心脏"}
)

print("查询结果:")
for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
    print(f"- {metadata['disease_symptom']} ({metadata['organ']}): {doc[:50]}...")
```

## 错误处理

所有API都包含适当的错误处理：

```python
try:
    result = extractor.extract_medical_info(text, case_id)
    if result["success"]:
        # 处理成功结果
        pass
    else:
        # 处理失败
        logger.error(f"提取失败: {result['error']}")
except Exception as e:
    logger.error(f"API调用异常: {e}")
```

## 性能优化

### 批处理

```python
# 批量提取
batch_results = extractor.batch_extract(texts, delay=1.0)

# 批量编码
embeddings = embedding_model.encode(texts, batch_size=32)
```

### 缓存

```python
# 使用预计算的嵌入向量
storage.add_embeddings(embeddings, documents, metadatas)
```

## 扩展开发

### 添加新的嵌入模型

```python
class CustomEmbedding:
    def __init__(self, model_name: str):
        # 初始化模型
        pass
    
    def encode(self, texts: List[str]) -> np.ndarray:
        # 实现编码逻辑
        pass
    
    def get_embedding_dimension(self) -> int:
        # 返回维度
        pass
```

### 添加新的存储后端

```python
class CustomStorage:
    def __init__(self, config: Dict[str, Any]):
        # 初始化存储
        pass
    
    def add_documents(self, documents, metadatas, ids):
        # 实现添加逻辑
        pass
    
    def query(self, query_texts, n_results):
        # 实现查询逻辑
        pass
``` 