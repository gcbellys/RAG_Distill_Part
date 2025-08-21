# 持续蒸馏系统使用说明

## 概述

持续蒸馏系统是一个基于API轮转池的自动化医学报告处理系统，能够从指定序号开始持续向后处理医学报告，直到收到停止信号。

## 系统特点

### 🔄 API轮转池机制
- 使用前12个API（api_1 到 api_12）作为处理池
- 智能检测API空闲状态，自动分配任务
- 支持并行处理，最大化资源利用率

### 📊 动态任务分配
- 从指定起始序号开始，自动向后查找可用文件
- 每个API一次只处理一个文件
- API空闲时立即分配下一个文件
- 使用全局变量记录当前处理序号
- 跳过不存在的文件，连续处理可用数据

### 🛑 优雅停止机制
- 支持运行时停止信号
- 等待当前任务完成后安全退出
- 记录最后处理的序号

### 📈 实时状态监控
- JSON格式的状态文件记录
- 实时监控面板显示进度
- 详细的API工作状态

## 使用方法

### 1. 启动持续蒸馏

```bash
# 从序号6001开始持续蒸馏
./scripts/distillation/continuous_distillation.sh 6001
```

### 2. 监控系统状态

```bash
# 实时监控（每10秒刷新）
./scripts/distillation/monitor_continuous.sh

# 单次查看状态
./scripts/distillation/monitor_continuous.sh --once
```

### 3. 停止系统

```bash
# 优雅停止（等待当前任务完成）
/tmp/stop_distillation.sh
```

### 4. 手动查看tmux会话

```bash
# 查看所有持续蒸馏会话
tmux list-sessions | grep continuous

# 连接到特定API会话查看详细日志
tmux attach-session -t continuous_api_1
```

## 配置说明

### 主要配置项（在脚本中修改）

```bash
# API轮转池 - 使用前12个API
API_POOL=("api_1" "api_2" "api_3" "api_4" "api_5" "api_6" "api_7" "api_8" "api_9" "api_10" "api_11" "api_12")

# 检查间隔（秒） - 检查空闲API的频率
CHECK_INTERVAL=5

# 输出目录
OUTPUT_DIR="/hy-tmp/output_continuous"
```

### 状态文件位置

- **状态文件**: `/tmp/continuous_distillation_status.json`
- **当前序号文件**: `/tmp/current_processing_number.txt`
- **停止标志**: `/tmp/stop_distillation.flag`
- **停止脚本**: `/tmp/stop_distillation.sh`

## 输出结构

```
/hy-tmp/output_continuous/
├── worker_api_1/
│   ├── json_results/
│   │   ├── report_6001_extracted.json
│   │   ├── report_6002_extracted.json
│   │   └── ...
│   ├── processing_logs/
│   └── thinking_chains/
├── worker_api_2/
│   └── ...
└── ...
```

## 状态文件格式

```json
{
  "start_time": "2025-08-07T20:00:00",
  "start_number": 6001,
  "current_number": 6543,
  "total_processed": 542,
  "apis_status": {},
  "last_update": "2025-08-07T21:30:15"
}
```

## 监控面板示例

```
================================
   持续蒸馏系统监控面板
================================

🚀 系统状态: 运行中
⏰ 运行时间: 1:30:15
🔄 最后更新: 0:00:05 ago

📊 处理进度
   起始序号: 6001
   当前序号: 6543
   已处理数: 542
   处理范围: 6001 - 6542

🔧 API轮转池状态
   ⚡ api_1: 工作中
   💤 api_2: 空闲
   ⚡ api_3: 工作中
   💤 api_4: 空闲
   ⚡ api_5: 工作中
   💤 api_6: 空闲
   ⚡ api_7: 工作中
   💤 api_8: 空闲
   ⚡ api_9: 工作中
   💤 api_10: 空闲
   ⚡ api_11: 工作中
   💤 api_12: 空闲

   活跃API: 6 | 空闲API: 6

📁 输出统计
   输出目录: /hy-tmp/output_continuous
   JSON文件: 542
   目录大小: 15M

🎮 控制命令
   停止系统: /tmp/stop_distillation.sh
   查看日志: tmux attach-session -t continuous_api_1
   退出监控: Ctrl+C
```

## 工作流程

1. **初始化阶段**
   - 创建状态文件和停止脚本
   - 初始化输出目录
   - 设置信号处理

2. **主循环阶段**
   - 检查停止信号
   - 扫描空闲API
   - 分配下一批任务
   - 更新状态信息

3. **任务处理阶段**
   - 创建临时任务文件
   - 启动tmux会话
   - 运行蒸馏worker
   - 监控任务完成状态

4. **停止阶段**
   - 等待所有任务完成
   - 清理临时文件
   - 记录最终状态

## 故障排除

### 常见问题

1. **API无响应**
   ```bash
   # 手动杀死卡住的会话
   tmux kill-session -t continuous_api_X
   ```

2. **状态文件损坏**
   ```bash
   # 删除状态文件重新启动
   rm /tmp/continuous_distillation_status.json
   ```

3. **磁盘空间不足**
   ```bash
   # 检查输出目录大小
   du -sh /hy-tmp/output_continuous
   ```

### 日志查看

```bash
# 查看特定API的处理日志
tmux attach-session -t continuous_api_1

# 查看系统级错误
journalctl -f | grep distillation
```

## 性能优化

### 建议配置

- **高性能服务器**: BATCH_SIZE=100, CHECK_INTERVAL=15
- **标准配置**: BATCH_SIZE=50, CHECK_INTERVAL=30  
- **资源受限**: BATCH_SIZE=25, CHECK_INTERVAL=60

### 监控要点

1. **CPU使用率**: 保持在80%以下
2. **内存使用**: 监控是否有内存泄漏
3. **网络带宽**: API调用频率
4. **磁盘I/O**: 输出文件写入速度

## 扩展功能

### 自定义API池

修改脚本中的 `API_POOL` 数组：

```bash
# 使用不同的API组合
API_POOL=("api_1" "api_3" "api_5" "api_7" "api_9" "api_11")
```

### 处理特定范围

可以修改 `find_next_batch` 函数来处理特定的序号范围。

### 集成云存储

可以在任务完成后自动上传到OSS：

```bash
# 在worker完成后添加上传逻辑
ossutil cp $OUTPUT_DIR oss://bucket/path -r --update
```

## 注意事项

1. **API配额**: 注意API调用限制和余额
2. **文件权限**: 确保输出目录有写权限
3. **网络稳定**: 保持网络连接稳定
4. **资源监控**: 定期检查系统资源使用情况

## 版本历史

- **v1.0**: 基础持续蒸馏功能
- **v1.1**: 添加监控面板和状态文件
- **v1.2**: 优化API空闲检测和任务分配 