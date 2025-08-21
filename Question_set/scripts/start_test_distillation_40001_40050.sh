#!/bin/bash
# -*- coding: utf-8 -*-
#
# 测试集蒸馏流程启动脚本 - 40001-40050范围
# 使用api_16进行症状提取，构建测试集
# 结果保存到 Question_set/results/test_distillation_40001_40050
#

# --- 配置 ---
INPUT_DIR="dataset"
OUTPUT_DIR="Question_set/results/test_distillation_40001_40050"
API_TO_USE="api_16"
VENV_PATH="conda activate rag_distill"
PROMPT_TYPE="comprehensive"
START_FILE_NUMBER=40001
END_FILE_NUMBER=40050
# ----------------

WORK_DIR="/opt/RAG_Evidence4Organ"
echo "设置工作目录为: $WORK_DIR"
cd "$WORK_DIR"

# 检查输入目录
if [ ! -d "$INPUT_DIR" ]; then
    echo "❌ 错误: 输入目录不存在 - $INPUT_DIR"
    exit 1
fi

# 创建输出目录
mkdir -p "$OUTPUT_DIR"
echo "✅ 创建输出目录: $OUTPUT_DIR"

# 检查API配置
if ! grep -q "$API_TO_USE" configs/system_config.py; then
    echo "❌ 错误: API配置不存在 - $API_TO_USE"
    exit 1
fi

echo "🔍 开始筛选文件范围: $START_FILE_NUMBER - $END_FILE_NUMBER"

# 筛选指定范围的文件
REPORT_FILES=()
for i in $(seq $START_FILE_NUMBER $END_FILE_NUMBER); do
    REPORT_FILE="$INPUT_DIR/report_$i.txt"
    if [ -f "$REPORT_FILE" ]; then
        REPORT_FILES+=("$REPORT_FILE")
    else
        echo "⚠️  警告: 文件不存在 - $REPORT_FILE"
    fi
done

TOTAL_FILES=${#REPORT_FILES[@]}
echo "📊 找到 $TOTAL_FILES 个文件需要处理"

if [ $TOTAL_FILES -eq 0 ]; then
    echo "❌ 错误: 没有找到需要处理的文件"
    exit 1
fi

# 创建任务分配文件
TASK_FILE="$OUTPUT_DIR/task_list.txt"
rm -f "$TASK_FILE"
for file in "${REPORT_FILES[@]}"; do
    echo "$file" >> "$TASK_FILE"
done

echo "📋 任务列表已保存到: $TASK_FILE"

# 创建worker输出目录
WORKER_OUTPUT_DIR="$OUTPUT_DIR/worker_$API_TO_USE"
mkdir -p "$WORKER_OUTPUT_DIR"
mkdir -p "$WORKER_OUTPUT_DIR/json_results"
mkdir -p "$WORKER_OUTPUT_DIR/processing_logs"
mkdir -p "$WORKER_OUTPUT_DIR/thinking_chains"

echo "📁 创建worker输出目录: $WORKER_OUTPUT_DIR"

# 启动单个worker处理所有文件
echo "🚀 启动症状提取worker..."
echo "   使用API: $API_TO_USE"
echo "   处理文件数: $TOTAL_FILES"
echo "   输出目录: $WORKER_OUTPUT_DIR"

# 创建tmux会话
SESSION_NAME="test_distill_40001_40050"
tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true

tmux new-session -d -s "$SESSION_NAME" -c "$WORK_DIR" << EOF
$VENV_PATH
PYTHONPATH=$WORK_DIR python3 Question_set/symptom_worker.py \\
    --api_key_name $API_TO_USE \\
    --file_list $TASK_FILE \\
    --output_dir $OUTPUT_DIR \\
    --prompt_type $PROMPT_TYPE \\
    --log_level INFO
EOF

echo "✅ Worker已启动在tmux会话: $SESSION_NAME"
echo ""
echo "📊 监控命令:"
echo "  tmux list-sessions | grep $SESSION_NAME"
echo "  tmux attach-session -t $SESSION_NAME"
echo "  tmux kill-session -t $SESSION_NAME  # 停止处理"
echo ""
echo "📁 结果将保存在: $WORKER_OUTPUT_DIR"
echo "   • json_results/ - 提取的症状JSON文件"
echo "   • processing_logs/ - 处理日志"
echo "   • thinking_chains/ - 思考链记录"
echo ""
echo "🎯 处理范围: $START_FILE_NUMBER - $END_FILE_NUMBER"
echo "🔧 使用API: $API_TO_USE"
echo "📝 提示词类型: $PROMPT_TYPE"
echo ""
echo "⏳ 开始处理... (按 Ctrl+C 停止)"
echo "============================================================"

# 等待用户确认
read -p "按回车键继续，或按 Ctrl+C 取消..."

# 显示会话状态
echo "📋 当前tmux会话状态:"
tmux list-sessions | grep "$SESSION_NAME" || echo "会话未找到"

echo ""
echo "🎉 测试集蒸馏任务已启动!"
echo "💡 提示: 使用 'tmux attach-session -t $SESSION_NAME' 查看实时进度" 