#!/bin/bash
# -*- coding: utf-8 -*-
#
# Question_set持续蒸馏系统 - API轮转池
# 使用api_13到api_16作为轮转池，进行症状提取任务
# 每个API一次处理一个文件，空闲时立即分配下一个文件
#

# --- 配置 ---
# 输入目录：包含所有.txt报告的文件夹
INPUT_DIR="dataset"
# 输出目录：存放各个worker产出的独立json文件
OUTPUT_DIR="/hy-tmp/output_questionset"
# API轮转池 - 使用api_13到api_16
API_POOL=("api_13" "api_14" "api_15" "api_16")
# Python虚拟环境路径
VENV_PATH="conda activate rag_distill"
# 提示词类型
PROMPT_TYPE="comprehensive"
# 状态文件
STATUS_FILE="/tmp/questionset_distillation_status.json"
STOP_FLAG_FILE="/tmp/stop_questionset.flag"
CURRENT_NUMBER_FILE="/tmp/current_questionset_number.txt"
# 检查间隔（秒）
CHECK_INTERVAL=5
# ----------------

# 获取项目根目录
WORK_DIR="/opt/RAG_Evidence4Organ"
echo "设置工作目录为: $WORK_DIR"
cd "$WORK_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

# 初始化当前序号
init_current_number() {
    local start_number=$1
    echo "$start_number" > "$CURRENT_NUMBER_FILE"
    log_info "当前处理序号初始化为: $start_number"
}

# 获取当前序号
get_current_number() {
    if [ -f "$CURRENT_NUMBER_FILE" ]; then
        cat "$CURRENT_NUMBER_FILE"
    else
        echo "0"
    fi
}

# 获取并递增序号（原子操作）
get_next_number() {
    local current=$(get_current_number)
    local next=$((current + 1))
    
    # 查找下一个存在的文件
    while [ $next -lt $((current + 1000)) ]; do
        if [ -f "$INPUT_DIR/report_${next}.txt" ]; then
            echo "$next" > "$CURRENT_NUMBER_FILE"
            echo "$next"
            return 0
        fi
        next=$((next + 1))
    done
    
    # 没找到文件
    return 1
}

# 初始化状态文件
init_status() {
    local start_number=$1
    cat > "$STATUS_FILE" << EOF
{
  "system": "Question_set",
  "start_time": "$(date -Iseconds)",
  "start_number": $start_number,
  "current_number": $start_number,
  "total_processed": 0,
  "apis_status": {},
  "last_update": "$(date -Iseconds)"
}
EOF
    log_info "状态文件初始化完成: $STATUS_FILE"
}

# 更新状态文件
update_status() {
    local current_number=$(get_current_number)
    local total_processed=$1
    
    if [ -f "$STATUS_FILE" ]; then
        python3 -c "
import json
import sys
from datetime import datetime

try:
    with open('$STATUS_FILE', 'r') as f:
        status = json.load(f)
    
    status['current_number'] = $current_number
    status['total_processed'] = $total_processed
    status['last_update'] = datetime.now().isoformat()
    
    with open('$STATUS_FILE', 'w') as f:
        json.dump(status, f, indent=2)
        
except Exception as e:
    print(f'Error updating status: {e}', file=sys.stderr)
    sys.exit(1)
"
    fi
}

# 检查API是否空闲
is_api_idle() {
    local api_name=$1
    local session_name="questionset_${api_name}"
    
    # 检查tmux会话是否存在
    if ! tmux has-session -t "$session_name" 2>/dev/null; then
        return 0  # 会话不存在，API空闲
    fi
    
    # 检查会话中是否有Python进程在运行
    local pane_content=$(tmux capture-pane -t "$session_name" -p 2>/dev/null | tail -5)
    
    # 如果看到shell提示符，说明任务完成
    if echo "$pane_content" | grep -q "root@.*#\s*$"; then
        return 0  # API空闲
    fi
    
    return 1  # API忙碌
}

# 获取下一个空闲的API
get_idle_api() {
    for api in "${API_POOL[@]}"; do
        if is_api_idle "$api"; then
            echo "$api"
            return 0
        fi
    done
    return 1  # 没有空闲API
}

# 启动API处理单个文件
start_api_task() {
    local api_name=$1
    local file_number=$2
    local session_name="questionset_${api_name}"
    local file_path="$INPUT_DIR/report_${file_number}.txt"
    
    log_info "🧠 $api_name 开始症状提取: report_${file_number}.txt"
    
    # 杀死旧会话
    tmux kill-session -t "$session_name" 2>/dev/null
    
    # 创建新会话
    tmux new-session -d -s "$session_name"
    tmux send-keys -t "$session_name" "cd $WORK_DIR" Enter
    tmux send-keys -t "$session_name" "export PYTHONPATH=$WORK_DIR:\$PYTHONPATH" Enter
    tmux send-keys -t "$session_name" "$VENV_PATH" Enter
    
    # 创建临时任务文件（只包含一个文件）
    local task_file="/tmp/questionset_task_${api_name}_${file_number}.txt"
    echo "$file_path" > "$task_file"
    
    # 创建该API的输出目录
    local api_output_dir="$OUTPUT_DIR/worker_${api_name}"
    mkdir -p "$api_output_dir"
    
    # 启动Question_set症状提取worker
    tmux send-keys -t "$session_name" "python3 Question_set/symptom_worker.py --api_key_name $api_name --file_list $task_file --output_dir $api_output_dir --prompt_type $PROMPT_TYPE" Enter
}

# 检查停止信号
check_stop_signal() {
    if [ -f "$STOP_FLAG_FILE" ]; then
        return 0  # 收到停止信号
    fi
    return 1
}

# 创建停止函数
create_stop_command() {
    cat > "/tmp/stop_questionset.sh" << 'EOF'
#!/bin/bash
echo "创建Question_set系统停止信号..."
touch /tmp/stop_questionset.flag
echo "停止信号已创建。Question_set蒸馏系统将在当前任务完成后停止。"
echo "最后处理的序号将保存在: /tmp/current_questionset_number.txt"
EOF
    chmod +x "/tmp/stop_questionset.sh"
    log_info "停止命令已创建: /tmp/stop_questionset.sh"
}

# 清理函数
cleanup() {
    log_info "正在清理Question_set系统资源..."
    
    # 杀死所有相关的tmux会话
    for api in "${API_POOL[@]}"; do
        local session_name="questionset_${api}"
        tmux kill-session -t "$session_name" 2>/dev/null
    done
    
    # 清理临时文件
    rm -f /tmp/questionset_task_*.txt
    rm -f "$STOP_FLAG_FILE"
    
    local final_number=$(get_current_number)
    log_success "✅ 最后处理的序号: $final_number"
    log_success "Question_set系统清理完成"
}

# 显示帮助信息
show_help() {
    echo "用法: $0 <起始序号>"
    echo ""
    echo "Question_set症状提取系统 - 使用api_13到api_16"
    echo ""
    echo "示例:"
    echo "  $0 6001    # 从序号6001开始持续症状提取"
    echo ""
    echo "说明:"
    echo "  • 每个API一次处理一个文件"
    echo "  • API空闲时立即分配下一个文件"
    echo "  • 专门用于构建测试集的症状提取"
    echo "  • 输出全英文格式"
    echo ""
    echo "停止系统:"
    echo "  /tmp/stop_questionset.sh"
    echo ""
    echo "查看当前序号:"
    echo "  cat /tmp/current_questionset_number.txt"
    echo ""
    echo "监控API状态:"
    echo "  tmux list-sessions | grep questionset"
}

# 统计处理完成的文件数
count_processed_files() {
    find "$OUTPUT_DIR" -name "*.json" 2>/dev/null | wc -l
}

# 主函数
main() {
    if [ $# -ne 1 ]; then
        show_help
        exit 1
    fi
    
    local start_number=$1
    
    # 验证起始序号
    if ! [[ "$start_number" =~ ^[0-9]+$ ]]; then
        log_error "起始序号必须是数字"
        exit 1
    fi
    
    log_info "🧠 启动Question_set持续蒸馏系统"
    log_info "📋 API轮转池: ${API_POOL[*]}"
    log_info "📊 起始序号: $start_number"
    log_info "📁 输出目录: $OUTPUT_DIR"
    log_info "⚡ 处理模式: 每个API一次处理一个文件进行症状提取"
    log_info "🎯 任务类型: 症状识别和描述生成（测试集构建）"
    
    # 创建输出目录
    mkdir -p "$OUTPUT_DIR"
    
    # 初始化状态
    init_current_number $start_number
    init_status $start_number
    create_stop_command
    
    # 设置清理陷阱
    trap cleanup EXIT INT TERM
    
    log_success "✅ Question_set持续蒸馏系统已启动"
    log_info "🛑 停止命令: /tmp/stop_questionset.sh"
    log_info "📊 状态文件: $STATUS_FILE"
    log_info "🔢 当前序号文件: $CURRENT_NUMBER_FILE"
    
    # 主循环
    while true; do
        # 检查停止信号
        if check_stop_signal; then
            log_warning "收到停止信号，等待当前任务完成..."
            break
        fi
        
        # 获取空闲API
        idle_api=$(get_idle_api)
        if [ $? -eq 0 ]; then
            # 获取下一个要处理的文件序号
            next_number=$(get_next_number)
            if [ $? -eq 0 ]; then
                # 启动任务
                start_api_task "$idle_api" "$next_number"
                
                # 更新状态
                local total_processed=$(count_processed_files)
                update_status $total_processed
                
                log_success "📈 当前序号: $next_number, 已完成: $total_processed 个症状提取"
            else
                log_warning "未找到更多文件，等待中..."
                sleep $CHECK_INTERVAL
            fi
        else
            # 没有空闲API，等待
            sleep $CHECK_INTERVAL
        fi
    done
    
    # 等待所有任务完成
    log_info "等待所有症状提取任务完成..."
    while true; do
        all_idle=true
        for api in "${API_POOL[@]}"; do
            if ! is_api_idle "$api"; then
                all_idle=false
                break
            fi
        done
        
        if $all_idle; then
            break
        fi
        
        sleep 5
    done
    
    # 最终统计
    local final_number=$(get_current_number)
    local total_processed=$(count_processed_files)
    update_status $total_processed
    
    log_success "🎉 Question_set持续蒸馏系统已停止"
    log_success "📊 最终统计: 处理了 $total_processed 个文件"
    log_success "📍 最后处理序号: $final_number"
    log_success "🧠 症状提取任务完成"
}

# 运行主函数
main "$@" 