#!/bin/bash
# -*- coding: utf-8 -*-
#
# 并行蒸馏流程启动脚本 (总指挥)
# 作者: Gemini & CDJ_LP
# 描述:
# 该脚本会自动筛选指定范围内的文件、分配任务，并使用tmux在后台为
# 多个API key启动并行的处理工作。
#

# --- 配置 ---
# 输入目录：包含所有.txt报告的文件夹
INPUT_DIR="RAG_Evidence4Organ/dataset"
# 输出目录：存放各个worker产出的独立json文件
OUTPUT_DIR="RAG_Evidence4Organ/result_new"
# 使用的API key名称列表 (从system_config.py中获取)
APIS_TO_USE=("api_1" "api_2" "api_3" "api_4" "api_5")
# Python虚拟环境路径
VENV_PATH="/home/cdj_lp/RAG-Graph/RAG_organ/bin/activate"
# 提示词类型: universal(所有器官) 或 restricted(仅5个指定器官)
PROMPT_TYPE="universal"
# --- !!! 目标处理范围 !!! ---
# 设置要处理的文件编号范围
START_FILE_NUMBER=10001
END_FILE_NUMBER=20000
# ----------------

# 获取项目根目录，以便在任何地方运行此脚本
WORK_DIR=$(pwd)
echo "设置工作目录为: $WORK_DIR"
cd "$WORK_DIR"

echo "🚀 启动并行蒸馏流水线..."

# 1. 创建输出目录和临时任务文件目录
mkdir -p "$OUTPUT_DIR"
TASK_LIST_DIR=$(mktemp -d -t distill_tasks_XXXXXXXX)
echo "已创建输出目录: $OUTPUT_DIR"
echo "临时任务文件将存放在: $TASK_LIST_DIR"

# 2. 筛选在范围内的文件
echo "正在从 $INPUT_DIR 筛选文件，范围: $START_FILE_NUMBER - $END_FILE_NUMBER..."
ALL_FILES=()
while IFS= read -r file; do
    if [[ $file =~ report_([0-9]+)\.txt ]]; then
        num=${BASH_REMATCH[1]}
        if [ "$num" -ge "$START_FILE_NUMBER" ] && [ "$num" -le "$END_FILE_NUMBER" ]; then
            ALL_FILES+=("$file")
        fi
    fi
done < <(ls "$INPUT_DIR")

NUM_FILES=${#ALL_FILES[@]}
if [ "$NUM_FILES" -eq 0 ]; then
    echo "错误：在指定范围内未找到任何报告文件。请检查INPUT_DIR和范围设置。"
    exit 1
fi
echo "成功筛选出 $NUM_FILES 个文件进行处理。"

# 3. 将任务分配到临时文件
NUM_APIS=${#APIS_TO_USE[@]}
CHUNK_SIZE=$(( (NUM_FILES + NUM_APIS - 1) / NUM_APIS )) # 向上取整

for i in "${!APIS_TO_USE[@]}"; do
    API_KEY_NAME=${APIS_TO_USE[$i]}
    TASK_FILE_PATH="$TASK_LIST_DIR/task_${API_KEY_NAME}.txt"
    
    start=$(( i * CHUNK_SIZE ))
    end=$(( start + CHUNK_SIZE ))
    if [ "$end" -gt "$NUM_FILES" ]; then
        end=$NUM_FILES
    fi
    
    # 清空旧文件并写入新任务
    > "$TASK_FILE_PATH"
    for ((j=start; j<end; j++)); do
        echo "$INPUT_DIR/${ALL_FILES[$j]}" >> "$TASK_FILE_PATH"
    done
done
echo "已将任务平均分配给 $NUM_APIS 个API。"


# 4. 循环启动Tmux会话
for API_KEY_NAME in "${APIS_TO_USE[@]}"; do
    SESSION_NAME="distill_worker_${API_KEY_NAME}"
    TASK_FILE_PATH="$TASK_LIST_DIR/task_${API_KEY_NAME}.txt"
    
    if [ ! -s "$TASK_FILE_PATH" ]; then
        echo "⏭️ API ${API_KEY_NAME} 没有待处理任务，已跳过。"
        continue
    fi

    echo "📡 正在启动 Worker: $SESSION_NAME, API: $API_KEY_NAME, 任务文件: $TASK_FILE_PATH"
    
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null
    tmux new-session -d -s "$SESSION_NAME"
    
    tmux send-keys -t "$SESSION_NAME" "source $VENV_PATH" Enter
    tmux send-keys -t "$SESSION_NAME" "cd $WORK_DIR" Enter
    
    CMD="python RAG_Evidence4Organ/knowledge_distillation/process_worker.py \\
        --output_dir \"$OUTPUT_DIR\" \\
        --api_key_name \"$API_KEY_NAME\" \\
        --file_list \"$TASK_FILE_PATH\" \\
        --prompt_type \"$PROMPT_TYPE\""
    tmux send-keys -t "$SESSION_NAME" "$CMD" Enter
done

echo ""
echo "✅ 所有并行处理任务已在后台启动！"
echo ""
echo " cleanup() {
  echo '正在清理临时任务文件...'
  rm -rf '$TASK_LIST_DIR'
  echo '清理完毕。'
}
trap cleanup EXIT"
echo "📋 可用命令进行监控："
echo "  tmux list-sessions"
echo "  tmux attach-session -t distill_worker_api_1"
echo "  watch -n 5 'ls -lh \"$OUTPUT_DIR\"/worker_*/ | wc -l' # 实时查看各worker产出的文件总数"
echo ""
echo "🛑 如何停止所有任务:"
echo "  for session in \$(tmux list-sessions -F '#S' | grep 'distill_worker'); do tmux kill-session -t \"\$session\"; done"
echo "  # 或者直接: tmux kill-server" 