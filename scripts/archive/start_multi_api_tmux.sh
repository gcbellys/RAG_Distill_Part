#!/bin/bash
# -*- coding: utf-8 -*-
"""
多API并行处理tmux启动脚本
"""

# 设置工作目录
WORK_DIR="/home/cdj_lp/RAG-Graph/RAG_Evidence4Organ"
cd "$WORK_DIR"

echo "🚀 启动多API并行处理..."

# 创建输出目录
mkdir -p knowledge_distillation/results/output_0_500
mkdir -p knowledge_distillation/results/output_501_1000
mkdir -p knowledge_distillation/results/output_1001_1500
mkdir -p knowledge_distillation/results/output_1501_2000
mkdir -p knowledge_distillation/results/output_2001_2500

# 启动第一个tmux session (API 1: 0-500)
echo "📡 启动API 1 (DeepSeek Original) - 处理 0-500..."
tmux new-session -d -s api_1 -c "$WORK_DIR"
tmux send-keys -t api_1 "cd $WORK_DIR" Enter
tmux send-keys -t api_1 "source /home/cdj_lp/RAG-Graph/RAG_organ/bin/activate" Enter
tmux send-keys -t api_1 "python3 scripts/process_multi_api.py --api-config api_1" Enter

# 启动第二个tmux session (API 2: 501-1000)
echo "📡 启动API 2 (Tencent Cloud DeepSeek 1) - 处理 501-1000..."
tmux new-session -d -s api_2 -c "$WORK_DIR"
tmux send-keys -t api_2 "cd $WORK_DIR" Enter
tmux send-keys -t api_2 "source /home/cdj_lp/RAG-Graph/RAG_organ/bin/activate" Enter
tmux send-keys -t api_2 "python3 scripts/process_multi_api.py --api-config api_2" Enter

# 启动第三个tmux session (API 3: 1001-1500)
echo "📡 启动API 3 (Tencent Cloud DeepSeek 2) - 处理 1001-1500..."
tmux new-session -d -s api_3 -c "$WORK_DIR"
tmux send-keys -t api_3 "cd $WORK_DIR" Enter
tmux send-keys -t api_3 "source /home/cdj_lp/RAG-Graph/RAG_organ/bin/activate" Enter
tmux send-keys -t api_3 "python3 scripts/process_multi_api.py --api-config api_3" Enter

# 启动第四个tmux session (API 4: 1501-2000)
echo "📡 启动API 4 (DeepSeek Key2) - 处理 1501-2000..."
tmux new-session -d -s api_4 -c "$WORK_DIR"
tmux send-keys -t api_4 "cd $WORK_DIR" Enter
tmux send-keys -t api_4 "source /home/cdj_lp/RAG-Graph/RAG_organ/bin/activate" Enter
tmux send-keys -t api_4 "python3 scripts/process_multi_api.py --api-config api_4" Enter

# 启动第五个tmux session (API 5: 2001-2500)
echo "📡 启动API 5 (DeepSeek Key3) - 处理 2001-2500..."
tmux new-session -d -s api_5 -c "$WORK_DIR"
tmux send-keys -t api_5 "cd $WORK_DIR" Enter
tmux send-keys -t api_5 "source /home/cdj_lp/RAG-Graph/RAG_organ/bin/activate" Enter
tmux send-keys -t api_5 "python3 scripts/process_multi_api.py --api-config api_5" Enter

echo "✅ 所有tmux session已启动！"
echo ""
echo "📋 可用命令："
echo "  tmux list-sessions                    # 查看所有session"
echo "  tmux attach-session -t api_1          # 连接到API 1 session"
echo "  tmux attach-session -t api_2          # 连接到API 2 session"
echo "  tmux attach-session -t api_3          # 连接到API 3 session"
echo "  tmux attach-session -t api_4          # 连接到API 4 session"
echo "  tmux attach-session -t api_5          # 连接到API 5 session"
echo "  tmux kill-session -t api_1            # 停止API 1 session"
echo "  tmux kill-session -t api_2            # 停止API 2 session"
echo "  tmux kill-session -t api_3            # 停止API 3 session"
echo "  tmux kill-session -t api_4            # 停止API 4 session"
echo "  tmux kill-session -t api_5            # 停止API 5 session"
echo ""
echo "📁 输出目录："
echo "  knowledge_distillation/results/output_0_500/"
echo "  knowledge_distillation/results/output_501_1000/"
echo "  knowledge_distillation/results/output_1001_1500/"
echo "  knowledge_distillation/results/output_1501_2000/"
echo "  knowledge_distillation/results/output_2001_2500/"
echo ""
echo "🔍 监控进度："
echo "  watch -n 5 'ls -la knowledge_distillation/results/output_*/'" 