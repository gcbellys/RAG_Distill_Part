#!/bin/bash
# -*- coding: utf-8 -*-
#
# 启动0805版本后5个API蒸馏脚本
# 处理1000-1999的文件，每个API处理200条
#

# --- 配置 ---
INPUT_DIR="dataset"
OUTPUT_DIR="/output_final_0805"
APIS_TO_USE=("api_6" "api_7" "api_8" "api_9" "api_10")
VENV_PATH="conda activate rag_distill"
PROMPT_TYPE="universal"
# 处理范围：1000-1999
START_FILE_NUMBER=1000
END_FILE_NUMBER=1999
FILES_PER_API=200
# ----------------

WORK_DIR="/opt/RAG_Evidence4Organ"
echo "设置工作目录为: $WORK_DIR"
cd "$WORK_DIR"

echo "🚀 启动0805版本后5个API蒸馏 (1000-1999范围，每个API处理200条)..."

# 1. 创建输出目录和临时任务文件目录
mkdir -p "$OUTPUT_DIR"
TASK_LIST_DIR=$(mktemp -d -t distill_tasks_api6_10_XXXXXXXX)
echo "已创建输出目录: $OUTPUT_DIR"
echo "临时任务文件将存放在: $TASK_LIST_DIR"

# 2. 筛选在范围内的文件（按数字顺序排序）
echo "正在从 $INPUT_DIR 筛选文件，范围: $START_FILE_NUMBER - $END_FILE_NUMBER..."
ALL_FILES=()
# 数字排序，保证顺序严格递增 (1000, 1001, 1002, ..., 1999)
for file in $(ls "$INPUT_DIR" | grep -E '^report_[0-9]+\.txt$' | sort -t_ -k2,2n); do
    if [[ $file =~ report_([0-9]+)\.txt ]]; then
        num=${BASH_REMATCH[1]}
        if [ "$num" -ge "$START_FILE_NUMBER" ] && [ "$num" -le "$END_FILE_NUMBER" ]; then
            ALL_FILES+=("$file")
        fi
    fi
done

NUM_FILES=${#ALL_FILES[@]}
if [ "$NUM_FILES" -eq 0 ]; then
    echo "错误：在指定范围内未找到任何报告文件。请检查INPUT_DIR和范围设置。"
    exit 1
fi
echo "成功筛选出 $NUM_FILES 个文件进行处理。"

# 3. 将任务分配到临时文件（每个API处理200条）
NUM_APIS=${#APIS_TO_USE[@]}
echo "使用 $NUM_APIS 个API，每个API处理 $FILES_PER_API 条数据"

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
        echo "$INPUT_DIR/${ALL_FILES[$j]}" >> "$TASK_FILE_PATH"
    done
    
    echo "API ${API_KEY_NAME}: 处理文件 ${start}-$((end-1)) (共 $((end-start)) 个文件)"
done
echo "已将任务分配给 $NUM_APIS 个API。"

# 4. 循环启动Tmux会话
for API_KEY_NAME in "${APIS_TO_USE[@]}"; do
    SESSION_NAME="distill_final_0805_${API_KEY_NAME}"
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
echo "🎉 后5个API Worker已启动！"
echo "📊 监控命令:"
echo "  tmux list-sessions | grep distill_final_0805"
echo "  tmux attach-session -t distill_final_0805_api_6"
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
    echo "  ${API_KEY_NAME}: 文件 ${start}-$((end-1)) -> $OUTPUT_DIR/worker_${API_KEY_NAME}/"
done
echo ""
echo "🔍 查看进度:"
echo "  watch -n 10 'ls -la $OUTPUT_DIR/worker_*/ | grep -c \"\.json\"'"
echo ""
echo "📈 聚合结果:"
echo "  python3 scripts/distillation/aggregate_final_0805.py" 