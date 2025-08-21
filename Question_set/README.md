# 症状提取系统 (Question_set)

## 概述

这是一个专门用于从医学报告中提取症状描述的系统，主要用于构建测试集。与原有的 `Question_Distillation_v2` 系统不同，本系统专注于：

- **症状识别**：识别医学报告中的症状描述语句
- **基于原文的症状生成**：基于原文生成清晰、标准的症状表述
- **测试集构建**：为医学知识测试提供高质量的症状数据

## 系统架构

```
Question_set/
├── extractors/          # 提取器模块
│   └── symptom_extractor.py    # 症状提取核心逻辑
├── prompts/            # 提示词系统
│   └── symptom_prompts.py      # 症状提取专用提示词
├── processors/         # 文档处理器
│   └── document_processor.py   # 文档分块和预处理
├── scripts/            # 脚本目录
│   ├── start_symptom_extraction.sh    # 主要启动脚本
│   └── test_single_report.py          # 单报告测试脚本
├── results/            # 结果输出目录
└── symptom_worker.py   # Worker主程序
```

## 核心功能

### 1. 症状类型识别

系统能够识别以下类型的症状：

- **主观症状**：患者自述的感受（疼痛、不适、头晕、恶心等）
- **客观体征**：医生观察到的异常（肿胀、出血、皮疹、黄疸等）
- **功能异常**：器官功能障碍（呼吸困难、心律不齐、消化不良等）
- **检查异常**：实验室或影像学异常发现（血压升高、血糖异常等）
- **病理变化**：组织或器官的病理改变（炎症、坏死、增生等）

### 2. 智能文档分块

- 基于医学报告结构进行智能分块
- 识别关键章节（如 "hospital course", "assessment and plan" 等）
- 过滤包含症状关键词的有效内容
- 优化分块大小以适应LLM处理

### 3. 多种提示词策略

- **comprehensive**：综合分析提示词（推荐）
- **identification**：症状识别专用提示词
- **generation**：症状描述生成提示词
- **batch**：批量处理提示词

## 使用方法

### 1. 快速测试

在开始大规模处理前，建议先测试单个报告：

```bash
# 测试默认报告（40000）
python3 Question_set/scripts/test_single_report.py

# 测试指定报告和API
python3 Question_set/scripts/test_single_report.py --report 40001 --api api_2 --prompt comprehensive
```

### 2. 批量处理

处理40000-44914范围的所有数据（4915个文件）：

```bash
# 启动症状提取流程
./Question_set/scripts/start_symptom_extraction.sh
```

该脚本将：
- 自动分配任务给15个API
- 每个API处理约327个文件
- 使用tmux会话并行处理
- 保存详细的处理日志和结果

### 3. 监控处理进度

```bash
# 查看所有活跃的症状提取会话
tmux list-sessions | grep symptom_extract

# 连接到特定worker查看详细进度
tmux attach-session -t symptom_extract_api_1

# 实时监控所有worker的进度
watch -n 5 'echo "=== 各Worker症状提取进度 ==="; for api in api_1 api_2 api_3 api_4 api_5 api_6 api_7 api_8 api_9 api_10 api_11 api_12 api_13 api_14 api_15; do count=$(find Question_set/results/symptom_extraction_40000_plus/worker_$api/symptom_results -name "*.json" 2>/dev/null | wc -l); echo "$api: $count 个症状文件"; done'
```

### 4. 单独运行Worker

```bash
# 手动运行单个worker
python3 Question_set/symptom_worker.py \
    --input_dir dataset/ \
    --output_dir Question_set/results/ \
    --api_key_name api_1 \
    --start_index 40000 \
    --end_index 40100 \
    --prompt_type comprehensive
```

## 输出结果

### 目录结构

```
Question_set/results/symptom_extraction_40000_plus/
├── worker_api_1/
│   ├── symptom_results/           # JSON格式的症状提取结果
│   │   ├── report_40000_symptoms.json
│   │   └── ...
│   ├── symptom_summaries/         # 文本格式的症状摘要
│   │   ├── report_40000_symptoms.txt
│   │   └── ...
│   ├── processing_logs/           # 处理日志
│   │   ├── report_40000_processing.json
│   │   └── ...
│   └── worker_statistics.json     # Worker统计信息
├── worker_api_2/
│   └── ...
└── ...
```

### 结果格式

#### 症状提取结果 (JSON)

```json
[
    {
        "symptom_description": "胸部持续性钝痛3天，活动后加重",
        "original_text": "患者诉胸部疼痛3天，呈持续性钝痛，活动后加重",
        "symptom_type": "主观症状",
        "body_system": "循环系统",
        "severity": "中度",
        "context": "持续3天，活动相关性疼痛",
        "confidence_score": "高",
        "anatomical_location": "胸部",
        "clinical_significance": "可能提示心血管疾病",
        "test_suitable": true,
        "case_id": "report_40000",
        "extraction_timestamp": "2024-01-XX"
    }
]
```

#### Worker统计信息

```json
{
    "worker_name": "api_1",
    "total_reports": 327,
    "processed_reports": 327,
    "successful_reports": 320,
    "total_symptoms_extracted": 1845,
    "success_rate": 0.978,
    "avg_symptoms_per_report": 5.77,
    "completion_time": "2024-01-XX",
    "prompt_type": "comprehensive"
}
```

## 与原蒸馏系统的区别

| 特性 | Question_Distillation_v2 | Question_set |
|------|---------------------------|--------------|
| **主要目标** | 症状-器官对应关系判断 | 症状描述识别和生成 |
| **输出类型** | 器官特异性症状映射 | 标准化症状描述 |
| **使用场景** | 知识蒸馏和推理 | 测试集构建 |
| **提示词策略** | 器官导向的推理 | 症状导向的提取 |
| **处理范围** | 0-39999 | 40000+ |

## 配置说明

### API配置

系统使用 `configs/system_config.py` 中的 `MULTI_API_CONFIG` 配置：

- 支持15个DeepSeek API
- 自动负载均衡
- 错误重试机制

### 处理参数

- **最小分块大小**：200字符
- **最大分块大小**：4000字符
- **重试次数**：3次
- **重试延迟**：2秒

## 故障排除

### 常见问题

1. **导入错误**：确保项目根目录在Python路径中
2. **API错误**：检查API密钥和网络连接
3. **内存不足**：适当调整并发worker数量
4. **文件权限**：确保脚本有执行权限

### 日志查看

每个worker都会生成详细的处理日志：

```bash
# 查看特定worker的日志
tail -f Question_set/results/symptom_extraction_40000_plus/worker_api_1/processing_logs/report_40000_processing.json

# 查看worker统计
cat Question_set/results/symptom_extraction_40000_plus/worker_api_1/worker_statistics.json
```

## 开发和扩展

### 添加新的提示词类型

1. 在 `Question_set/prompts/symptom_prompts.py` 中添加新方法
2. 更新 `get_prompt_by_task()` 函数
3. 在命令行参数中添加新选项

### 自定义处理逻辑

1. 修改 `Question_set/processors/document_processor.py` 的分块逻辑
2. 调整 `Question_set/extractors/symptom_extractor.py` 的提取算法
3. 更新 `Question_set/symptom_worker.py` 的处理流程

## 性能指标

基于测试数据的预期性能：

- **处理速度**：约每秒1000-2000字符
- **症状提取率**：平均每报告5-8个症状
- **成功率**：>95%
- **总处理时间**：4915个文件预计6-12小时（取决于API响应速度）

---

*最后更新：2024年1月* 