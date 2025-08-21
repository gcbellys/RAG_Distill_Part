#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断蒸馏提示词系统 (Diag_Distillation)
用于从医学文本中分步提取主诉症状、诊断器官和解剖部位的对应关系
"""

import json
from typing import List, Dict, Any

# Import the definitive source of truth for organ structures
from configs.model_config import ORGAN_ANATOMY_STRUCTURE

class DiagnosticExtractionPrompts:
    """诊断蒸馏提示词系统"""
    
    @staticmethod
    def get_step1_comprehensive_descriptive_extraction_prompt(text_content: str) -> str:
        """
        Step 1: Comprehensive descriptive content extraction (symptoms, exam findings, clinical signs) — English only
        """
        return f"""
You are a medical text analysis expert. Your task is to extract ALL DESCRIPTIVE CONTENT from medical reports, including patient symptoms, examination findings, laboratory/test measurements, and clinical signs, while STRICTLY EXCLUDING diagnostic judgments.

EXPANDED DEFINITION AND FULL-DOCUMENT SWEEP:
1) Expanded definition of a valid symptom/sign:
   - Not only patient-reported complaints, but also objective clinical signs observed and recorded by clinicians in any section of the note.
2) Full-document sweep (consider ALL sections):
   - Chief Complaint, History of Present Illness, Physical Examination, Hospital Course, Treatment Plan, Discharge Diagnosis, and any other narrative sections.
3) Neonatal/pediatric emphasis examples (do extract when present):
   - "grunting, flaring, and retracting"; "decreased aeration"; "oxygen saturation 88–90%".

EXTRACT THESE (descriptive content):

1. Patient Symptoms (subjective)
   - Complaints: pain, discomfort, nausea, dizziness, fatigue
   - Functional limitations: shortness of breath, difficulty swallowing
   - Sensory changes: vision problems, hearing loss, numbness
   - Neonatal/peds examples: grunting, flaring, retracting, cyanosis, apnea

2. Examination Findings (objective)
   - Physical examination results: enlarged organs, masses, swelling
   - Vital signs: blood pressure, heart rate, temperature, oxygen saturation
   - Auscultation findings: murmurs, rales, breath sounds, decreased aeration
   - Palpation findings: tenderness, masses, organ enlargement
   - Respiratory examples: decreased breath sounds, wheezing, stridor, chest retractions

3. Laboratory/Test Results (objective measurements only)
   - Blood tests: counts and values (e.g., bilirubin levels)
   - Imaging observations: X-ray, CT, MRI, ultrasound (descriptive observations only)
   - Function tests: ECG changes, spirometry results
   - Pathology/biopsy (descriptive tissue characteristics only)

4. Clinical Signs (observable)
   - Jaundice, cyanosis, edema, pallor
   - Neurologic signs: reflexes, muscle strength, coordination
   - Skin changes: rashes, lesions, color changes
   - Neonatal specifics: gestational age markers, Apgar scores, birth weight

STRICTLY EXCLUDE (diagnostic/judgmental content):
- Diagnostic conclusions and disease labels (e.g., "hyaline membrane disease", "pneumonia", "myocardial infarction", "hypertension", "prematurity")
- Medical judgments and impressions (e.g., "consistent with", "suggestive of", differential diagnoses)
- Treatment plans (medications, surgeries, therapies)

EXTRACTION PRINCIPLES:
1) Descriptive vs Diagnostic
   - ✅ "oxygen saturation 88–90% on 100% blow-by O2" (descriptive measurement)
   - ❌ "hypoxemia" (diagnostic interpretation)
   - ✅ "decreased aeration to the bases" (descriptive finding)
   - ❌ "pneumonia" (diagnostic conclusion)

2) Full-document scan
   - Carefully read ALL sections, including lists and narrative text
   - Capture measurements, locations, and objective observations

3) Exact text preservation
   - Use exact language from the source
   - Include measurements, locations, qualifiers when present

TASK: Extract all descriptive content from the following medical text:

{text_content}

OUTPUT FORMAT:
Return a JSON object exactly like this:
{{
    "descriptive_findings": [
        {{
            "finding_text": "exact descriptive text from original",
            "finding_type": "patient_symptom|examination_finding|lab_result|clinical_sign",
            "source_quote": "exact sentence/phrase from text",
            "body_system": "cardiovascular|respiratory|gastrointestinal|neurological|genitourinary|musculoskeletal|endocrine|neonatal|other",
            "extraction_confidence": "high|medium|low"
        }}
    ],
    "excluded_content": [
        {{
            "excluded_text": "diagnostic/judgmental content that was excluded",
            "exclusion_reason": "disease_name|diagnostic_conclusion|medical_judgment|treatment_plan",
            "source_quote": "exact sentence where this was found"
        }}
    ],
    "extraction_summary": {{
        "total_findings": "number of descriptive findings extracted",
        "findings_by_type": {{
            "patient_symptoms": "count",
            "examination_findings": "count",
            "lab_results": "count",
            "clinical_signs": "count"
        }},
        "excluded_items": "number of diagnostic items excluded"
    }}
}}

ENHANCED EXAMPLES (including neonatal/pediatric):
- "grunting, flaring and retracting noted in the delivery room"
- "decreased aeration to the bases"
- "oxygen saturation 88–90% on blow-by oxygen"
- "Apgar 8 at 1 minute and 8 at 5 minutes"
- "initial bilirubin 4.4/0.3 on day of life #1"
- "white count 15.6, hematocrit 41.6, platelets 413,000"

PRIORITY: Comprehensive extraction of descriptive content while strictly excluding diagnostic judgments.
"""

    @staticmethod 
    def get_step2_diagnosis_organ_extraction_prompt(text_content: str) -> str:
        """
        第二步：从医生建议或诊断中提取器官信息
        """
        return """
You are a medical text analysis expert. Your task is to extract ORGAN information from physician diagnoses, recommendations, or medical assessments.

**STEP 2: ORGAN EXTRACTION FROM MEDICAL DIAGNOSES**

**Task**: Analyze medical text to identify sections containing physician diagnoses, medical assessments, or recommendations, then extract organ information mentioned in these sections.

**Instructions**:
1. **Identify Diagnostic Sections**: Look for sections containing:
   - Medical diagnoses
   - Assessment and plan
   - Physician recommendations
   - Medical conclusions
   - Diagnostic impressions
   - Treatment plans

2. **Extract Organ Information**: From diagnostic sections, extract:
   - Organs explicitly mentioned by physicians
   - Organs implied in diagnostic statements
   - Organs referenced in treatment plans
   - Body systems under medical evaluation

**Section Types to Focus On**:
- "Assessment and Plan"
- "Impression"
- "Diagnosis"
- "Medical Assessment"
- "Recommendations"
- "Plan"
- "Physician Notes"
- "Discharge Diagnosis"

**IMPORTANT: Use Standard Medical Terminology**
You MUST use ONLY the following standard organ names in your output:
- Brain, Cerebellum, Brainstem, Diencephalon, Spinal cord (Medulla spinalis)
- Heart (Cor), Artery (Arteria), Vena (Vena), Capillary (Vas capillare)
- Nose (Nasus), Pharynx, Larynx, Trachea, Bronchus, Lung (Pulmo)
- Mouth (Oral cavity), Tongue (Lingua), Teeth (Dentes), Salivary glands
- Esophagus, Stomach (Gaster), Small intestine (Intestinum tenue), Large intestine (Intestinum crassum)
- Liver (Hepar), Gallbladder (Vesica biliaris), Pancreas, Mesentery
- Kidney (Ren), Ureter, Urinary bladder (Vesica urinaria), Urethra
- Testis, Epididymis, Prostate, Penis
- Ovary (Ovarium), Uterine tube (Tuba uterina), Uterus, Vagina, Vulva, Placenta
- Pituitary gland (Hypophysis), Pineal gland, Thyroid gland, Parathyroid gland, Adrenal gland (Suprarenal gland)
- Thymus, Lymph node, Spleen (Lien), Tonsil (Tonsilla), Bone marrow (Medulla ossium)
- Eye (Oculus), Ear (Auris), Skin (Cutis), Mammary gland

**Output Format**:
Return a JSON object with the following structure:
{{
    "diagnostic_sections": [
        {{
            "section_type": "type of diagnostic section",
            "original_text": "exact text from the diagnostic section",
            "mentioned_organs": [
                {{
                    "organ_name": "standard organ name from the list above",
                    "context": "how the organ was mentioned in diagnosis",
                    "supporting_text": "exact phrase mentioning the organ"
                }}
            ]
        }}
    ],
    "all_organs_identified": ["list of all unique standard organ names found in diagnoses"]
}}

**Organ Extraction Rules**:
- Extract organs ONLY from physician diagnoses/assessments, not patient complaints
- Use exact medical terminology from the original text
- Include both directly named organs and those implied in medical terms
- Focus on organs that are the subject of medical evaluation or treatment
- ALWAYS map to the standard organ names listed above

**Important Guidelines**:
- ONLY extract from diagnostic/assessment sections, NOT patient complaint sections
- Must come directly from original text - no inference
- Include the exact context where each organ was mentioned
- If no diagnostic sections mention organs, return empty arrays
- Use ONLY the standard organ names provided above

**Example**:
If diagnostic text contains: "Assessment: Acute myocardial infarction. Plan: Cardiac catheterization to evaluate coronary arteries..."

Extract:
- mentioned_organs: [{{"organ_name": "Heart (Cor)", "context": "myocardial infarction", "supporting_text": "Acute myocardial infarction"}}]

Extract organ information from physician diagnoses in the following medical report:

{text_content}
"""

    @staticmethod
    def get_step3_anatomical_mapping_prompt(patient_symptoms, diagnosed_organs, original_text) -> str:
        """
        第三步：基于症状和器官确定具体解剖部位
        """
        # Import ELSE_STRUCT for additional organs
        from configs.model_config import ORGAN_ANATOMY_STRUCTURE, ELSE_STRUCT
        
        structure_string = ""
        # Add main organs from ORGAN_ANATOMY_STRUCTURE
        for organ, parts in ORGAN_ANATOMY_STRUCTURE.items():
            structure_string += f"\n- {organ}:\n"
            structure_string += "  " + ", ".join(f'"{part}"' for part in parts) + "\n"
        
        # Add other organs from ELSE_STRUCT
        for organ, parts in ELSE_STRUCT.items():
            structure_string += f"\n- {organ}:\n"
            structure_string += "  " + ", ".join(f'"{part}"' for part in parts) + "\n"

        prompt = """
You are a medical anatomy expert. Your task is to map identified symptoms and diagnosed organs to specific anatomical locations.

**STEP 3: ANATOMICAL LOCATION MAPPING**

**Task**: Based on the patient symptoms and physician-diagnosed organs, determine the specific anatomical parts that should be examined, using ONLY the original text as reference.

**Instructions**:
1. **Receive Input**: You will receive:
   - Patient's main symptoms (from Step 1)
   - Physician-diagnosed organs (from Step 2)
   - Original medical text for reference

2. **Map to Anatomical Locations**: For each symptom-organ combination:
   - Identify specific anatomical parts mentioned in the original text
   - If specific parts are not mentioned, select the most relevant anatomical structures based on the symptom description
   - Use only predefined anatomical structures for organs listed in the reference

**IMPORTANT: Use Standard Medical Terminology**
All organ names must be from the standard list:
- Brain, Cerebellum, Brainstem, Diencephalon, Spinal cord (Medulla spinalis)
- Heart (Cor), Artery (Arteria), Vena (Vena), Capillary (Vas capillare)
- Nose (Nasus), Pharynx, Larynx, Trachea, Bronchus, Lung (Pulmo)
- Mouth (Oral cavity), Tongue (Lingua), Teeth (Dentes), Salivary glands
- Esophagus, Stomach (Gaster), Small intestine (Intestinum tenue), Large intestine (Intestinum crassum)
- Liver (Hepar), Gallbladder (Vesica biliaris), Pancreas, Mesentery
- Kidney (Ren), Ureter, Urinary bladder (Vesica urinaria), Urethra
- Testis, Epididymis, Prostate, Penis
- Ovary (Ovarium), Uterine tube (Tuba uterina), Uterus, Vagina, Vulva, Placenta
- Pituitary gland (Hypophysis), Pineal gland, Thyroid gland, Parathyroid gland, Adrenal gland (Suprarenal gland)
- Thymus, Lymph node, Spleen (Lien), Tonsil (Tonsilla), Bone marrow (Medulla ossium)
- Eye (Oculus), Ear (Auris), Skin (Cutis), Mammary gland

**Anatomical Structure Reference**:
For the following organs, you MUST choose from these exact anatomical structures:
STRUCTURE_PLACEHOLDER

**For other organs**: Use anatomical terms mentioned in the original text or standard medical anatomical terminology.

**Output Format**:
Return a JSON object with the following structure:
{{
    "symptom_organ_mappings": [
        {{
            "patient_symptom": "main symptom from patient complaint",
            "diagnosed_organ": "standard organ name from the list above", 
            "anatomical_locations": [
                "specific anatomical part 1",
                "specific anatomical part 2", 
                "specific anatomical part 3"
            ],
            "text_evidence": {{
                "symptom_source": "exact text where symptom was described",
                "organ_source": "exact text where organ was diagnosed",
                "anatomical_basis": "reasoning for anatomical location selection based on original text"
            }},
            "confidence": "high/medium/low"
        }}
    ]
}}

**Mapping Rules**:
1. **Text-Based Priority**: If specific anatomical parts are mentioned in the original text, use those first
2. **Symptom Relevance**: Choose anatomical structures most relevant to the specific symptom
3. **Medical Accuracy**: Ensure anatomical selections are medically appropriate for the symptom-organ combination
4. **Evidence Required**: Every mapping must have supporting evidence from the original text
5. **Standard Terminology**: Use ONLY the standard organ names provided above

**Important Guidelines**:
- Base all mappings on information from the original medical text
- Each symptom-organ pair should have at least 2 anatomical locations
- Provide clear text evidence for each mapping decision
- If anatomical parts are explicitly mentioned in text, prioritize those
- Confidence should reflect how clearly the mapping is supported by the original text
- Use ONLY the standard organ names listed above

**Example**:
Patient Symptom: "chest pain radiating to left arm"
Diagnosed Organ: "Heart (Cor)" (from "myocardial infarction")
Anatomical Locations: ["Left Ventricle (LV)", "Aortic Valve", "Left Ventricular Posterior Wall (LVPW)"]

Map symptoms to anatomical locations using the following information:

**Patient Symptoms**: PATIENT_SYMPTOMS_PLACEHOLDER
**Diagnosed Organs**: DIAGNOSED_ORGANS_PLACEHOLDER
**Original Medical Text**: ORIGINAL_TEXT_PLACEHOLDER

"""
        
        # 替换占位符
        prompt = prompt.replace("STRUCTURE_PLACEHOLDER", structure_string)
        prompt = prompt.replace("PATIENT_SYMPTOMS_PLACEHOLDER", str(patient_symptoms))
        prompt = prompt.replace("DIAGNOSED_ORGANS_PLACEHOLDER", str(diagnosed_organs))
        prompt = prompt.replace("ORIGINAL_TEXT_PLACEHOLDER", original_text[:2000] + "..." if len(original_text) > 2000 else original_text)
        
        return prompt

    @staticmethod
    def get_integrated_diagnostic_prompt(text_content: str) -> str:
        """
        Integrated diagnostic distillation prompt — English only, with chief symptom inference
        """
        # Import ELSE_STRUCT for additional organs
        from configs.model_config import ORGAN_ANATOMY_STRUCTURE, ELSE_STRUCT
        
        structure_string = ""
        for organ, parts in ORGAN_ANATOMY_STRUCTURE.items():
            structure_string += f"\n- {organ}:\n"
            structure_string += "  " + ", ".join(f'"{part}"' for part in parts) + "\n"
        for organ, parts in ELSE_STRUCT.items():
            structure_string += f"\n- {organ}:\n"
            structure_string += "  " + ", ".join(f'"{part}"' for part in parts) + "\n"
        
        prompt = f"""
You are a medical text analysis expert specializing in diagnostic information extraction. Perform a comprehensive, single-pass analysis and output results in a strict JSON format.

CHIEF SYMPTOM INFERENCE (TOP PRIORITY):
1) Before mapping anything, infer the dominant clinical problem of this report.
2) Synthesize across the whole document: objective signs (e.g., "grunting, flaring"), key diagnoses (e.g., "hyaline membrane disease"), and core interventions (e.g., "intubated and received surfactant").
3) Name the dominant clinical symptom/sign that best captures the core problem, and use it as the value of the s_symptom field in the final output.
4) Example (neonatal): Given "grunting, flaring", a diagnosis of "hyaline membrane disease", and surfactant use, infer the dominant symptom/sign as "respiratory distress in newborn".

CRITICAL DISTINCTION: Symptom vs. Diagnosis for s_symptom
- Symptom/Sign (for s_symptom): what the patient experiences or what is objectively observed (e.g., "chest pain", "shortness of breath", "coffee-ground emesis", "grunting and retracting", "respiratory distress in newborn").
- Diagnosis (for d_diagnosis): the medical label explaining the symptom (e.g., "myocardial infarction", "pneumonia", "hyaline membrane disease").

STANDARD ORGAN TERMINOLOGY (whitelist only):
- Brain, Cerebellum, Brainstem, Diencephalon, Spinal cord (Medulla spinalis)
- Heart (Cor), Artery (Arteria), Vena (Vena), Capillary (Vas capillare)
- Nose (Nasus), Pharynx, Larynx, Trachea, Bronchus, Lung (Pulmo)
- Mouth (Oral cavity), Tongue (Lingua), Teeth (Dentes), Salivary glands
- Esophagus, Stomach (Gaster), Small intestine (Intestinum tenue), Large intestine (Intestinum crassum)
- Liver (Hepar), Gallbladder (Vesica biliaris), Pancreas, Mesentery
- Kidney (Ren), Ureter, Urinary bladder (Vesica urinaria), Urethra
- Testis, Epididymis, Prostate, Penis
- Ovary (Ovarium), Uterine tube (Tuba uterina), Uterus, Vagina, Vulva, Placenta
- Pituitary gland (Hypophysis), Pineal gland, Thyroid gland, Parathyroid gland, Adrenal gland (Suprarenal gland)
- Thymus, Lymph node, Spleen (Lien), Tonsil (Tonsilla), Bone marrow (Medulla ossium)
- Eye (Oculus), Ear (Auris), Skin (Cutis), Mammary gland

ANATOMICAL STRUCTURE REFERENCE (use only these exact structures for organs):
{structure_string}

OUTPUT FORMAT REQUIREMENTS:
Return a JSON array of objects in the form:
[
  {{
    "s_symptom": "A specific single symptom/sign inferred from and supported by the text",
    "U_unit_set": [
      {{
        "u_unit": {{
          "d_diagnosis": "A physician's diagnosis from the text",
          "o_organ": {{
            "organName": "Standard organ name from whitelist",
            "anatomicalLocations": [
              "Specific anatomical location (from predefined structures)",
              "..."
            ]
          }},
          "b_textual_basis": {{
            "doctorsDiagnosisAndJudgment": "Quoted diagnostic/judgmental text from the source",
            "medicalInference": "Your concise explanation of the symptom-diagnosis-organ linkage"
          }}
        }}
      }}
    ]
  }}
]

RULES:
1) Forced Association Principle: Only create a u_unit when the text explicitly links a symptom/sign with a physician diagnosis. If no clear link exists, do not fabricate associations.
2) Text Fidelity: All quoted content must be copied verbatim from the source.
3) Symptom Specificity: s_symptom must be a symptom/sign, not a disease label.
4) Anatomical Locations: At least 2 locations; use predefined structures for the selected organ.
5) Dominant Symptom Inference: If the report is disorganized and explicit symptoms are sparse, infer a dominant symptom/sign that best captures the clinical picture (e.g., "respiratory distress in newborn"), grounded in the provided text.

Analyze the following medical text and produce the output:

{text_content}
"""
        
        return prompt

def get_prompt_by_step(step: int) -> str:
    """根据步骤获取对应的提示词"""
    prompts = {
        1: DiagnosticExtractionPrompts.get_step1_comprehensive_descriptive_extraction_prompt,
        2: DiagnosticExtractionPrompts.get_step2_diagnosis_organ_extraction_prompt, 
        3: DiagnosticExtractionPrompts.get_step3_anatomical_mapping_prompt,
        "integrated": DiagnosticExtractionPrompts.get_integrated_diagnostic_prompt
    }
    
    if step in prompts:
        return prompts[step]()
    else:
        return DiagnosticExtractionPrompts.get_integrated_diagnostic_prompt()

def create_diagnostic_pipeline() -> Dict[str, str]:
    """创建完整的诊断提取流程提示词"""
    return {
        "step1_complaints": DiagnosticExtractionPrompts.get_step1_comprehensive_descriptive_extraction_prompt(),
        "step2_diagnoses": DiagnosticExtractionPrompts.get_step2_diagnosis_organ_extraction_prompt(),
        "step3_anatomical": DiagnosticExtractionPrompts.get_step3_anatomical_mapping_prompt(),
        "integrated": DiagnosticExtractionPrompts.get_integrated_diagnostic_prompt()
    }

# 保留原有类以维持兼容性，但标记为废弃
class MedicalExtractionPrompts:
    """医学信息抽取提示词系统 (已废弃，请使用DiagnosticExtractionPrompts)"""
    
    @staticmethod
    def get_universal_inference_prompt() -> str:
        """兼容性方法 - 重定向到新的整合提示词"""
        return DiagnosticExtractionPrompts.get_integrated_diagnostic_prompt()
    
    @staticmethod
    def get_inference_prompt() -> str:
        """兼容性方法 - 重定向到新的整合提示词"""
        return DiagnosticExtractionPrompts.get_integrated_diagnostic_prompt()

if __name__ == "__main__":
    # 测试新的诊断提示词系统
    print("诊断蒸馏提示词系统测试")
    print("=" * 50)
    
    # 测试各步骤提示词
    steps = [1, 2, 3, "integrated"]
    
    for step in steps:
        prompt = get_prompt_by_step(step)
        print(f"\n步骤 {step} 提示词长度: {len(prompt)} 字符")
        print(f"前100字符: {prompt[:100]}...")
    
    # 测试完整流程
    pipeline = create_diagnostic_pipeline()
    print(f"\n完整诊断流程包含 {len(pipeline)} 个提示词")
    
    for stage, prompt in pipeline.items():
        print(f"  {stage}: {len(prompt)} 字符") 