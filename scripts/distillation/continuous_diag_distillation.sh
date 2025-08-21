#!/bin/bash
# -*- coding: utf-8 -*-
#
# Diag_Distillation 持续蒸馏系统 - API轮转池
# 使用api_1到api_16作为轮转池，从指定序号开始持续向后蒸馏
#
# --- V3 - 最终稳定版 ---
# 1. 修复了竞态条件：在主循环中加入了延时，防止因循环过快导致所有任务被分配给单个API。
# 2. 修复了文件计数：精确统计目标目录中的文件，避免了计数错误。
# 3. 增强了日志：提供了更清晰的系统状态反馈。
#

# --- 配置 ---
INPUT_DIR="dataset"
OUTPUT_DIR="/hy-tmp/output_diag_continuous"
API_POOL=("api_1" "api_2" "api_3" "api_4" "api_5" "api_6" "api_7" "api_8" "api_9" "api_10" "api_11" "api_12" "api_13" "api_14" "api_15" "api_16")
VENV_PATH="conda activate rag_distill"
STATUS_FILE="/tmp/continuous_diag_distillation_status.json"
STOP_FLAG_FILE="/tmp/stop_diag_distillation.flag"
CURRENT_NUMBER_FILE="/tmp/current_diag_processing_number.txt"
PID_DIR="/tmp/diag_pids"
# 主循环延时（秒），这是防止竞态条件的关键
LOOP_DELAY=1
# ----------------

WORK_DIR="/opt/RAG_Evidence4Organ"
cd "$WORK_DIR" || exit 1

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"; }

# ... (其他辅助函数保持不变) ...
init_current_number() { local start_number=$1; echo "$start_number" > "$CURRENT_NUMBER_FILE"; log_info "当前处理序号初始化为: $start_number"; }
get_current_number() { if [ -f "$CURRENT_NUMBER_FILE" ]; then cat "$CURRENT_NUMBER_FILE"; else echo "0"; fi; }
get_next_number() {
    local current; current=$(get_current_number)
    local next=$((current + 1))
    while [ $next -lt $((current + 2000)) ]; do
        if [ -f "$INPUT_DIR/report_${next}.txt" ] || [ -f "$INPUT_DIR/report_${next}.json" ]; then
            echo "$next" > "$CURRENT_NUMBER_FILE"
            echo "$next"
            return 0
        fi
        next=$((next + 1))
    done
    return 1
}
init_status() { local start_number=$1; cat > "$STATUS_FILE" << EOF
{ "start_time": "$(date -Iseconds)", "start_number": $start_number, "current_number": $start_number, "total_processed": 0, "apis_status": {}, "last_update": "$(date -Iseconds)" }
EOF
log_info "状态文件初始化完成: $STATUS_FILE"; }
update_status() { local current_number; current_number=$(get_current_number); local total_processed=$1; if [ -f "$STATUS_FILE" ]; then python3 -c "import json, sys, datetime; d=json.load(open('$STATUS_FILE')); d['current_number']=$current_number; d['total_processed']=$total_processed; d['last_update']=datetime.datetime.now().isoformat(); json.dump(d, open('$STATUS_FILE', 'w'), indent=2)"; fi; }

is_api_idle() {
    local api_name=$1
    local pid_file="${PID_DIR}/${api_name}.pid"
    if [ ! -f "$pid_file" ]; then return 0; fi
    local pid; pid=$(cat "$pid_file")
    if ps -p "$pid" > /dev/null; then
        return 1
    else
        log_warning "API $api_name 的任务(PID: $pid)已结束。清理PID文件。"
        rm -f "$pid_file"
        return 0
    fi
}

start_api_task() {
    local api_name=$1
    local file_number=$2
    local session_name="continuous_diag_${api_name}"
    local pid_file="${PID_DIR}/${api_name}.pid"
    local log_file="${OUTPUT_DIR}/logs/${api_name}_report_${file_number}.log"

    log_info "🚀 $api_name 开始处理: report_${file_number} | 日志: ${log_file}"
    
    tmux kill-session -t "$session_name" 2>/dev/null
    tmux new-session -d -s "$session_name"
    
    local cmd="cd $WORK_DIR && export PYTHONPATH=$WORK_DIR:\$PYTHONPATH && $VENV_PATH && python3 Diag_Distillation/process_worker.py --input_dir $INPUT_DIR --output_dir $OUTPUT_DIR --api_key_name $api_name --start_index $file_number --end_index $file_number > ${log_file} 2>&1 & echo \$! > $pid_file"
    tmux send-keys -t "$session_name" "$cmd" Enter
}
check_stop_signal() { if [ -f "$STOP_FLAG_FILE" ]; then return 0; fi; return 1; }
create_stop_command() { cat > "/tmp/stop_diag_distillation.sh" << 'EOF'
#!/bin/bash
echo "创建停止信号..." && touch /tmp/stop_diag_distillation.flag && echo "停止信号已创建。"
EOF
chmod +x "/tmp/stop_diag_distillation.sh"; log_info "停止命令已创建: /tmp/stop_diag_distillation.sh"; }

cleanup() {
    log_info "正在清理资源..."
    for api in "${API_POOL[@]}"; do
        tmux kill-session -t "continuous_diag_${api}" 2>/dev/null
    done
    rm -f "$STOP_FLAG_FILE"
    rm -rf "$PID_DIR"
    local final_number; final_number=$(get_current_number)
    log_success "✅ 最后处理的序号: $final_number"
    log_success "清理完成"
}
show_help() { echo "用法: $0 <起始序号> [输出目录]"; }

# --- **修复** ---
# 精确统计最终输出目录中的文件
count_processed_files() {
    find "$OUTPUT_DIR/diagnostic_results" -name "diagnostic_*.json" 2>/dev/null | wc -l
}

main() {
    if [ $# -lt 1 ] || [ $# -gt 2 ]; then show_help; exit 1; fi
    local start_number=$1
    if ! [[ "$start_number" =~ ^[0-9]+$ ]]; then log_error "起始序号必须是数字"; exit 1; fi

    # 可选输出目录参数
    if [ $# -eq 2 ]; then
        OUTPUT_DIR="$2"
        log_info "使用自定义输出目录: $OUTPUT_DIR"
    else
        log_info "使用默认输出目录: $OUTPUT_DIR"
    fi
    
    log_info "🚀 启动Diag_Distillation持续蒸馏系统 (V3 - 最终稳定版)"
    log_info "📋 API轮转池: ${#API_POOL[@]}个API"
    
    mkdir -p "$OUTPUT_DIR/diagnostic_results"
    mkdir -p "$OUTPUT_DIR/logs"
    mkdir -p "$PID_DIR"
    
    init_current_number "$start_number"
    init_status "$start_number"
    create_stop_command
    
    trap cleanup EXIT INT TERM
    
    log_success "✅ 系统已启动。日志将保存在 $OUTPUT_DIR/logs/"
    
    while true; do
        if check_stop_signal; then
            log_warning "收到停止信号，等待当前任务完成..."; break;
        fi
        
        local idle_api_found=false
        for api in "${API_POOL[@]}"; do
            if is_api_idle "$api"; then
                local next_number; next_number=$(get_next_number)
                if [ $? -eq 0 ]; then
                    start_api_task "$api" "$next_number"
                    idle_api_found=true
                    
                    local total_processed; total_processed=$(count_processed_files)
                    update_status "$total_processed"
                    log_success "📈 当前序号: $next_number, 已完成: $total_processed 个文件"
                else
                    log_warning "未找到更多文件，等待中..."; break 2;
                fi
            fi
        done

        if ! $idle_api_found; then
            log_info "所有API均在忙碌中，等待 ${LOOP_DELAY} 秒..."
        fi
        
        # --- **修复** ---
        # 在每次主循环后加入延时，防止竞态条件
        sleep "$LOOP_DELAY"
    done
    
    log_info "等待所有任务完成..."
    while true; do
        all_idle=true
        for api in "${API_POOL[@]}"; do
            if ! is_api_idle "$api"; then all_idle=false; break; fi
        done
        if $all_idle; then break; fi
        sleep 5
    done
    
    log_success "🎉 Diag_Distillation持续蒸馏系统已停止"
}

main "$@"