#!/bin/bash
# -*- coding: utf-8 -*-
#
# 缺失数据蒸馏流程启动脚本
# 处理指定的6个缺失序号(13, 779, 2675, 2928, 3099, 5413)以及5856-6000范围
# 结果保存到 /hy-tmp/output_missing_data
#

# --- 配置 ---
# 输入目录：包含所有.txt报告的文件夹
INPUT_DIR="dataset"
# 输出目录：存放各个worker产出的独立json文件
OUTPUT_DIR="/hy-tmp/output_missing_data"
# 使用的API key名称列表 (从system_config.py中获取)
APIS_TO_USE=("api_1" "api_2" "api_3" "api_4" "api_5" "api_6" "api_7" "api_8" "api_9" "api_10" "api_11" "api_12" "api_13" "api_14" "api_15")
# Python虚拟环境路径 (使用conda环境)
VENV_PATH="conda activate rag_distill"
# 提示词类型: universal(所有器官) 或 restricted(仅5个指定器官)
PROMPT_TYPE="universal"
# ----------------

# 获取项目根目录，以便在任何地方运行此脚本
WORK_DIR="/opt/RAG_Evidence4Organ"
echo "设置工作目录为: $WORK_DIR"
cd "$WORK_DIR"

echo "🚀 启动缺失数据蒸馏流水线 (6个缺失序号 + 5856-6000范围，使用15个API)..."

# 1. 定义需要处理的序号
# 缺失的6个序号
MISSING_NUMBERS=(13 779 2675 2928 3099 5413)
# 5856-6000范围
for i in {5856..6000}; do
    MISSING_NUMBERS+=($i)
done

NUM_MISSING=${#MISSING_NUMBERS[@]}
echo "📋 需要处理的总序号数: $NUM_MISSING"
echo "🔍 包括:"
echo "   • 6个缺失序号: 13, 779, 2675, 2928, 3099, 5413"
echo "   • 5856-6000范围: $((6000-5856+1)) 个序号"

# 2. 创建输出目录和临时任务文件目录
mkdir -p "$OUTPUT_DIR"
TASK_LIST_DIR=$(mktemp -d -t distill_missing_tasks_XXXXXXXX)
echo "已创建输出目录: $OUTPUT_DIR"
echo "临时任务文件将存放在: $TASK_LIST_DIR"

# 3. 检查对应的文件是否存在
echo "正在检查序号对应的文件..."
MISSING_FILES=()
EXISTING_FILES=0
MISSING_FILES_COUNT=0

for num in "${MISSING_NUMBERS[@]}"; do
    file_path="$INPUT_DIR/report_${num}.txt"
    if [ -f "$file_path" ]; then
        MISSING_FILES+=("report_${num}.txt")
        EXISTING_FILES=$((EXISTING_FILES + 1))
    else
        echo "⚠️  警告: 文件不存在 $file_path"
        MISSING_FILES_COUNT=$((MISSING_FILES_COUNT + 1))
    fi
done

NUM_FILES=${#MISSING_FILES[@]}
echo "✅ 成功找到 $NUM_FILES 个文件 (缺失 $MISSING_FILES_COUNT 个文件)"

if [ "$NUM_FILES" -eq 0 ]; then
    echo "❌ 错误：未找到任何序号对应的文件。"
    exit 1
fi

# 4. 将任务分配到临时文件
NUM_APIS=${#APIS_TO_USE[@]}
FILES_PER_API=$(( (NUM_FILES + NUM_APIS - 1) / NUM_APIS )) # 向上取整
echo "使用 $NUM_APIS 个API，每个API处理约 $FILES_PER_API 条数据"

for i in "${!APIS_TO_USE[@]}"; do
    API_KEY_NAME=${APIS_TO_USE[$i]}
    TASK_FILE_PATH="$TASK_LIST_DIR/task_${API_KEY_NAME}.txt"
    
    start=$(( i * FILES_PER_API ))
    end=$(( start + FILES_PER_API ))
    if [ "$end" -gt "$NUM_FILES" ]; then
        end=$NUM_FILES
    fi
    
    # 清空旧文件并写入新任务
    > "$TASK_FILE_PATH"
    for ((j=start; j<end; j++)); do
        echo "$INPUT_DIR/${MISSING_FILES[$j]}" >> "$TASK_FILE_PATH"
    done
    
    actual_count=$((end - start))
    echo "API ${API_KEY_NAME}: 处理文件 ${start}-$((end-1)) (共 $actual_count 个文件)"
done
echo "已将任务分配给 $NUM_APIS 个API。"

# 6. 循环启动Tmux会话
for API_KEY_NAME in "${APIS_TO_USE[@]}"; do
    SESSION_NAME="distill_missing_${API_KEY_NAME}"
    TASK_FILE_PATH="$TASK_LIST_DIR/task_${API_KEY_NAME}.txt"
    
    if [ ! -s "$TASK_FILE_PATH" ]; then
        echo "⏭️ API ${API_KEY_NAME} 没有待处理任务，已跳过。"
        continue
    fi

    echo "📡 正在启动 Worker: $SESSION_NAME, API: $API_KEY_NAME, 任务文件: $TASK_FILE_PATH"
    
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null
    tmux new-session -d -s "$SESSION_NAME"
    
    tmux send-keys -t "$SESSION_NAME" "cd $WORK_DIR" Enter
    tmux send-keys -t "$SESSION_NAME" "export PYTHONPATH=$WORK_DIR:\$PYTHONPATH" Enter
    tmux send-keys -t "$SESSION_NAME" "$VENV_PATH" Enter
    
    # 启动处理worker
    tmux send-keys -t "$SESSION_NAME" "python3 -m Question_Distillation_v2.process_worker --file_list $TASK_FILE_PATH --api_key_name $API_KEY_NAME --output_dir $OUTPUT_DIR --prompt_type $PROMPT_TYPE" Enter
    
    echo "✅ Worker $SESSION_NAME 已启动"
    sleep 2  # 避免同时启动太多进程
done

echo ""
echo "🎉 所有Worker已启动！"
echo "📊 监控命令:"
echo "  tmux list-sessions | grep distill_missing"
echo "  tmux attach-session -t distill_missing_api_1"
echo ""
echo "📁 结果将保存在: $OUTPUT_DIR"
echo "📋 任务分配情况:"
for i in "${!APIS_TO_USE[@]}"; do
    API_KEY_NAME=${APIS_TO_USE[$i]}
    start=$(( i * FILES_PER_API ))
    end=$(( start + FILES_PER_API ))
    if [ "$end" -gt "$NUM_FILES" ]; then
        end=$NUM_FILES
    fi
    actual_count=$((end - start))
    echo "  ${API_KEY_NAME}: $actual_count 个文件 -> $OUTPUT_DIR/worker_${API_KEY_NAME}/"
done
echo ""
echo "🔍 查看进度:"
echo "  watch -n 10 'ls -la $OUTPUT_DIR/worker_*/ | grep -c \"\.json\"'"
echo ""
echo "📈 实时监控各worker进度:"
echo "  watch -n 5 'echo \"=== 各Worker进度 ===\"; for api in api_1 api_2 api_3 api_4 api_5 api_6 api_7 api_8 api_9 api_10 api_11 api_12 api_13 api_14 api_15; do count=\$(find $OUTPUT_DIR/worker_\$api/json_results -name \"*.json\" 2>/dev/null | wc -l); echo \"\$api: \$count 个文件\"; done'"
echo ""
echo "🎯 处理范围总结:"
echo "  • 6个缺失序号: 13, 779, 2675, 2928, 3099, 5413"
echo "  • 5856-6000范围: $((6000-5856+1)) 个序号"
echo "  • 总计: $NUM_MISSING 个序号，$NUM_FILES 个文件"
echo ""
echo "🧹 清理临时文件:"
echo "  rm -rf $TASK_LIST_DIR" 