# 通用器官提取功能使用指南

## 📋 功能概述

通用器官提取功能允许系统从医学文本中提取与**所有器官系统**相关的症状-器官对应关系，而不仅限于5个指定器官。这大大扩展了系统的应用范围。

## 🎯 核心特性

### 1. 支持所有器官系统
- **心血管系统**: 心脏、血管
- **呼吸系统**: 肺部、气道
- **消化系统**: 胃、肠道、肝脏、胰腺等
- **神经系统**: 大脑、脊髓、神经
- **肌肉骨骼系统**: 骨骼、肌肉、关节
- **内分泌系统**: 甲状腺、胰腺、肾上腺等
- **泌尿生殖系统**: 肾脏、膀胱、生殖器官
- **皮肤系统**: 皮肤
- **其他所有器官系统**

### 2. 智能约束机制
- **5个指定器官**: 心脏、肝脏、肾脏、甲状腺、胰腺 - 使用精确的解剖结构列表
- **其他器官**: 允许LLM基于医学知识自由推断相关解剖结构

### 3. 分类标识
每个提取结果都包含 `organ_category` 字段：
- `"specified"`: 5个指定器官之一
- `"other"`: 其他器官

## 🚀 使用方法

### 方法1: 使用通用启动脚本

```bash
# 启动通用器官提取
bash scripts/distillation/start_universal_distillation.sh

# 监控进度
tmux list-sessions
tmux attach-session -t distill_universal_worker_api_1

# 聚合结果
python scripts/distillation/aggregate_results.py \
    --input_dir RAG_Evidence4Organ/result_universal \
    --output_file RAG_Evidence4Organ/data/corpus_universal.json

# 构建RAG系统
python scripts/rag_tools/build_rag_corpus.py RAG_Evidence4Organ/data/corpus_universal.json
```

### 方法2: 手动指定参数

```bash
# 直接运行worker，指定通用模式
python RAG_Evidence4Organ/knowledge_distillation/process_worker.py \
    --output_dir RAG_Evidence4Organ/result_universal \
    --api_key_name api_1 \
    --file_list task_list.txt \
    --prompt_type universal
```

### 方法3: 修改现有脚本

编辑 `scripts/distillation/start_distillation.sh`，将 `PROMPT_TYPE` 设置为 `"universal"`：

```bash
# 提示词类型: universal(所有器官) 或 restricted(仅5个指定器官)
PROMPT_TYPE="universal"
```

## 📊 输出格式

### 指定器官示例
```json
{
    "symptom_or_disease": "chest pain",
    "inferred_organ": "Heart",
    "suggested_anatomical_parts_to_examine": [
        "Aortic Valve",
        "Coronary Arteries", 
        "Pericardium"
    ],
    "evidence_from_report": "Patient complains of chest pain for 3 days...",
    "case_id": "10001",
    "organ_category": "specified"
}
```

### 其他器官示例
```json
{
    "symptom_or_disease": "severe headache",
    "inferred_organ": "Brain",
    "suggested_anatomical_parts_to_examine": [
        "Frontal Lobe",
        "Temporal Lobe",
        "Cerebral Cortex"
    ],
    "evidence_from_report": "Patient presents with severe headache...",
    "case_id": "10002",
    "organ_category": "other"
}
```

## 🔍 统计信息

聚合脚本会自动生成器官分布统计：

```
📊 器官分布统计:
  📍 指定器官 (5个核心器官):
    Heart: 150
    Liver: 89
    Kidneys: 67
    Thyroid: 45
    Pancreas: 23
  🌐 其他器官:
    Brain: 234
    Lungs: 189
    Stomach: 156
    Spine: 98
    Eyes: 67
```

## ⚙️ 配置选项

### 提示词类型选择
- `universal`: 支持所有器官系统
- `restricted`: 仅支持5个指定器官

### 输出目录
- 通用模式: `RAG_Evidence4Organ/result_universal`
- 限制模式: `RAG_Evidence4Organ/result_new`

## 🎯 应用场景

### 1. 全面医学分析
适用于需要分析所有器官系统的医学研究，如：
- 全身症状分析
- 多系统疾病研究
- 综合医学评估

### 2. 专科医学研究
可以针对特定器官系统进行深入研究：
- 神经科症状分析
- 呼吸系统疾病研究
- 消化系统症状提取

### 3. 医学教育
为医学教育提供全面的症状-器官对应关系数据。

## 🔧 高级用法

### 自定义器官映射
可以修改 `configs/model_config.py` 中的 `ORGAN_ANATOMY_STRUCTURE` 来添加更多指定器官：

```python
ORGAN_ANATOMY_STRUCTURE = {
    "Heart": [...],
    "Liver": [...],
    # 添加新的指定器官
    "Brain": [
        "Frontal Lobe", "Temporal Lobe", "Parietal Lobe",
        "Occipital Lobe", "Cerebellum", "Brainstem"
    ],
    "Lungs": [
        "Left Upper Lobe", "Left Lower Lobe", 
        "Right Upper Lobe", "Right Middle Lobe", "Right Lower Lobe"
    ]
}
```

### 自定义验证规则
可以修改 `validate_extraction()` 函数来添加自定义的验证规则。

## 📈 性能对比

| 特性 | 限制模式 | 通用模式 |
|------|----------|----------|
| 支持器官数量 | 5个 | 所有器官 |
| 解剖结构约束 | 严格 | 混合（指定+自由） |
| 提取范围 | 有限 | 全面 |
| 处理速度 | 较快 | 稍慢 |
| 数据质量 | 高精度 | 高覆盖 |

## 🚨 注意事项

1. **API成本**: 通用模式可能产生更多的API调用，请注意成本控制
2. **数据质量**: 其他器官的解剖结构由LLM推断，可能存在一定的不确定性
3. **存储空间**: 通用模式会产生更多的数据，请确保有足够的存储空间
4. **处理时间**: 通用模式需要更长的处理时间

## 🔄 迁移指南

### 从限制模式迁移到通用模式

1. **备份现有数据**
```bash
cp -r RAG_Evidence4Organ/result_new RAG_Evidence4Organ/result_new_backup
```

2. **修改配置**
```bash
# 编辑启动脚本
sed -i 's/PROMPT_TYPE="restricted"/PROMPT_TYPE="universal"/' scripts/distillation/start_distillation.sh
```

3. **重新运行提取**
```bash
bash scripts/distillation/start_distillation.sh
```

4. **聚合新结果**
```bash
python scripts/distillation/aggregate_results.py \
    --input_dir RAG_Evidence4Organ/result_new \
    --output_file RAG_Evidence4Organ/data/corpus_universal.json
```

## 📞 技术支持

如果遇到问题，请检查：
1. API密钥配置是否正确
2. 虚拟环境是否正确激活
3. 文件路径是否存在
4. 网络连接是否正常

---

**通用器官提取功能** - 让医学证据检索更全面、更智能！ 🏥🔬🌐 