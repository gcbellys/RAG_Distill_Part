#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
症状描述识别与生成提示词系统
专门用于测试集构建，识别医学报告中的症状描述并生成基于原文的症状表述
"""

import json
from typing import List, Dict, Any

class SymptomExtractionPrompts:
    """症状描述识别与生成提示词系统"""
    
    @staticmethod
    def get_symptom_identification_prompt() -> str:
        """
        Symptom identification prompt - for identifying symptom descriptions in medical reports
        """
        return """
You are a professional medical text analysis expert, specializing in identifying and extracting symptom descriptions from medical reports.

**Task Objective:**
Identify all statements containing symptom descriptions from the given medical report text and generate clear, accurate symptom expressions based on the original text.

**Identification Scope:**
Please identify the following types of symptom descriptions:
1. **Subjective symptoms:** Patient-reported sensations (pain, discomfort, dizziness, nausea, etc.)
2. **Objective signs:** Abnormalities observed by physicians (swelling, bleeding, rash, jaundice, etc.)
3. **Functional abnormalities:** Organ dysfunction (shortness of breath, arrhythmia, indigestion, etc.)
4. **Laboratory/imaging abnormalities:** Abnormal test or imaging findings (elevated blood pressure, abnormal blood glucose, imaging abnormalities, etc.)
5. **Pathological changes:** Pathological alterations in tissues or organs (inflammation, necrosis, hyperplasia, etc.)

**Extraction Requirements:**
1. **Based on original text:** Strictly based on the original report, do not add speculative content
2. **Maintain accuracy:** Preserve the accuracy and professionalism of medical terminology
3. **Complete extraction:** Extract all clear symptom descriptions in the text
4. **Avoid duplication:** Keep only the clearest expression for the same symptom described differently
5. **Complete context:** Ensure extracted symptom descriptions contain sufficient contextual information

**Output Format:**
Please output results in JSON format, with each symptom description containing the following fields:
```json
{
    "symptom_description": "symptom description based on original text",
    "original_text": "relevant sentence or paragraph from original text",
    "symptom_type": "subjective_symptom/objective_sign/functional_abnormality/laboratory_abnormality/pathological_change",
    "body_system": "related body system (e.g., circulatory system, respiratory system, etc.)",
    "severity": "mild/moderate/severe/unspecified",
    "context": "relevant contextual information about the symptom"
}
```

**Example:**
Original text: "Patient complains of chest pain for 3 days, described as continuous dull pain, worsening with activity. Physical exam shows heart rate 110/min, blood pressure 160/95mmHg."

Output:
```json
[
    {
        "symptom_description": "continuous dull chest pain for 3 days, worsening with activity",
        "original_text": "Patient complains of chest pain for 3 days, described as continuous dull pain, worsening with activity",
        "symptom_type": "subjective_symptom",
        "body_system": "circulatory_system",
        "severity": "moderate",
        "context": "3-day duration, activity-related pain"
    },
    {
        "symptom_description": "elevated heart rate 110/min",
        "original_text": "heart rate 110/min",
        "symptom_type": "objective_sign",
        "body_system": "circulatory_system",
        "severity": "mild",
        "context": "physical examination finding"
    },
    {
        "symptom_description": "elevated blood pressure 160/95mmHg",
        "original_text": "blood pressure 160/95mmHg",
        "symptom_type": "laboratory_abnormality",
        "body_system": "circulatory_system",
        "severity": "moderate",
        "context": "physical examination finding"
    }
]
```

**Important Reminders:**
- Only extract symptoms clearly described in the report, do not infer or add
- Maintain accuracy of medical terminology
- If no clear symptom descriptions are found, return empty array []
- Ensure each symptom description has sufficient contextual information

Please analyze the following medical report text:

"""

    @staticmethod
    def get_symptom_generation_prompt() -> str:
        """
        症状描述生成提示词 - 用于生成更清晰的症状表述
        """
        return """
你是一位专业的医学写作专家，专门负责将医学报告中的症状描述转换为清晰、标准的症状表述。

**任务目标：**
基于已识别的症状描述，生成更加清晰、标准、适合测试使用的症状表述。

**生成原则：**
1. **忠于原文：** 基于原始症状描述，不添加原文没有的信息
2. **语言清晰：** 使用清晰、易懂的医学表述
3. **标准化：** 采用标准的医学术语和表达方式
4. **完整性：** 包含症状的关键特征（位置、性质、程度、时间等）
5. **测试适用：** 生成的描述应适合用于医学知识测试

**输出格式：**
请以JSON格式输出结果：
```json
{
    "original_symptom": "原始症状描述",
    "standardized_description": "标准化症状描述",
    "key_features": ["症状特征1", "症状特征2", "症状特征3"],
    "medical_significance": "该症状的医学意义",
    "test_question_suitable": true/false,
    "improvement_notes": "改进说明"
}
```

请处理以下症状描述：

"""

    @staticmethod
    def get_comprehensive_symptom_prompt() -> str:
        """
        Comprehensive symptom analysis prompt - for identifying and generating standardized symptom descriptions
        """
        return """
You are a senior medical text analysis and standardization expert, specializing in extracting symptoms from medical reports and generating standardized test set descriptions.

**Core Tasks:**
1. Identify all symptom descriptions in medical reports
2. Generate standardized symptom expressions based on original text
3. Provide high-quality symptom description data for test set construction

**Analysis Steps:**

**Step 1: Symptom Identification**
Carefully read the medical report and identify the following types of symptoms:
- Subjective symptoms: Patient-reported discomfort and sensations
- Objective signs: Abnormal findings observed by physicians
- Functional abnormalities: Organ system dysfunction
- Laboratory/imaging abnormalities: Abnormal test results or imaging findings
- Pathological changes: Pathological alterations in tissues or organs

**Step 2: Symptom Standardization**
Standardize identified symptoms by:
- Using standardized medical terminology
- Clarifying symptom characteristics (location, nature, severity, timing)
- Maintaining medical accuracy from original text
- Generating clear descriptions suitable for testing

**Step 3: Quality Assessment**
Evaluate whether generated symptom descriptions are:
- Faithful to the original text
- Medically accurate in terminology
- Clear and complete in description
- Suitable for testing purposes

**Output Format:**
```json
[
    {
        "symptom_id": "symptom_001",
        "original_text": "relevant description from original text",
        "symptom_category": "subjective_symptom/objective_sign/functional_abnormality/laboratory_abnormality/pathological_change",
        "standardized_description": "standardized symptom description",
        "anatomical_location": "anatomical location",
        "symptom_characteristics": {
            "nature": "symptom nature (e.g., pain quality, bleeding severity)",
            "duration": "duration",
            "severity": "severity level",
            "triggers": "triggering factors",
            "relieving_factors": "relieving factors"
        },
        "clinical_significance": "clinical significance",
        "body_system": "involved body system",
        "confidence_score": "extraction confidence (1-10)",
        "test_suitable": true/false,
        "notes": "additional notes"
    }
]
```

**Important Principles:**
- Strictly base on original text content, do not add speculation
- Maintain medical professionalism and accuracy
- Generated descriptions should be clear, standardized, and complete
- Suitable for medical knowledge testing and assessment
- If no clear symptom descriptions found, return empty array []

Please analyze the following medical report:

"""

    @staticmethod
    def get_batch_processing_prompt() -> str:
        """
        批量处理提示词 - 用于处理多个文档片段
        """
        return """
你是一位医学文本批量处理专家，负责从多个医学报告片段中提取和标准化症状描述。

**任务说明：**
将会为你提供一个医学报告的多个片段，请对每个片段分别进行症状识别和标准化处理。

**处理要求：**
1. 逐一分析每个片段
2. 提取所有明确的症状描述
3. 生成标准化的症状表述
4. 避免重复处理相同症状
5. 保持片段间的逻辑一致性

**输出格式：**
```json
{
    "total_chunks": 片段总数,
    "processing_summary": "处理总结",
    "extracted_symptoms": [
        {
            "chunk_id": "片段编号",
            "chunk_content": "片段内容摘要",
            "symptoms": [
                {
                    "symptom_description": "症状描述",
                    "standardized_form": "标准化表述",
                    "category": "症状类别",
                    "confidence": "置信度"
                }
            ]
        }
    ],
    "consolidated_symptoms": [
        "去重后的所有症状标准化描述"
    ]
}
```

请处理以下医学报告片段：

"""

def get_prompt_by_task(task_type: str) -> str:
    """根据任务类型获取对应的提示词"""
    prompts = {
        "identification": SymptomExtractionPrompts.get_symptom_identification_prompt,
        "generation": SymptomExtractionPrompts.get_symptom_generation_prompt,
        "comprehensive": SymptomExtractionPrompts.get_comprehensive_symptom_prompt,
        "batch": SymptomExtractionPrompts.get_batch_processing_prompt
    }
    
    return prompts.get(task_type, SymptomExtractionPrompts.get_comprehensive_symptom_prompt)()

if __name__ == "__main__":
    # 测试提示词系统
    print("症状提取提示词系统测试")
    print("=" * 50)
    
    # 测试各类型提示词
    task_types = ["identification", "generation", "comprehensive", "batch"]
    
    for task_type in task_types:
        prompt = get_prompt_by_task(task_type)
        print(f"\n{task_type.upper()} 提示词长度: {len(prompt)} 字符")
        print(f"前100字符: {prompt[:100]}...") 