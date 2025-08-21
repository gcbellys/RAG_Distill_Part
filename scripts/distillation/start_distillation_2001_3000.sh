#!/bin/bash
# -*- coding: utf-8 -*-
#
# 蒸馏流程启动脚本 - 2001-3000范围
# 处理2001-3000条数据，使用5个API（api_11-15），每个API处理200条
# 结果保存到 test_2001_3000_apis_output
#

# --- 配置 ---
# 输入目录：包含所有.txt报告的文件夹
INPUT_DIR="dataset"
# 输出目录：存放各个worker产出的独立json文件
OUTPUT_DIR="test_2001_3000_apis_output"
# 使用的API key名称列表 (从system_config.py中获取)
APIS_TO_USE=("api_11" "api_12" "api_13" "api_14" "api_15")
# Python虚拟环境路径 (使用conda环境)
VENV_PATH="conda activate rag_distill"
# 提示词类型: universal(所有器官) 或 restricted(仅5个指定器官)
PROMPT_TYPE="universal"
# --- !!! 目标处理范围 !!! ---
# 设置要处理的文件编号范围
START_FILE_NUMBER=2001
END_FILE_NUMBER=3000
# 每个API处理的数量
FILES_PER_API=200
# ----------------

# 获取项目根目录，以便在任何地方运行此脚本
WORK_DIR="/opt/RAG_Evidence4Organ"
echo "设置工作目录为: $WORK_DIR"
cd "$WORK_DIR"

echo "🚀 启动蒸馏流水线 - 2001-3000范围 (使用api_11-15，每个API处理200条)..."

# 1. 创建输出目录和临时任务文件目录
mkdir -p "$OUTPUT_DIR"
TASK_LIST_DIR=$(mktemp -d -t distill_tasks_2001_3000_XXXXXXXX)
echo "已创建输出目录: $OUTPUT_DIR"
echo "临时任务文件将存放在: $TASK_LIST_DIR"

# 2. 筛选在范围内的文件（按数字顺序排序）
echo "正在从 $INPUT_DIR 筛选文件，范围: $START_FILE_NUMBER - $END_FILE_NUMBER..."
ALL_FILES=()
# 数字排序，保证顺序严格递增 (2001, 2002, 2003, ..., 3000)
for file in $(ls "$INPUT_DIR" | grep -E '^report_[0-9]+\.txt$' | sort -t_ -k2,2n); do
    if [[ $file =~ report_([0-9]+)\.txt ]]; then
        num=${BASH_REMATCH[1]}
        if [ "$num" -ge "$START_FILE_NUMBER" ] && [ "$num" -le "$END_FILE_NUMBER" ]; then
            ALL_FILES+=("$file")
        fi
    fi
done

# 验证筛选结果
echo "筛选结果验证:"
echo "  第一个文件: ${ALL_FILES[0]}"
echo "  最后一个文件: ${ALL_FILES[-1]}"
echo "  总文件数: ${#ALL_FILES[@]}"

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
    
    # 获取实际的文件编号范围
    if [ "$start" -lt "$NUM_FILES" ]; then
        first_file_num=$(echo "${ALL_FILES[$start]}" | grep -o '[0-9]\+')
        if [ "$end" -le "$NUM_FILES" ]; then
            last_file_num=$(echo "${ALL_FILES[$((end-1))]}" | grep -o '[0-9]\+')
        else
            last_file_num=$(echo "${ALL_FILES[$((NUM_FILES-1))]}" | grep -o '[0-9]\+')
        fi
        echo "API ${API_KEY_NAME}: 处理文件 ${start}-$((end-1)) (实际编号: ${first_file_num}-${last_file_num}, 共 $((end-start)) 个文件)"
    else
        echo "API ${API_KEY_NAME}: 无任务分配"
    fi
done
echo "已将任务分配给 $NUM_APIS 个API。"

# 4. 循环启动Tmux会话
for API_KEY_NAME in "${APIS_TO_USE[@]}"; do
    SESSION_NAME="distill_2001_3000_${API_KEY_NAME}"
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
echo "  tmux list-sessions | grep distill_2001_3000"
echo "  tmux attach-session -t distill_2001_3000_api_11"
echo "  tmux attach-session -t distill_2001_3000_api_12"
echo "  tmux attach-session -t distill_2001_3000_api_13"
echo "  tmux attach-session -t distill_2001_3000_api_14"
echo "  tmux attach-session -t distill_2001_3000_api_15"
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
    
    # 获取实际的文件编号范围
    if [ "$start" -lt "$NUM_FILES" ]; then
        first_file_num=$(echo "${ALL_FILES[$start]}" | grep -o '[0-9]\+')
        if [ "$end" -le "$NUM_FILES" ]; then
            last_file_num=$(echo "${ALL_FILES[$((end-1))]}" | grep -o '[0-9]\+')
        else
            last_file_num=$(echo "${ALL_FILES[$((NUM_FILES-1))]}" | grep -o '[0-9]\+')
        fi
        echo "  ${API_KEY_NAME}: 文件 ${first_file_num}-${last_file_num} -> $OUTPUT_DIR/worker_${API_KEY_NAME}/"
    else
        echo "  ${API_KEY_NAME}: 无任务分配"
    fi
done
echo ""
echo "🔍 查看进度:"
echo "  watch -n 10 'ls -la $OUTPUT_DIR/worker_*/ | grep -c \"\.json\"'"
echo ""
echo "📈 实时监控各worker进度:"
echo "  watch -n 5 'echo \"=== 各Worker进度 ===\"; for api in api_11 api_12 api_13 api_14 api_15; do count=\$(find $OUTPUT_DIR/worker_\$api/json_results -name \"*.json\" 2>/dev/null | wc -l); echo \"\$api: \$count 个文件\"; done'"
echo ""
echo "🧹 清理临时文件:"
echo "  rm -rf $TASK_LIST_DIR" 