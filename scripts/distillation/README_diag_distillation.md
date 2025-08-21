# Diag_Distillation 持续蒸馏系统

## 概述

这是一个针对Diag_Distillation的三步诊断提取持续蒸馏系统，使用api_1到api_16进行轮转处理。

## 系统特点

- 🔄 **API轮转池**: 使用api_1到api_16共16个API
- ⚡ **并行处理**: 每个API一次处理一个文件，空闲时立即分配下一个
- 🔬 **三步诊断**: 症状提取 → 器官提取 → 解剖映射
- 📊 **实时监控**: 提供实时状态监控和进度跟踪
- 🛑 **优雅停止**: 支持优雅停止，等待当前任务完成

## 文件结构

```
scripts/distillation/
├── continuous_diag_distillation.sh    # 持续蒸馏主脚本
├── monitor_diag_continuous.sh         # 监控脚本
└── README_diag_distillation.md        # 使用说明
```

## 使用方法

### 1. 启动持续蒸馏

```bash
# 从序号10001开始持续蒸馏
./scripts/distillation/continuous_diag_distillation.sh 10001

# 从其他序号开始
./scripts/distillation/continuous_diag_distillation.sh 20001
```

### 2. 监控系统状态

```bash
# 持续监控（每10秒刷新）
./scripts/distillation/monitor_diag_continuous.sh

# 只显示一次状态
./scripts/distillation/monitor_diag_continuous.sh --once

# 显示帮助信息
./scripts/distillation/monitor_diag_continuous.sh --help
```

### 3. 停止系统

```bash
# 创建停止信号
/tmp/stop_diag_distillation.sh

# 或者直接删除停止标志文件
rm /tmp/stop_diag_distillation.flag
```

## 配置说明

### 主要配置项

- **INPUT_DIR**: 输入目录（默认：dataset）
- **OUTPUT_DIR**: 输出目录（默认：/hy-tmp/output_diag_continuous）
- **API_POOL**: API轮转池（api_1到api_16）
- **CHECK_INTERVAL**: 检查间隔（默认：5秒）

### 状态文件

- **状态文件**: `/tmp/continuous_diag_distillation_status.json`
- **当前序号**: `/tmp/current_diag_processing_number.txt`
- **停止标志**: `/tmp/stop_diag_distillation.flag`

## 输出结构

```
/hy-tmp/output_diag_continuous/
├── diagnostic_results/                    # 原始诊断结果
│   ├── diagnostic_10001.json
│   ├── diagnostic_10002.json
│   └── ...
├── diagnostic_results_normalized/         # 标准化结果
│   ├── diagnostic_10001.json
│   ├── diagnostic_10002.json
│   └── ...
└── logs/                                  # 处理日志
    ├── diagnostic_10001.log
    ├── diagnostic_10002.log
    └── ...
```

## 监控面板

监控面板显示以下信息：

1. **系统状态**: 运行时间、最后更新
2. **处理进度**: 起始序号、当前序号、已完成数
3. **API状态**: 16个API的实时状态（工作中/空闲/未启动）
4. **输出统计**: 文件数量、目录大小
5. **最近结果**: 最近处理的5个文件

## 故障排除

### 常见问题

1. **API配置错误**
   - 检查`configs/system_config.py`中的API配置
   - 确认api_1到api_16都已正确配置

2. **权限问题**
   - 确保脚本有执行权限：`chmod +x scripts/distillation/*.sh`
   - 确保有写入输出目录的权限

3. **tmux会话问题**
   - 检查tmux是否安装：`which tmux`
   - 清理旧会话：`tmux kill-server`

4. **文件不存在**
   - 确认输入目录中有`report_*.txt`文件
   - 检查文件命名格式是否正确

### 日志查看

```bash
# 查看特定API的日志
tmux attach-session -t continuous_diag_api_1

# 查看系统日志
tail -f /tmp/continuous_diag_distillation_status.json
```

## 性能优化

1. **API轮转**: 16个API并行处理，最大化吞吐量
2. **文件检查**: 智能查找下一个存在的文件
3. **状态更新**: 实时更新处理状态和进度
4. **资源清理**: 自动清理临时文件和会话

## 注意事项

1. **数据备份**: 建议定期备份输出结果
2. **磁盘空间**: 监控输出目录的磁盘使用情况
3. **网络稳定**: 确保API调用的网络连接稳定
4. **系统资源**: 监控CPU和内存使用情况

## 技术支持

如有问题，请检查：
1. 系统日志和错误信息
2. API配置和网络连接
3. 文件权限和磁盘空间
4. tmux会话状态 