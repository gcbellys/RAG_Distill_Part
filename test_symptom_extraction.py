 #!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试症状提取逻辑
"""

import sys
import os
sys.path.append('/opt/RAG_Evidence4Organ')

def test_symptom_extraction_prompt():
    """测试症状提取提示词"""
    
    try:
        from Diag_Distillation.prompts.medical_prompts import DiagnosticExtractionPrompts
        
        prompts = DiagnosticExtractionPrompts()
        
        # 测试文本
        test_text = """
Chief Complaint: Patient reports 3 days of chest pain radiating to left arm, associated with shortness of breath and nausea.
Physical Examination: Patient appears in moderate distress. Complains of chest pain rated 8/10. Patient is diaphoretic and tachypneic.
        """
        
        # 获取提示词
        prompt = prompts.get_step1_complaint_extraction_prompt(test_text)
        
        print("✅ 症状提取提示词测试成功")
        print(f"📝 提示词长度: {len(prompt)} 字符")
        
        # 检查关键短语
        key_phrases = [
            "COMPREHENSIVE SYMPTOM EXTRACTION",
            "Priority 1 - Patient Complaint Sections", 
            "Priority 2 - Other Symptom Descriptions",
            "What to Extract (SYMPTOMS)",
            "What NOT to Extract (DIAGNOSES/JUDGMENTS)"
        ]
        
        missing_phrases = []
        for phrase in key_phrases:
            if phrase not in prompt:
                missing_phrases.append(phrase)
        
        if missing_phrases:
            print(f"❌ 缺少关键短语: {missing_phrases}")
            return False
        else:
            print("✅ 所有关键短语都已包含")
            return True
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_process_worker_import():
    """测试process_worker导入"""
    
    try:
        from Diag_Distillation.process_worker import smart_chunk_medical_report
        
        # 测试文本
        test_text = """
Chief Complaint: Chest pain
History of Present Illness: Patient reports chest pain
Assessment: Acute myocardial infarction
        """
        
        chunks = smart_chunk_medical_report(test_text)
        
        print("✅ process_worker导入测试成功")
        print(f"📊 识别到 {len(chunks)} 个块")
        
        for chunk in chunks:
            print(f"   - {chunk['section']} ({chunk['type']})")
        
        return True
        
    except Exception as e:
        print(f"❌ process_worker测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🔍 开始测试症状提取逻辑...")
    print("=" * 50)
    
    success1 = test_symptom_extraction_prompt()
    success2 = test_process_worker_import()
    
    print("=" * 50)
    if success1 and success2:
        print("🎉 所有测试通过！症状提取逻辑修改成功。")
    else:
        print("❌ 部分测试失败，需要检查修改。")