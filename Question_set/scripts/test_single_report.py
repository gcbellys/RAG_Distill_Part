#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单报告症状提取测试脚本
用于测试症状提取系统在单个报告上的功能
"""

import os
import sys
import json
from datetime import datetime

# 添加项目根目录到Python路径
project_root = "/opt/RAG_Evidence4Organ"
sys.path.insert(0, project_root)

from Question_set.extractors.symptom_extractor import SymptomExtractor
from Question_set.prompts.symptom_prompts import get_prompt_by_task
from Question_set.processors.document_processor import DocumentProcessor
from configs.system_config import MULTI_API_CONFIG

def test_single_report(report_number: int = 40000, api_name: str = "api_1", prompt_type: str = "comprehensive"):
    """Test symptom extraction on a single report"""
    
    print(f"🧪 Starting symptom extraction system test")
    print(f"Test report: report_{report_number}.txt")
    print(f"Using API: {api_name}")
    print(f"Prompt type: {prompt_type}")
    print("=" * 60)
    
    # 1. Read test report
    report_file = f"dataset/report_{report_number}.txt"
    if not os.path.exists(report_file):
        print(f"❌ Error: Test file not found: {report_file}")
        return False
    
    try:
        with open(report_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        print(f"✅ Successfully read report file")
        print(f"   Text length: {len(text)} characters")
        print(f"   Word count: {len(text.split())} words")
        print(f"   First 200 characters: {text[:200]}...")
        print()
        
    except Exception as e:
        print(f"❌ Failed to read report file: {str(e)}")
        return False
    
    # 2. Initialize API configuration
    api_config = MULTI_API_CONFIG.get(api_name)
    if not api_config:
        print(f"❌ Error: API configuration not found: {api_name}")
        return False
    
    print(f"✅ API configuration loaded successfully")
    print(f"   Model: {api_config['model']}")
    print(f"   Base URL: {api_config['base_url']}")
    print()
    
    # 3. Initialize components
    try:
        extractor = SymptomExtractor(
            model=api_config["model"],
            api_key=api_config["api_key"],
            base_url=api_config["base_url"]
        )
        
        processor = DocumentProcessor()
        prompt = get_prompt_by_task(prompt_type)
        
        print(f"✅ Components initialized successfully")
        print(f"   Prompt length: {len(prompt)} characters")
        print()
        
    except Exception as e:
        print(f"❌ Component initialization failed: {str(e)}")
        return False
    
    # 4. Document preprocessing and chunking
    try:
        print("🔄 Starting document preprocessing...")
        chunks = processor.process_document(text, f"report_{report_number}")
        
        print(f"✅ Document preprocessing completed")
        print(f"   Generated chunks: {len(chunks)}")
        
        if chunks:
            for i, chunk in enumerate(chunks):
                print(f"   Chunk {i+1}: {chunk['section_name']} ({chunk.get('char_count', 'N/A')} characters)")
        print()
        
    except Exception as e:
        print(f"❌ Document preprocessing failed: {str(e)}")
        return False
    
    if not chunks:
        print("⚠️ Warning: No valid chunks generated, document may not contain symptom keywords")
        return True
    
    # 5. Symptom extraction
    try:
        print("🔄 Starting symptom extraction...")
        start_time = datetime.now()
        
        if len(chunks) == 1:
            symptoms = extractor.extract_symptoms_from_text(chunks[0]["content"], prompt)
        else:
            symptoms = extractor.extract_symptoms_from_chunks(chunks, prompt)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        print(f"✅ Symptom extraction completed")
        print(f"   Processing time: {processing_time:.2f} seconds")
        print(f"   Extracted symptoms: {len(symptoms)}")
        print()
        
    except Exception as e:
        print(f"❌ Symptom extraction failed: {str(e)}")
        return False
    
    # 6. Display extraction results
    if symptoms:
        print("📋 Extracted symptom details:")
        print("-" * 60)
        
        for i, symptom in enumerate(symptoms[:5], 1):  # Only show first 5
            print(f"Symptom {i}:")
            print(f"  Description: {symptom.get('symptom_description', 'N/A')}")
            print(f"  Type: {symptom.get('symptom_type', 'N/A')}")
            print(f"  Body system: {symptom.get('body_system', 'N/A')}")
            print(f"  Severity: {symptom.get('severity', 'N/A')}")
            print(f"  Confidence: {symptom.get('confidence_score', 'N/A')}")
            print(f"  Original text: {symptom.get('original_text', 'N/A')[:100]}...")
            print()
        
        if len(symptoms) > 5:
            print(f"... {len(symptoms) - 5} more symptoms not shown")
        print()
    else:
        print("⚠️ No symptoms extracted")
    
    # 7. Save test results
    try:
        test_output_dir = "Question_set/results/test_output"
        os.makedirs(test_output_dir, exist_ok=True)
        
        test_result = {
            "test_info": {
                "report_number": report_number,
                "api_name": api_name,
                "prompt_type": prompt_type,
                "test_time": datetime.now().isoformat(),
                "processing_time_seconds": processing_time
            },
            "document_stats": {
                "original_length": len(text),
                "word_count": len(text.split()),
                "chunks_generated": len(chunks)
            },
            "extraction_results": {
                "symptoms_count": len(symptoms),
                "symptoms": symptoms
            }
        }
        
        output_file = os.path.join(test_output_dir, f"test_report_{report_number}_{api_name}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(test_result, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Test results saved to: {output_file}")
        print()
        
    except Exception as e:
        print(f"⚠️ Failed to save test results: {str(e)}")
    
    # 8. Test summary
    print("🎯 Test summary:")
    print(f"   ✅ Document processing: Success (generated {len(chunks)} chunks)")
    print(f"   ✅ Symptom extraction: Success (extracted {len(symptoms)} symptoms)")
    print(f"   ✅ Processing time: {processing_time:.2f} seconds")
    print(f"   ✅ Average processing speed: {len(text) / processing_time:.0f} characters/second")
    
    return True

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Single report symptom extraction test")
    parser.add_argument("--report", type=int, default=40000, help="Report number")
    parser.add_argument("--api", type=str, default="api_1", help="API name")
    parser.add_argument("--prompt", type=str, default="comprehensive", 
                       choices=["identification", "generation", "comprehensive", "batch"],
                       help="Prompt type")
    
    args = parser.parse_args()
    
    success = test_single_report(args.report, args.api, args.prompt)
    
    if success:
        print("\n🎉 Test completed! Symptom extraction system is working properly.")
        print("You can now run the full batch processing script:")
        print("  ./Question_set/scripts/start_symptom_extraction.sh")
    else:
        print("\n❌ Test failed! Please check system configuration and dependencies.")
    
    return success

if __name__ == "__main__":
    main() 