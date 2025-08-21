#!/bin/bash
# -*- coding: utf-8 -*-
#
# 监控0805版本蒸馏进度脚本
#

OUTPUT_DIR="/hy-tmp/output_final_0805"
APIS_TO_USE=("api_1" "api_2" "api_3" "api_4" "api_5" "api_6" "api_7" "api_8" "api_9" "api_10")

echo "📊 0805版本蒸馏进度监控"
echo "================================"

# 检查输出目录是否存在
if [ ! -d "$OUTPUT_DIR" ]; then
    echo "❌ 输出目录不存在: $OUTPUT_DIR"
    echo "请先运行: ./scripts/distillation/start_final_0805_distillation.sh"
    exit 1
fi

# 检查tmux会话状态
echo "🔍 Tmux会话状态:"
tmux list-sessions | grep distill_final_0805 || echo "  没有找到运行中的会话"

echo ""
echo "📁 各API处理进度:"
echo "API名称           | 文件数量 | 完成数量 | 进度"
echo "------------------|----------|----------|------"

total_files=0
total_completed=0

for API_KEY_NAME in "${APIS_TO_USE[@]}"; do
    worker_dir="$OUTPUT_DIR/worker_${API_KEY_NAME}"
    
    if [ -d "$worker_dir" ]; then
        # 计算该API应该处理的文件数量
        api_index=${API_KEY_NAME#api_}
        start_file=$(( (api_index - 1) * 300 ))
        end_file=$(( start_file + 299 ))
        expected_files=300
        
        # 计算实际完成的文件数量
        completed_files=$(find "$worker_dir" -name "*.json" | wc -l)
        
        # 计算进度百分比
        if [ "$expected_files" -gt 0 ]; then
            progress=$(( completed_files * 100 / expected_files ))
        else
            progress=0
        fi
        
        printf "%-16s | %8d | %8d | %3d%%\n" "$API_KEY_NAME" "$expected_files" "$completed_files" "$progress"
        
        total_files=$(( total_files + expected_files ))
        total_completed=$(( total_completed + completed_files ))
    else
        printf "%-16s | %8d | %8d | %3d%%\n" "$API_KEY_NAME" "300" "0" "0"
        total_files=$(( total_files + 300 ))
    fi
done

echo "------------------|----------|----------|------"
if [ "$total_files" -gt 0 ]; then
    total_progress=$(( total_completed * 100 / total_files ))
    printf "%-16s | %8d | %8d | %3d%%\n" "总计" "$total_files" "$total_completed" "$total_progress"
else
    printf "%-16s | %8d | %8d | %3d%%\n" "总计" "0" "0" "0"
fi

echo ""
echo "📈 详细统计:"

# 统计各API的详细情况
for API_KEY_NAME in "${APIS_TO_USE[@]}"; do
    worker_dir="$OUTPUT_DIR/worker_${API_KEY_NAME}"
    
    if [ -d "$worker_dir" ]; then
        echo ""
        echo "🔍 $API_KEY_NAME 详情:"
        echo "  目录: $worker_dir"
        
        # 列出最新的几个文件
        latest_files=$(find "$worker_dir" -name "*.json" -printf "%T@ %p\n" | sort -nr | head -5 | cut -d' ' -f2-)
        if [ -n "$latest_files" ]; then
            echo "  最新处理的文件:"
            echo "$latest_files" | while read file; do
                basename_file=$(basename "$file")
                echo "    $basename_file"
            done
        fi
        
        # 检查是否有错误日志
        if [ -f "$worker_dir/error.log" ]; then
            echo "  ⚠️  发现错误日志: $worker_dir/error.log"
        fi
    fi
done

echo ""
echo "🎯 操作建议:"
echo "  查看特定API进度: tmux attach-session -t distill_final_0805_api_1"
echo "  聚合结果: python3 scripts/distillation/aggregate_final_0805.py"
echo "  实时监控: watch -n 30 './scripts/distillation/monitor_final_0805.sh'" 