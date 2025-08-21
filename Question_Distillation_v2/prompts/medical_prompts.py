#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医学信息抽取知识蒸馏提示词系统
用于从医学文本中提取症状/疾病与器官及解剖学部位的对应关系
"""

import json
from typing import List, Dict, Any

# Import the definitive source of truth for organ structures
from configs.model_config import ORGAN_ANATOMY_STRUCTURE

class MedicalExtractionPrompts:
    """医学信息抽取提示词系统"""
    
    @staticmethod
    def get_primary_extraction_prompt() -> str:
        """
        Primary extraction prompt - for identifying symptom/disease and organ relationships
        """
        return """
You are a top-tier medical information extraction expert, specializing in extracting structured medical information from clinical texts.

Task Description:
I will provide you with a medical text. Please carefully read it and identify all clear correspondences between "specific symptoms/diseases" and "organs" requiring imaging examination and their "specific anatomical locations".

Extraction Requirements:
1. Symptoms/Diseases: including but not limited to pain, bleeding, swelling, infection, obstruction, rupture, inflammation, etc.
2. Organs: heart, lung, liver, thyroid and other major organs
3. Specific Anatomical Locations: such as left ventricle, right lower lobe of lung, right lobe of liver, thyroid nodule, etc.

Output Format:
Please output the results in strict JSON format, with each record containing the following fields:
{
    "disease_symptom": "specific symptom or disease description",
    "organ": "related organ name", 
    "specific_part": "specific anatomical location",
    "confidence": "high/medium/low",
    "evidence": "text fragment supporting this relationship"
}

If no clear correspondence is found, output an empty list: []

Important Notes:
- Only extract relationships with clear medical evidence
- Avoid speculative or inferred relationships
- Prioritize cases requiring imaging examination
- Maintain accuracy of medical terminology
- If the same symptom involves multiple organs, list them separately

Please begin analyzing the following medical text:
"""

    @staticmethod
    def get_specialized_cardiac_prompt() -> str:
        """
        Cardiac specialty prompt - specifically for extracting heart-related symptoms
        """
        return """
You are a cardiologist specializing in the diagnosis and treatment of cardiovascular diseases.

Task: Extract heart-related symptoms/diseases and their correspondence with specific cardiac locations from the following medical text.

Focus Areas:
1. Cardiac Symptoms: chest pain, palpitations, dyspnea, syncope, edema, etc.
2. Cardiac Structures: left atrium, right atrium, left ventricle, right ventricle, coronary arteries, valves, etc.
3. Cardiac Function: systolic function, diastolic function, conduction system, etc.
4. Imaging Studies: ECG, echocardiogram, coronary angiography, CT, MRI, etc.

Special Requirements:
- Distinguish between cardiac and non-cardiac chest pain
- Identify specific types of arrhythmias
- Pay attention to specific locations of valvular lesions
- Focus on the distribution of coronary artery disease

Output Format:
{
    "disease_symptom": "specific symptom or disease description",
    "organ": "heart", 
    "specific_part": "specific cardiac location",
    "confidence": "high/medium/low",
    "evidence": "text fragment supporting this relationship"
}

Please extract heart-related information from the following text:
"""

    @staticmethod
    def get_specialized_pulmonary_prompt() -> str:
        """
        Pulmonary specialty prompt - specifically for extracting lung-related symptoms
        """
        return """
You are a pulmonologist specializing in the diagnosis and treatment of respiratory system diseases.

Task: Extract lung-related symptoms/diseases and their correspondence with specific pulmonary locations from the following medical text.

Focus Areas:
1. Respiratory Symptoms: cough, sputum, dyspnea, chest pain, hemoptysis, etc.
2. Pulmonary Structures: left lung, right lung, upper lobe, middle lobe, lower lobe, bronchi, alveoli, etc.
3. Pulmonary Lesions: pneumonia, pulmonary embolism, pulmonary nodules, pleural effusion, pneumothorax, etc.
4. Imaging Studies: chest X-ray, CT, MRI, bronchoscopy, etc.

Special Requirements:
- Distinguish between infectious and non-infectious pulmonary diseases
- Identify the source of pulmonary embolism
- Pay attention to the location and characteristics of pulmonary nodules
- Focus on the distribution of pleural effusion

Output Format:
{
    "disease_symptom": "specific symptom or disease description",
    "organ": "lung", 
    "specific_part": "specific pulmonary location",
    "confidence": "high/medium/low",
    "evidence": "text fragment supporting this relationship"
}

Please extract lung-related information from the following text:
"""

    @staticmethod
    def get_specialized_liver_prompt() -> str:
        """
        Liver specialty prompt - specifically for extracting liver-related symptoms
        """
        return """
You are a hepatologist specializing in the diagnosis and treatment of liver diseases.

Task: Extract liver-related symptoms/diseases and their correspondence with specific hepatic locations from the following medical text.

Focus Areas:
1. Hepatic Symptoms: abdominal pain, jaundice, ascites, hepatomegaly, liver function abnormalities, etc.
2. Hepatic Structures: left lobe of liver, right lobe of liver, porta hepatis, hepatic vessels, bile ducts, etc.
3. Hepatic Lesions: hepatitis, cirrhosis, liver tumors, liver cysts, hepatic hemangioma, etc.
4. Imaging Studies: ultrasound, CT, MRI, liver biopsy, etc.

Special Requirements:
- Distinguish between viral and non-viral hepatitis
- Identify specific locations of liver tumors
- Pay attention to the degree of cirrhosis and complications
- Focus on the extent of bile duct involvement

Output Format:
{
    "disease_symptom": "specific symptom or disease description",
    "organ": "liver", 
    "specific_part": "specific hepatic location",
    "confidence": "high/medium/low",
    "evidence": "text fragment supporting this relationship"
}

Please extract liver-related information from the following text:
"""

    @staticmethod
    def get_specialized_thyroid_prompt() -> str:
        """
        Thyroid specialty prompt - specifically for extracting thyroid-related symptoms
        """
        return """
You are an endocrinologist specializing in the diagnosis and treatment of thyroid diseases.

Task: Extract thyroid-related symptoms/diseases and their correspondence with specific thyroid locations from the following medical text.

Focus Areas:
1. Thyroid Symptoms: neck mass, dysphagia, hoarseness, palpitations, weight changes, etc.
2. Thyroid Structures: left thyroid lobe, right thyroid lobe, isthmus, nodules, etc.
3. Thyroid Lesions: thyroid nodules, thyroiditis, hyperthyroidism, thyroid cancer, etc.
4. Imaging Studies: ultrasound, CT, nuclear scan, fine needle aspiration, etc.

Special Requirements:
- Distinguish between benign and malignant thyroid nodules
- Identify types of thyroid dysfunction
- Pay attention to the location and characteristics of thyroid nodules
- Focus on the extent of thyroiditis involvement

Output Format:
{
    "disease_symptom": "specific symptom or disease description",
    "organ": "thyroid", 
    "specific_part": "specific thyroid location",
    "confidence": "high/medium/low",
    "evidence": "text fragment supporting this relationship"
}

Please extract thyroid-related information from the following text:
"""

    @staticmethod
    def get_validation_prompt() -> str:
        """
        Validation prompt - for final verification of extraction accuracy
        """
        return """
You are a medical information quality assurance expert.

Task: Please perform final verification of the following medical information extraction results.

Verification Dimensions:
1. Completeness: Whether important medical information is missing
2. Accuracy: Whether medical terminology and descriptions are accurate
3. Consistency: Whether information within the same case is consistent
4. Clinical Relevance: Whether extracted information has clinical significance
5. Imaging Indications: Whether imaging examination is indeed required

Verification Standards:
- Conforms to medical knowledge and clinical practice
- Standardized and accurate terminology usage
- Precise anatomical descriptions
- Sufficient and reliable evidence
- Clear clinical significance

Please verify the following extraction results and correct any issues:
"""

    @staticmethod
    def get_batch_processing_prompt() -> str:
        """
        Batch processing prompt - for processing multiple cases
        """
        return """
You are an efficient medical information processing expert.

Task: Batch process multiple medical cases to extract symptom/disease and organ correspondences.

Processing Requirements:
1. Maintain consistency in processing standards
2. Prioritize cases requiring imaging examination
3. Ensure completeness of information for each case
4. Pay attention to correlations between cases

Output Format:
[
    {
        "case_id": "case identifier",
        "extractions": [
            {
                "disease_symptom": "specific symptom or disease description",
                "organ": "related organ name", 
                "specific_part": "specific anatomical location",
                "confidence": "high/medium/low",
                "evidence": "text fragment supporting this relationship"
            }
        ]
    }
]

Please batch process the following medical cases:
"""

    @staticmethod
    def get_inference_prompt() -> str:
        """
        Returns a extraction prompt focused on the 5 specified organs only.
        Emphasizes extraction over inference to stay close to the original diagnosis.
        """
        
        structure_string = ""
        for organ, parts in ORGAN_ANATOMY_STRUCTURE.items():
            structure_string += f"\n- {organ}:\n"
            structure_string += "  " + ", ".join(f'"{part}"' for part in parts) + "\n"

        prompt = f"""
You are a medical information extraction expert. Your task is to EXTRACT symptom-organ relationships directly from the given medical report text, focusing ONLY on the 5 specified organs: Heart, Liver, Kidneys, Thyroid, and Pancreas.

**CORE PRINCIPLE: EXTRACT, DON'T INFER**
- Focus on symptoms and conditions that are explicitly mentioned in the text
- Only extract symptoms that relate to the 5 specified organs
- Avoid making medical inferences beyond what is stated in the report
- Each extracted item should have clear textual evidence from the report

**Step 1: Symptom Extraction**
Scan the report and extract symptoms, conditions, or medical findings that are explicitly mentioned and relate to Heart, Liver, Kidneys, Thyroid, or Pancreas. Look for:
- Direct symptom descriptions related to these organs
- Clinical findings affecting these organs
- Diagnostic results for these organs
- Physical examination findings

**Step 2: Organ Identification**
For each extracted symptom, identify which of the 5 specified organs it relates to based on:
- Organs explicitly mentioned in the text in relation to the symptom
- Medical context provided in the report
- ONLY choose from: Heart, Liver, Kidneys, Thyroid, Pancreas

**Step 3: Anatomical Structure Selection**
For all identified symptoms, you MUST choose anatomical structures EXACTLY from this strict list:
{structure_string}

**Output Requirements:**
- Your final output must be a single, valid JSON array `[]`
- Each object represents ONE distinct symptom or finding from the report
- Each object must contain:
  - `symptom_or_disease`: Exact symptom/condition as described in the report
  - `inferred_organ`: One of the 5 specified organs (Heart, Liver, Kidneys, Thyroid, Pancreas)
  - `suggested_anatomical_parts_to_examine`: Array of AT LEAST THREE specific anatomical parts that MUST be exact matches from the list above
  - `evidence_from_report`: Direct quote from the report supporting this extraction
  - `organ_category`: Always "specified"

**Examples of GOOD extraction (based on original text):**
1. Text: "patient has chest pain" → Extract: "chest pain" → Heart → ["Left Ventricle (LV)", "Aortic Valve", "Pericardium"]
2. Text: "elevated liver enzymes" → Extract: "elevated liver enzymes" → Liver → ["Left Lobe of Liver", "Right Lobe of Liver", "Hepatic Artery"]
3. Text: "thyroid nodule detected" → Extract: "thyroid nodule" → Thyroid → ["Right Lobe of Thyroid", "Left Lobe of Thyroid", "Isthmus of Thyroid"]

**Important Notes:**
- Stay close to the original medical report language
- Only extract symptoms clearly related to the 5 specified organs
- Ignore symptoms related to other organs
- Each symptom should be a separate JSON object

Extract all relevant symptom-organ relationships for the 5 specified organs from the following medical report:

"""
        return prompt

    @staticmethod
    def get_universal_inference_prompt() -> str:
        """
        Returns a universal extraction prompt that handles ALL organs by extracting from the original text.
        Emphasizes extraction over inference to stay close to the original diagnosis.
        """
        
        structure_string = ""
        for organ, parts in ORGAN_ANATOMY_STRUCTURE.items():
            structure_string += f"\n- {organ}:\n"
            structure_string += "  " + ", ".join(f'"{part}"' for part in parts) + "\n"

        prompt = f"""
You are a medical information extraction expert. Your task is to EXTRACT symptom-organ relationships directly from the given medical report text, staying as close as possible to the original diagnosis and descriptions.

**CORE PRINCIPLE: EXTRACT, DON'T INFER**
- Focus on symptoms and organs that are explicitly mentioned or clearly indicated in the text
- Avoid making medical inferences beyond what is stated in the report
- Each extracted item should have clear textual evidence from the report

**Step 1: Symptom Extraction**
Scan the report and extract ALL symptoms, conditions, or medical findings that are explicitly mentioned in the text. Look for:
- Direct symptom descriptions (e.g., "chest pain", "shortness of breath")
- Clinical findings (e.g., "hematocrit dropped", "blood pressure elevated")
- Diagnostic results (e.g., "ECG shows ST elevation", "CT reveals mass")
- Physical examination findings

**Step 2: Organ Identification**
For each extracted symptom, identify the most relevant organ based on:
- Organs explicitly mentioned in the text in relation to the symptom
- Medical context provided in the report (not general medical knowledge)
- Choose SPECIFIC ORGANS, not organ systems
- Valid examples: Heart, Lungs, Liver, Kidneys, Brain, Stomach, Skin, Spleen, etc.
- **STRICTLY FORBIDDEN**: Blood, Cardiovascular system, Respiratory system, Integumentary system, Immune system, etc.

**CRITICAL ORGAN MAPPING RULES:**
- For blood-related symptoms (hematocrit, hemoglobin, septicemia) → use "Liver"
- For skin conditions (cellulitis, rashes, ulcers) → use "Skin" 
- For breathing issues → use "Lungs"
- For circulation problems → use "Heart"
- NEVER use "Blood" as an organ name - always choose the organ that produces or processes blood components

**Step 3: Anatomical Structure Selection**

**For the following 5 SPECIFIED organs, you MUST choose EXACTLY from this list:**
{structure_string}

**For ALL OTHER organs, provide specific anatomical structures mentioned in the report or commonly associated with the symptom in medical practice, but ensure they are precise anatomical terms.**

**IMPORTANT: Choose anatomical structures that are MOST RELEVANT to the specific symptom, not generic structures. Consider:**
- For blood pressure issues → focus on ventricles, valves, and major vessels
- For ejection fraction → focus on ventricles and septum
- For valve problems → focus on the specific valve and adjacent chambers
- For urine/kidney issues → focus on cortex, medulla, pelvis based on the specific symptom
- For chest pain → consider coronary arteries, pericardium, or myocardium based on description

**Output Requirements:**
- Your final output must be a single, valid JSON array `[]`
- Each object represents ONE distinct symptom or finding from the report
- Each object must contain:
  - `symptom_or_disease`: Exact symptom/condition as described in the report
  - `inferred_organ`: Single most relevant specific organ (not organ system)
  - `suggested_anatomical_parts_to_examine`: Array of AT LEAST THREE specific anatomical parts
    * For specified organs (Heart, Liver, Kidneys, Thyroid, Pancreas): MUST be exact matches from above list
    * For other organs: Relevant anatomical structures based on the symptom and medical context
  - `evidence_from_report`: Direct quote from the report supporting this extraction
  - `organ_category`: "specified" or "other"

**Examples of GOOD extraction (based on original text):**
1. Text: "patient has chest pain" → Extract: "chest pain" → Heart → ["Left Ventricle (LV)", "Aortic Valve", "Pericardium"]
2. Text: "hematocrit dropped from 33 to 31.7" → Extract: "hematocrit dropped" → Liver → ["Hepatic Sinusoids", "Portal Circulation", "Hepatic Parenchyma"]
3. Text: "left groin hematoma" → Extract: "left groin hematoma" → Skin → ["Subcutaneous Tissue", "Dermis", "Superficial Fascia"]

**Important Notes:**
- Stay close to the original medical report language
- Don't over-interpret or add medical knowledge not present in the text
- Extract multiple separate entries if the report mentions multiple distinct symptoms
- Each symptom should be a separate JSON object

Extract all relevant symptom-organ relationships from the following medical report:

"""
        return prompt

def get_prompt_by_specialty(specialty: str) -> str:
    """根据专科类型获取对应的提示词"""
    prompts = {
        "cardiac": MedicalExtractionPrompts.get_specialized_cardiac_prompt,
        "pulmonary": MedicalExtractionPrompts.get_specialized_pulmonary_prompt,
        "liver": MedicalExtractionPrompts.get_specialized_liver_prompt,
        "thyroid": MedicalExtractionPrompts.get_specialized_thyroid_prompt,
        "general": MedicalExtractionPrompts.get_primary_extraction_prompt
    }
    
    return prompts.get(specialty, MedicalExtractionPrompts.get_primary_extraction_prompt)()

def create_extraction_pipeline() -> Dict[str, str]:
    """创建完整的提取流程提示词"""
    return {
        "primary": MedicalExtractionPrompts.get_primary_extraction_prompt(),
        "cardiac": MedicalExtractionPrompts.get_specialized_cardiac_prompt(),
        "pulmonary": MedicalExtractionPrompts.get_specialized_pulmonary_prompt(),
        "liver": MedicalExtractionPrompts.get_specialized_liver_prompt(),
        "thyroid": MedicalExtractionPrompts.get_specialized_thyroid_prompt(),
        "validation": MedicalExtractionPrompts.get_validation_prompt(),
        "batch": MedicalExtractionPrompts.get_batch_processing_prompt()
    }

# Allowed organs are now the keys of the new structure
ALLOWED_ORGANS = list(ORGAN_ANATOMY_STRUCTURE.keys())

if __name__ == "__main__":
    # 测试提示词系统
    print("医学提取提示词系统测试")
    print("=" * 50)
    
    # 测试各专科提示词
    specialties = ["cardiac", "pulmonary", "liver", "thyroid", "general"]
    
    for specialty in specialties:
        prompt = get_prompt_by_specialty(specialty)
        print(f"\n{specialty.upper()} 提示词长度: {len(prompt)} 字符")
        print(f"前100字符: {prompt[:100]}...")
    
    # 测试完整流程
    pipeline = create_extraction_pipeline()
    print(f"\n完整流程包含 {len(pipeline)} 个提示词")
    
    for stage, prompt in pipeline.items():
        print(f"  {stage}: {len(prompt)} 字符") 