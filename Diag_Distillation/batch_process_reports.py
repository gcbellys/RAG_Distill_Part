#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量处理医学报告脚本
处理指定范围的报告，为每个报告生成raw、normalized、log三个文件
"""

import os
import sys
import json
import time
import traceback
from datetime import datetime
from typing import Dict, Any, List

# 添加项目根目录到Python路径
project_root = "/opt/RAG_Evidence4Organ"
sys.path.insert(0, project_root)

from Question_Distillation_v2.extractors.llm_extractor import LLMExtractor
from Diag_Distillation.prompts.medical_prompts import DiagnosticExtractionPrompts
from Diag_Distillation.process_worker import process_report_with_diagnostic_steps
from configs.system_config import MULTI_API_CONFIG

class BatchReportProcessor:
    def __init__(self, api_key_name: str = "api_16"):
        self.api_key_name = api_key_name
        self.setup_api()
        self.setup_output_dir()
        self.prompts = DiagnosticExtractionPrompts()
        
    def setup_api(self):
        """初始化API"""
        api_config = MULTI_API_CONFIG.get(self.api_key_name)
        if not api_config:
            raise ValueError(f"未找到API配置: {self.api_key_name}")
        
        self.extractor = LLMExtractor(
            model=api_config["model"],
            api_key=api_config["api_key"],
            base_url=api_config["base_url"]
        )
        print(f"✅ API初始化成功: {api_config['model']}")
    
    def setup_output_dir(self):
        """设置输出目录"""
        self.output_dir = "/opt/RAG_Evidence4Organ/Diag_Distillation/output_test"
        
        # 清理旧的输出目录
        if os.path.exists(self.output_dir):
            import shutil
            shutil.rmtree(self.output_dir)
            print(f"🗑️ 清理旧的输出目录: {self.output_dir}")
        
        # 创建新的输出目录结构
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "raw"), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "normalized"), exist_ok=True) 
        os.makedirs(os.path.join(self.output_dir, "logs"), exist_ok=True)
        print(f"📁 创建输出目录结构: {self.output_dir}")
    
    def load_report(self, report_num: int) -> str:
        """加载指定编号的报告"""
        report_path = f"/opt/RAG_Evidence4Organ/dataset/report_{report_num}.txt"
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            return content
        except FileNotFoundError:
            print(f"❌ 报告文件不存在: {report_path}")
            return ""
        except Exception as e:
            print(f"❌ 读取报告失败 {report_path}: {e}")
            return ""
    
    def process_single_report(self, report_num: int) -> Dict[str, Any]:
        """处理单个报告"""
        print(f"\n{'='*20} 处理报告 {report_num} {'='*20}")
        
        # 记录处理日志
        log_entries = []
        start_time = time.time()
        
        def log(message: str, level: str = "INFO"):
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"[{timestamp}] [{level}] {message}"
            log_entries.append(log_entry)
            print(log_entry)
        
        log(f"开始处理报告: report_{report_num}")
        
        # 加载报告
        report_content = self.load_report(report_num)
        if not report_content:
            log(f"报告加载失败", "ERROR")
            return {
                "success": False,
                "error": "报告加载失败",
                "log_entries": log_entries
            }
        
        log(f"报告加载成功: {len(report_content)} 字符")
        
        try:
            # 处理报告
            log("开始诊断蒸馏处理...")
            
            result = process_report_with_diagnostic_steps(
                extractor=self.extractor,
                report_data={"text": report_content},
                report_num=f"report_{report_num}",
                prompts=self.prompts,
                api_key_name=self.api_key_name
            )
            
            processing_time = time.time() - start_time
            
            if result:
                # 分析结果
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
                self.save_results(report_num, result)
                
                return {
                    "success": True,
                    "report_num": report_num,
                    "raw": raw,
                    "normalized": normalized,
                    "processing_time": processing_time,
                    "log_entries": log_entries,
                    "statistics": {
                        "total_findings": len(normalized),
                        "total_units": sum(len(item.get('U_unit_set', [])) for item in normalized),
                        "unique_organs": len(unique_organs) if 'unique_organs' in locals() else 0
                    }
                }
            else:
                log("处理失败: 未返回结果", "ERROR")
                return {
                    "success": False,
                    "error": "处理失败: 未返回结果",
                    "log_entries": log_entries
                }
                
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"处理过程出错: {str(e)}"
            log(error_msg, "ERROR")
            log(f"错误详情: {traceback.format_exc()}", "ERROR")
            
            return {
                "success": False,
                "error": error_msg,
                "processing_time": processing_time,
                "log_entries": log_entries
            }
    
    def save_results(self, report_num: int, result: Dict[str, Any]):
        """保存处理结果到三个文件"""
        
        # 文件路径
        raw_file = os.path.join(self.output_dir, "raw", f"report_{report_num}_raw.json")
        normalized_file = os.path.join(self.output_dir, "normalized", f"report_{report_num}_normalized.json")
        log_file = os.path.join(self.output_dir, "logs", f"report_{report_num}_log.txt")
        
        try:
            if result["success"]:
                # 保存raw结果
                with open(raw_file, 'w', encoding='utf-8') as f:
                    json.dump(result["raw"], f, ensure_ascii=False, indent=2)
                
                # 保存normalized结果
                with open(normalized_file, 'w', encoding='utf-8') as f:
                    json.dump(result["normalized"], f, ensure_ascii=False, indent=2)
                
                print(f"💾 结果已保存:")
                print(f"   Raw: {raw_file}")
                print(f"   Normalized: {normalized_file}")
            else:
                # 保存错误信息
                error_info = {
                    "success": False,
                    "error": result.get("error", "未知错误"),
                    "timestamp": datetime.now().isoformat()
                }
                
                with open(raw_file, 'w', encoding='utf-8') as f:
                    json.dump(error_info, f, ensure_ascii=False, indent=2)
                
                with open(normalized_file, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                
                print(f"❌ 错误信息已保存:")
                print(f"   Raw: {raw_file}")
                print(f"   Normalized: {normalized_file}")
            
            # 保存日志
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("\n".join(result["log_entries"]))
            
            print(f"   Log: {log_file}")
            
        except Exception as e:
            print(f"❌ 保存结果失败: {e}")
    
    def process_batch(self, start_num: int, end_num: int):
        """批量处理报告"""
        print(f"🚀 开始批量处理报告")
        print(f"📊 处理范围: report_{start_num} - report_{end_num}")
        print(f"📁 输出目录: {self.output_dir}")
        print(f"🔑 API配置: {self.api_key_name}")
        print()
        
        total_reports = end_num - start_num + 1
        successful = 0
        failed = 0
        batch_start_time = time.time()
        
        for report_num in range(start_num, end_num + 1):
            try:
                # 处理报告
                result = self.process_single_report(report_num)
                
                # 保存结果
                self.save_results(report_num, result)
                
                if result["success"]:
                    successful += 1
                    print(f"✅ report_{report_num}: 处理成功")
                else:
                    failed += 1
                    print(f"❌ report_{report_num}: 处理失败 - {result.get('error', '未知错误')}")
                
                # 进度显示
                progress = ((report_num - start_num + 1) / total_reports) * 100
                print(f"📈 进度: {progress:.1f}% ({report_num - start_num + 1}/{total_reports})")
                
                # 简短休息避免API限制
                time.sleep(1)
                
            except Exception as e:
                failed += 1
                print(f"❌ report_{report_num}: 严重错误 - {e}")
                
                # 记录错误并继续
                error_result = {
                    "success": False,
                    "error": str(e),
                    "log_entries": [f"[{datetime.now()}] [ERROR] 严重错误: {e}"]
                }
                self.save_results(report_num, error_result)
        
        # 批量处理总结
        total_time = time.time() - batch_start_time
        
        print(f"\n{'='*60}")
        print(f"📊 批量处理完成总结")
        print(f"{'='*60}")
        print(f"📁 输出目录: {self.output_dir}")
        print(f"📈 处理统计:")
        print(f"   总报告数: {total_reports}")
        print(f"   成功处理: {successful}")
        print(f"   处理失败: {failed}")
        print(f"   成功率: {(successful/total_reports)*100:.1f}%")
        print(f"⏱️ 总耗时: {total_time:.1f}秒")
        print(f"⚡ 平均每报告: {total_time/total_reports:.1f}秒")
        
        # 生成批量处理摘要
        summary = {
            "batch_info": {
                "start_num": start_num,
                "end_num": end_num,
                "total_reports": total_reports,
                "successful": successful,
                "failed": failed,
                "success_rate": f"{(successful/total_reports)*100:.1f}%",
                "total_time": f"{total_time:.1f}s",
                "avg_time_per_report": f"{total_time/total_reports:.1f}s"
            },
            "timestamp": datetime.now().isoformat(),
            "api_config": self.api_key_name,
            "output_directory": self.output_dir
        }
        
        summary_file = os.path.join(self.output_dir, "batch_summary.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"📋 批量摘要已保存: {summary_file}")

def main():
    """主函数"""
    print("🏥 医学报告批量处理系统")
    print("=" * 80)
    
    try:
        # 初始化处理器
        processor = BatchReportProcessor(api_key_name="api_16")
        
        # 批量处理报告10061-10070
        processor.process_batch(start_num=10061, end_num=10070)
        
    except Exception as e:
        print(f"❌ 系统初始化失败: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main() 