#!/bin/bash
# -*- coding: utf-8 -*-
#
# 持续蒸馏系统监控脚本
# 实时显示系统状态和进度
#

STATUS_FILE="/tmp/continuous_distillation_status.json"
OUTPUT_DIR="/hy-tmp/output_continuous"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 清屏函数
clear_screen() {
    clear
    echo -e "${CYAN}================================${NC}"
    echo -e "${CYAN}   持续蒸馏系统监控面板${NC}"
    echo -e "${CYAN}================================${NC}"
    echo
}

# 显示状态信息
show_status() {
    if [ ! -f "$STATUS_FILE" ]; then
        echo -e "${RED}❌ 状态文件不存在，系统可能未启动${NC}"
        echo "   状态文件路径: $STATUS_FILE"
        return
    fi
    
    # 读取当前序号
    local current_number=""
    if [ -f "/tmp/current_processing_number.txt" ]; then
        current_number=$(cat "/tmp/current_processing_number.txt" 2>/dev/null)
    fi
    
    # 读取状态
    local status=$(cat "$STATUS_FILE" 2>/dev/null)
    if [ -z "$status" ]; then
        echo -e "${RED}❌ 无法读取状态文件${NC}"
        return
    fi
    
    # 使用Python解析JSON
    local info=$(python3 -c "
import json
import sys
from datetime import datetime

try:
    status = json.loads('$status')
    
    start_time = datetime.fromisoformat(status['start_time'].replace('Z', '+00:00'))
    last_update = datetime.fromisoformat(status['last_update'].replace('Z', '+00:00'))
    current_time = datetime.now()
    
    running_time = current_time - start_time
    last_update_ago = current_time - last_update
    
    print(f\"START_NUMBER:{status['start_number']}\")
    print(f\"TOTAL_PROCESSED:{status['total_processed']}\")
    print(f\"RUNNING_TIME:{str(running_time).split('.')[0]}\")
    print(f\"LAST_UPDATE:{str(last_update_ago).split('.')[0]} ago\")
    
except Exception as e:
    print(f\"ERROR:{e}\", file=sys.stderr)
    sys.exit(1)
" 2>/dev/null)
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ 状态信息解析失败${NC}"
        return
    fi
    
    # 解析结果
    local start_number=$(echo "$info" | grep "START_NUMBER:" | cut -d: -f2)
    local total_processed=$(echo "$info" | grep "TOTAL_PROCESSED:" | cut -d: -f2)
    local running_time=$(echo "$info" | grep "RUNNING_TIME:" | cut -d: -f2)
    local last_update=$(echo "$info" | grep "LAST_UPDATE:" | cut -d: -f2-)
    
    # 显示系统状态
    echo -e "${GREEN}🚀 系统状态: 运行中${NC}"
    echo -e "${BLUE}⏰ 运行时间:${NC} $running_time"
    echo -e "${BLUE}🔄 最后更新:${NC} $last_update"
    echo
    
    # 显示进度信息
    echo -e "${YELLOW}📊 处理进度${NC}"
    echo -e "   起始序号: $start_number"
    if [ -n "$current_number" ]; then
        echo -e "   当前序号: $current_number"
        echo -e "   处理范围: $start_number - $current_number"
    else
        echo -e "   当前序号: 未知"
    fi
    echo -e "   已完成数: $total_processed"
    echo -e "   处理模式: 每个API处理一个文件"
    echo
}

# 显示API状态
show_api_status() {
    echo -e "${YELLOW}🔧 API轮转池状态${NC}"
    
    local api_pool=("api_1" "api_2" "api_3" "api_4" "api_5" "api_6" "api_7" "api_8" "api_9" "api_10" "api_11" "api_12")
    local active_count=0
    local idle_count=0
    
    for api in "${api_pool[@]}"; do
        local session_name="continuous_${api}"
        local status_icon
        local status_text
        
        if tmux has-session -t "$session_name" 2>/dev/null; then
            # 检查是否在运行
            local pane_content=$(tmux capture-pane -t "$session_name" -p 2>/dev/null | tail -3)
            if echo "$pane_content" | grep -q "root@.*#\s*$"; then
                status_icon="💤"
                status_text="空闲"
                idle_count=$((idle_count + 1))
            else
                status_icon="⚡"
                status_text="工作中"
                active_count=$((active_count + 1))
            fi
        else
            status_icon="😴"
            status_text="未启动"
            idle_count=$((idle_count + 1))
        fi
        
        echo -e "   $status_icon $api: $status_text"
    done
    
    echo
    echo -e "   ${GREEN}活跃API: $active_count${NC} | ${BLUE}空闲API: $idle_count${NC}"
    echo
}

# 显示输出统计
show_output_stats() {
    echo -e "${YELLOW}📁 输出统计${NC}"
    
    if [ -d "$OUTPUT_DIR" ]; then
        local total_files=$(find "$OUTPUT_DIR" -name "*.json" 2>/dev/null | wc -l)
        local total_size=$(du -sh "$OUTPUT_DIR" 2>/dev/null | cut -f1)
        
        echo -e "   输出目录: $OUTPUT_DIR"
        echo -e "   JSON文件: $total_files"
        echo -e "   目录大小: $total_size"
    else
        echo -e "   输出目录不存在: $OUTPUT_DIR"
    fi
    echo
}

# 显示控制命令
show_controls() {
    echo -e "${CYAN}🎮 控制命令${NC}"
    echo -e "   停止系统: ${GREEN}/tmp/stop_distillation.sh${NC}"
    echo -e "   查看日志: ${GREEN}tmux attach-session -t continuous_api_1${NC}"
    echo -e "   退出监控: ${GREEN}Ctrl+C${NC}"
    echo
}

# 主函数
main() {
    local refresh_interval=10
    
    if [ "$1" == "--once" ]; then
        clear_screen
        show_status
        show_api_status
        show_output_stats
        show_controls
        exit 0
    fi
    
    echo "🔍 启动持续蒸馏系统监控 (每${refresh_interval}秒刷新)"
    echo "按 Ctrl+C 退出监控"
    sleep 2
    
    while true; do
        clear_screen
        show_status
        show_api_status
        show_output_stats
        show_controls
        
        echo -e "${CYAN}================================${NC}"
        echo -e "下次刷新: ${refresh_interval}秒后"
        
        sleep $refresh_interval
    done
}

# 检查参数
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --once    只显示一次状态，不持续监控"
    echo "  --help    显示此帮助信息"
    echo ""
    echo "默认行为: 持续监控，每10秒刷新一次"
    exit 0
fi

# 运行主函数
main "$@" 