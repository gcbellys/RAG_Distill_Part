#!/bin/bash
# -*- coding: utf-8 -*-
#
# 症状提取流程启动脚本 - 40000+范围
# 处理40000-44914条数据，使用15个API，构建测试集症状数据
# 结果保存到 Question_set/results/symptom_extraction_40000_plus
#

# --- 配置 ---
INPUT_DIR="dataset"
OUTPUT_DIR="Question_set/results/symptom_extraction_40000_plus"
APIS_TO_USE=("api_1" "api_2" "api_3" "api_4" "api_5" "api_6" "api_7" "api_8" "api_9" "api_10" "api_11" "api_12" "api_13" "api_14" "api_15")
VENV_PATH="conda activate rag_distill"
PROMPT_TYPE="comprehensive"
START_FILE_NUMBER=40000
END_FILE_NUMBER=44914
# ----------------

WORK_DIR="/opt/RAG_Evidence4Organ"
echo "设置工作目录为: $WORK_DIR"
cd "$WORK_DIR"

echo "🚀 启动症状提取流水线 - 40000+范围 (使用15个API构建测试集)..."

mkdir -p "$OUTPUT_DIR"
TASK_LIST_DIR=$(mktemp -d -t symptom_extract_tasks_XXXXXXXX)
echo "已创建输出目录: $OUTPUT_DIR"
echo "临时任务文件将存放在: $TASK_LIST_DIR"

echo "正在从 $INPUT_DIR 筛选文件，范围: $START_FILE_NUMBER - $END_FILE_NUMBER..."
ALL_FILES=()
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
echo "成功筛选出 $NUM_FILES 个文件进行症状提取处理。"

NUM_APIS=${#APIS_TO_USE[@]}
FILES_PER_API=$(( (NUM_FILES + NUM_APIS - 1) / NUM_APIS ))
echo "使用 $NUM_APIS 个API，每个API处理约 $FILES_PER_API 条数据"

# 分配任务给各个API
for i in "${!APIS_TO_USE[@]}"; do
    API_KEY_NAME=${APIS_TO_USE[$i]}
    TASK_FILE_PATH="$TASK_LIST_DIR/task_${API_KEY_NAME}.txt"

    start=$(( i * FILES_PER_API ))
    end=$(( start + FILES_PER_API ))
    if [ "$end" -gt "$NUM_FILES" ]; then
        end=$NUM_FILES
    fi

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
        actual_count=$((end - start))
        echo "API ${API_KEY_NAME}: 处理文件 ${start}-$((end-1)) (实际编号: ${first_file_num}-${last_file_num}, 共 ${actual_count} 个文件)"
    else
        echo "API ${API_KEY_NAME}: 无任务分配"
    fi
done
echo "已将任务分配给 $NUM_APIS 个API。"

# 启动各个Worker
echo ""
echo "🎯 开始启动症状提取Worker..."
for API_KEY_NAME in "${APIS_TO_USE[@]}"; do
    SESSION_NAME="symptom_extract_${API_KEY_NAME}"
    TASK_FILE_PATH="$TASK_LIST_DIR/task_${API_KEY_NAME}.txt"

    if [ ! -s "$TASK_FILE_PATH" ]; then
        echo "⏭️ API ${API_KEY_NAME} 没有待处理任务，已跳过。"
        continue
    fi

    echo "📡 正在启动 Worker: $SESSION_NAME, API: $API_KEY_NAME, 任务文件: $TASK_FILE_PATH"

    # 终止可能存在的同名会话
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null

    # 创建新的tmux会话
    tmux new-session -d -s "$SESSION_NAME"

    # 设置工作环境
    tmux send-keys -t "$SESSION_NAME" "cd $WORK_DIR" Enter
    tmux send-keys -t "$SESSION_NAME" "export PYTHONPATH=$WORK_DIR:\$PYTHONPATH" Enter
    tmux send-keys -t "$SESSION_NAME" "$VENV_PATH" Enter

    # 启动症状提取worker
    tmux send-keys -t "$SESSION_NAME" "python3 Question_set/symptom_worker.py --file_list $TASK_FILE_PATH --api_key_name $API_KEY_NAME --output_dir $OUTPUT_DIR --prompt_type $PROMPT_TYPE" Enter

    echo "✅ Worker $SESSION_NAME 已启动"
    sleep 2
done

echo ""
echo "🎉 所有症状提取Worker已启动！"
echo ""
echo "📊 监控命令:"
echo "  tmux list-sessions | grep symptom_extract"
echo "  tmux attach-session -t symptom_extract_api_1"
echo "  tmux attach-session -t symptom_extract_api_2"
echo "  ..."
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

    if [ "$start" -lt "$NUM_FILES" ]; then
        first_file_num=$(echo "${ALL_FILES[$start]}" | grep -o '[0-9]\+')
        if [ "$end" -le "$NUM_FILES" ]; then
            last_file_num=$(echo "${ALL_FILES[$((end-1))]}" | grep -o '[0-9]\+')
        else
            last_file_num=$(echo "${ALL_FILES[$((NUM_FILES-1))]}" | grep -o '[0-9]\+')
        fi
        actual_count=$((end - start))
        echo "  ${API_KEY_NAME}: 文件 ${first_file_num}-${last_file_num} (${actual_count}个) -> $OUTPUT_DIR/worker_${API_KEY_NAME}/"
    else
        echo "  ${API_KEY_NAME}: 无任务分配"
    fi
done
echo ""
echo "🔍 查看症状提取进度:"
echo "  watch -n 10 'ls -la $OUTPUT_DIR/worker_*/symptom_results/ | grep -c \"\.json\"'"
echo ""
echo "📈 实时监控各worker进度:"
echo "  watch -n 5 'echo \"=== 各Worker症状提取进度 ===\"; for api in api_1 api_2 api_3 api_4 api_5 api_6 api_7 api_8 api_9 api_10 api_11 api_12 api_13 api_14 api_15; do count=\$(find $OUTPUT_DIR/worker_\$api/symptom_results -name \"*.json\" 2>/dev/null | wc -l); echo \"\$api: \$count 个症状文件\"; done'"
echo ""
echo "📋 查看Worker统计信息:"
echo "  find $OUTPUT_DIR -name \"worker_statistics.json\" -exec echo \"=== {} ===\" \\; -exec cat {} \\; -exec echo \"\" \\;"
echo ""
echo "🧹 清理临时文件:"
echo "  rm -rf $TASK_LIST_DIR"
echo ""
echo "🎯 关于症状提取:"
echo "  - 目的: 构建测试集，识别症状描述"
echo "  - 范围: 40000-44914 (共 $NUM_FILES 个文件)"
echo "  - 输出: 每个报告生成症状JSON文件和处理日志"
echo "  - 不同于原蒸馏: 专注症状识别而非症状-器官对应关系" 