#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
并行批量处理医学报告脚本
使用多个API密钥并行处理指定范围的报告
"""

import os
import sys
import json
import time
import traceback
import threading
from datetime import datetime
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue

# 添加项目根目录到Python路径
project_root = "/opt/RAG_Evidence4Organ"
sys.path.insert(0, project_root)

from Question_Distillation_v2.extractors.llm_extractor import LLMExtractor
from Diag_Distillation.prompts.medical_prompts import DiagnosticExtractionPrompts
from Diag_Distillation.process_worker import process_report_with_diagnostic_steps
from configs.system_config import MULTI_API_CONFIG

class ParallelBatchReportProcessor:
    def __init__(self, api_keys: List[str] = None):
        if api_keys is None:
            api_keys = ["api_13", "api_14", "api_15", "api_16", "api_12"]
        
        self.api_keys = api_keys
        self.setup_apis()
        self.setup_output_dir()
        self.prompts = DiagnosticExtractionPrompts()
        
        # 线程安全的结果存储
        self.results_lock = threading.Lock()
        self.processing_results = {}
        
    def setup_apis(self):
        """初始化所有API"""
        self.extractors = {}
        for api_key in self.api_keys:
            try:
                if api_key not in MULTI_API_CONFIG:
                    print(f"❌ API密钥 {api_key} 不存在于配置中")
                    continue
                    
                api_config = MULTI_API_CONFIG[api_key]
                extractor = LLMExtractor(
                    model=api_config["model"],
                    api_key=api_config["api_key"],
                    base_url=api_config["base_url"]
                )
                
                self.extractors[api_key] = extractor
                print(f"✅ API初始化成功: {api_key} - {api_config['model']}")
                
            except Exception as e:
                print(f"❌ API {api_key} 初始化失败: {e}")
        
        if not self.extractors:
            raise Exception("没有可用的API")
            
        print(f"🔗 成功初始化 {len(self.extractors)} 个API")
        
    def setup_output_dir(self):
        """设置输出目录"""
        self.output_dir = "/opt/RAG_Evidence4Organ/Diag_Distillation/output_test"
        
        # 清理旧的输出目录
        if os.path.exists(self.output_dir):
            import shutil
            shutil.rmtree(self.output_dir)
            print(f"🗑️ 清理旧的输出目录: {self.output_dir}")
        
        # 创建新的输出目录结构
        os.makedirs(f"{self.output_dir}/raw", exist_ok=True)
        os.makedirs(f"{self.output_dir}/normalized", exist_ok=True)
        os.makedirs(f"{self.output_dir}/logs", exist_ok=True)
        print(f"📁 创建输出目录结构: {self.output_dir}")
        
    def load_report(self, report_num: int) -> str:
        """加载报告数据"""
        dataset_dir = "/opt/RAG_Evidence4Organ/dataset"
        
        # 尝试加载txt文件
        txt_file = os.path.join(dataset_dir, f"report_{report_num}.txt")
        if os.path.exists(txt_file):
            with open(txt_file, 'r', encoding='utf-8') as f:
                return f.read()
        
        # 尝试加载json文件
        json_file = os.path.join(dataset_dir, f"report_{report_num}.json")
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('text', '') or data.get('medical_record_content', '')
        
        raise FileNotFoundError(f"报告 {report_num} 不存在 (txt或json)")
    
    def process_single_report(self, report_num: int, api_key: str) -> Dict[str, Any]:
        """处理单个报告"""
        
        def log(message: str):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_message = f"[{timestamp}] [INFO] {message}"
            print(f"[{api_key}] {log_message}")
            return log_message
        
        try:
            start_time = time.time()
            log(f"开始处理报告: report_{report_num}")
            
            # 加载报告
            report_text = self.load_report(report_num)
            log(f"报告加载成功: {len(report_text)} 字符")
            
            # 准备报告数据
            report_data = {
                'text': report_text,
                'case_id': str(report_num),
                'filename': f'report_{report_num}.txt'
            }
            
            log("开始诊断蒸馏处理...")
            
            # 处理报告
            extractor = self.extractors[api_key]
            result = process_report_with_diagnostic_steps(
                extractor, report_data, report_num, self.prompts, api_key
            )
            
            if not result:
                raise Exception("处理失败：无返回结果")
            
            processing_time = time.time() - start_time
            
            # 安全获取数据
            normalized = result.get("normalized", [])
            raw = result.get("raw", {})
            
            log(f"处理成功完成 (耗时: {processing_time:.1f}秒)")
            
            # 安全检查: 确保normalized是列表类型
            if isinstance(normalized, list):
                log(f"标准化结果: {len(normalized)} 个条目")
                
                if normalized:
                    total_units = sum(len(item.get('U_unit_set', [])) for item in normalized if isinstance(item, dict))
                    unique_organs = set()
                    for item in normalized:
                        if isinstance(item, dict):
                            for unit_wrapper in item.get('U_unit_set', []):
                                if isinstance(unit_wrapper, dict):
                                    u_unit = unit_wrapper.get('u_unit', {})
                                    if isinstance(u_unit, dict):
                                        organ_name = u_unit.get('o_organ', {}).get('organName')
                                        if organ_name:
                                            unique_organs.add(organ_name)
                    
                    log(f"诊断单元总数: {total_units}")
                    log(f"涉及器官数: {len(unique_organs)}")
                    if unique_organs:
                        log(f"涉及器官: {', '.join(sorted(unique_organs))}")
            else:
                log(f"警告: 标准化结果类型异常: {type(normalized)}")
                log(f"标准化结果内容: {normalized}")
            
            # 保存结果文件
            self.save_results(report_num, result, api_key)
            
            return {
                "success": True,
                "report_num": report_num,
                "api_key": api_key,
                "processing_time": processing_time,
                "total_units": sum(len(item.get('U_unit_set', [])) for item in normalized if isinstance(item, dict) and isinstance(normalized, list)),
                "unique_organs": list(unique_organs) if isinstance(normalized, list) else [],
                "log_messages": []
            }
            
        except Exception as e:
            error_msg = f"处理过程出错: {str(e)}"
            log(f"ERROR] {error_msg}")
            log(f"ERROR] 错误详情: {traceback.format_exc()}")
            
            # 保存错误信息
            error_result = {
                "success": False,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }
            self.save_results(report_num, {"raw": error_result, "normalized": []}, api_key)
            
            return {
                "success": False,
                "report_num": report_num,
                "api_key": api_key,
                "error": error_msg,
                "log_messages": []
            }
    
    def save_results(self, report_num: int, result: Dict[str, Any], api_key: str):
        """保存处理结果"""
        try:
            # 保存原始结果
            raw_file = f"{self.output_dir}/raw/report_{report_num}_raw.json"
            with open(raw_file, 'w', encoding='utf-8') as f:
                json.dump(result.get("raw", {}), f, ensure_ascii=False, indent=2)
            
            # 保存标准化结果
            normalized_file = f"{self.output_dir}/normalized/report_{report_num}_normalized.json"
            with open(normalized_file, 'w', encoding='utf-8') as f:
                json.dump(result.get("normalized", []), f, ensure_ascii=False, indent=2)
            
            # 创建简单的日志文件
            log_file = f"{self.output_dir}/logs/report_{report_num}_log.txt"
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"Report: {report_num}\n")
                f.write(f"API: {api_key}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                if result.get("raw", {}).get("success", True):
                    f.write("Status: Success\n")
                else:
                    f.write("Status: Failed\n")
                    f.write(f"Error: {result.get('raw', {}).get('error', 'Unknown')}\n")
            
            print(f"[{api_key}] 💾 结果已保存:")
            print(f"[{api_key}]    Raw: {raw_file}")
            print(f"[{api_key}]    Normalized: {normalized_file}")
            print(f"[{api_key}]    Log: {log_file}")
            
        except Exception as e:
            print(f"[{api_key}] ❌ 保存结果失败: {e}")
    
    def process_batch_parallel(self, start_num: int, end_num: int, max_workers: int = None):
        """并行批量处理报告"""
        if max_workers is None:
            max_workers = len(self.extractors)
        
        print("🚀 开始并行批量处理报告")
        print("=" * 80)
        print(f"📊 处理范围: report_{start_num} - report_{end_num}")
        print(f"📁 输出目录: {self.output_dir}")
        print(f"🔗 可用API: {list(self.extractors.keys())}")
        print(f"🧵 最大并发数: {max_workers}")
        print()
        
        # 准备报告任务
        report_nums = list(range(start_num, end_num + 1))
        api_queue = Queue()
        
        # 将API密钥放入队列，实现负载均衡
        for api_key in self.extractors.keys():
            api_queue.put(api_key)
        
        start_time = time.time()
        completed_count = 0
        success_count = 0
        failed_count = 0
        
        # 使用线程池执行并行处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 创建任务映射
            future_to_report = {}
            
            for report_num in report_nums:
                # 从队列中获取API密钥
                if not api_queue.empty():
                    api_key = api_queue.get()
                else:
                    # 如果队列为空，使用第一个API
                    api_key = list(self.extractors.keys())[0]
                
                future = executor.submit(self.process_single_report, report_num, api_key)
                future_to_report[future] = (report_num, api_key)
            
            # 处理完成的任务
            for future in as_completed(future_to_report):
                report_num, api_key = future_to_report[future]
                
                try:
                    result = future.result()
                    completed_count += 1
                    
                    if result["success"]:
                        success_count += 1
                        print(f"✅ [{api_key}] report_{report_num}: 处理成功")
                    else:
                        failed_count += 1
                        print(f"❌ [{api_key}] report_{report_num}: 处理失败 - {result.get('error', 'Unknown')}")
                    
                    # 将API密钥放回队列
                    api_queue.put(api_key)
                    
                    # 显示进度
                    progress = (completed_count / len(report_nums)) * 100
                    print(f"📈 进度: {progress:.1f}% ({completed_count}/{len(report_nums)})")
                    print()
                    
                except Exception as e:
                    failed_count += 1
                    print(f"❌ [{api_key}] report_{report_num}: 执行异常 - {e}")
                    # 将API密钥放回队列
                    api_queue.put(api_key)
        
        # 生成最终总结
        total_time = time.time() - start_time
        self.generate_batch_summary(start_num, end_num, len(report_nums), success_count, failed_count, total_time)
    
    def generate_batch_summary(self, start_num: int, end_num: int, total: int, success: int, failed: int, total_time: float):
        """生成批量处理总结"""
        print()
        print("=" * 60)
        print("📊 并行批量处理完成总结")
        print("=" * 60)
        print(f"📁 输出目录: {self.output_dir}")
        print(f"📈 处理统计:")
        print(f"   总报告数: {total}")
        print(f"   成功处理: {success}")
        print(f"   处理失败: {failed}")
        print(f"   成功率: {(success/total*100):.1f}%")
        print(f"⏱️ 总耗时: {total_time:.1f}秒")
        print(f"⚡ 平均每报告: {total_time/total:.1f}秒")
        
        # 保存总结到文件
        summary = {
            "batch_info": {
                "start_num": start_num,
                "end_num": end_num,
                "total_reports": total,
                "successful": success,
                "failed": failed,
                "success_rate": f"{(success/total*100):.1f}%",
                "total_time": f"{total_time:.1f}s",
                "avg_time_per_report": f"{total_time/total:.1f}s"
            },
            "timestamp": datetime.now().isoformat(),
            "api_config": list(self.extractors.keys()),
            "output_directory": self.output_dir
        }
        
        summary_file = f"{self.output_dir}/batch_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"📋 批量摘要已保存: {summary_file}")

def main():
    """主函数"""
    print("🏥 医学报告并行批量处理系统")
    print("=" * 80)
    
    try:
        # 使用5个API密钥进行并行处理
        api_keys = ["api_13", "api_14", "api_15", "api_16", "api_12"]
        processor = ParallelBatchReportProcessor(api_keys=api_keys)
        
        # 并行批量处理报告10061-10070
        processor.process_batch_parallel(start_num=10061, end_num=10070, max_workers=5)
        
    except Exception as e:
        print(f"❌ 系统初始化失败: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main() 