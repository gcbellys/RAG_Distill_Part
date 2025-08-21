#!/bin/bash
# -*- coding: utf-8 -*-
#
# 智能续传流程启动脚本
# 作者: Gemini & CDJ_LP
# 描述:
# 该脚本用于启动断点续传任务。它首先调用Python脚本生成
# 精确的待办任务清单，然后为每个清单启动一个并行的处理worker。
#

# --- 配置 ---
# 原始数据目录
INPUT_DIR="RAG_Evidence4Organ/dataset"
# 结果保存目录 (父目录)
RESULTS_DIR="RAG_Evidence4Organ/result_new"
# 存放生成的任务清单的临时目录
TASK_LIST_DIR="RAG_Evidence4Organ/scripts/task_lists"
# 原始目标处理总数
TOTAL_TO_PROCESS=10000
# 使用的API key名称列表 (确保与system_config.py一致)
APIS_TO_USE=("api_1" "api_4" "api_5" "api_6" "api_7")
# Python虚拟环境路径
VENV_PATH="/home/cdj_lp/RAG-Graph/RAG_organ/bin/activate"
# ----------------

WORK_DIR=$(pwd)
echo "设置工作目录为: $WORK_DIR"
cd "$WORK_DIR"

echo "🚀 启动智能断点续传流水线..."

# --- 第1步: 生成任务清单 ---
echo "ขั้นตอนที่ 1: กำลังสร้างรายการงานที่ค้างอยู่..."
# 清理旧的任务清单
rm -rf "$TASK_LIST_DIR"
mkdir -p "$TASK_LIST_DIR"

# 将API列表转换为字符串参数
API_ARGS="${APIS_TO_USE[@]}"

# 调用Python脚本生成任务
python RAG_Evidence4Organ/scripts/generate_resume_tasks.py \
    --input_dir "$INPUT_DIR" \
    --results_dir "$RESULTS_DIR" \
    --task_output_dir "$TASK_LIST_DIR" \
    --total_to_process "$TOTAL_TO_PROCESS" \
    --api_keys $API_ARGS

# 检查任务清单是否为空，如果所有任务都已完成，则脚本可以提前退出
if [ -z "$(ls -A $TASK_LIST_DIR)" ]; then
    echo "✅ 所有任务清单为空，说明所有报告都已处理完毕。脚本退出。"
    exit 0
fi

echo "✅ 任务清单生成完毕。"

# --- 第2步: 启动并行处理Workers ---
echo "ขั้นตอนที่ 2: กำลังเริ่มตัวประมวลผลแบบขนานสำหรับงานที่เหลือ..."

for API_KEY_NAME in "${APIS_TO_USE[@]}"; do
    TASK_FILE="${TASK_LIST_DIR}/task_${API_KEY_NAME}.txt"
    
    # 如果某个API的任务清单不存在或为空，则跳过
    if [ ! -s "$TASK_FILE" ]; then
        echo "⏭️ API ${API_KEY_NAME} 没有待处理任务，已跳过。"
        continue
    fi

    SESSION_NAME="resume_worker_${API_KEY_NAME}"
    
    echo "📡 正在启动 Worker: $SESSION_NAME, API: $API_KEY_NAME, 任务文件: $TASK_FILE"
    
    # 杀掉可能存在的同名旧session
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null
    
    # 创建新的后台session
    tmux new-session -d -s "$SESSION_NAME"
    
    # 发送命令
    tmux send-keys -t "$SESSION_NAME" "source $VENV_PATH" Enter
    tmux send-keys -t "$SESSION_NAME" "cd $WORK_DIR" Enter
    CMD="python RAG_Evidence4Organ/knowledge_distillation/process_worker.py \\
        --output_dir \"$RESULTS_DIR\" \\
        --api_key_name \"$API_KEY_NAME\" \\
        --file_list \"$TASK_FILE\""
    tmux send-keys -t "$SESSION_NAME" "$CMD" Enter
done

echo ""
echo "✅ 所有断点续传任务已在后台启动！"
echo ""
echo "📋 可用命令进行监控："
echo "  tmux list-sessions"
echo "  tmux attach-session -t resume_worker_api_1"
echo ""
echo "🛑 如何停止所有任务:"
echo "  tmux kill-server" 