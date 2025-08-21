import argparse
import json
import asyncio
from pathlib import Path
from datetime import datetime
import sys
import os

# No longer need to modify path since we run as a module
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Use relative imports because this script is run as a module inside a package
from .llm_service import LLMService, load_llm_configs
from ..rag_system.api.main import RAGService as MainRAGService # Rename to avoid conflict

# --- Prompts ---

# This new prompt emphasizes the use of retrieved context for the RAG system.
SYSTEM_PROMPT_RAG = """You are an expert radiologist. Your task is to analyze a clinical query based **strictly on the provided context** and determine the organ and structures to examine.

--- Retrieved Knowledge ---
{context_docs}
--- End Retrieved Knowledge ---

You MUST follow these rules:
1.  **Your entire analysis MUST be derived from the information within the "Retrieved Knowledge" section.** Do not use your general knowledge.
2.  The retrieved knowledge is ranked by relevance. **You MUST prioritize information from documents with a higher rank (e.g., Rank 1 over Rank 2).**
3.  Your primary goal is to synthesize the retrieved texts. If the context mentions specific symptoms linked to an organ, use that as your primary evidence.
4.  First, provide a "Symptom Analysis" that summarizes the key findings from the retrieved knowledge.
5.  Second, identify the primary "Organ" to be examined.
6.  Third, list the specific "Anatomical Structures" that require examination, ensuring they are mentioned or strongly implied by the context.
7.  Your final output MUST be a single JSON object with three keys: "Symptom Analysis", "Organ", and "Anatomical Structures". The value for "Anatomical Structures" must be a list of strings.
"""

SYSTEM_PROMPT_DIRECT = """You are an expert radiologist. Your task is to analyze a clinical query and determine which organ and specific anatomical structures should be examined.

You MUST follow these rules:
1.  First, provide a brief "Symptom Analysis".
2.  Second, identify the primary "Organ" to be examined from the keys in the provided JSON structure.
3.  Third, from the list of anatomical structures corresponding to that organ in the JSON, select the specific "Anatomical Structures" that require examination.
4.  Your final output MUST be a single JSON object with three keys: "Symptom Analysis", "Organ", and "Anatomical Structures". The value for "Anatomical Structures" must be a list of strings.
5.  The organ and structure names you choose MUST EXACTLY match the names provided in the JSON structure below. Do not invent new names or use synonyms.

Here is the authoritative list of organs and their anatomical structures:
{organ_structures}
"""

def get_organ_structures():
    # In a real app, this might come from a config file or a database.
    return {
      "Heart": ["Aortic Valve", "Mitral Valve", "Tricuspid Valve", "Pulmonary Valve", "Left Ventricle (LV)", "Right Ventricle (RV)", "Left Atrium (LA)", "Right Atrium (RA)", "Interventricular Septum (IVS)", "Interatrial Septum (IAS)", "Left Ventricular Posterior Wall (LVPW)", "Papillary Muscles", "Chordae Tendineae", "Aortic Root & Ascending Aorta", "Main Pulmonary Artery (MPA)", "Pericardium"],
      "Liver": ["Left Lobe of Liver", "Right Lobe of Liver", "Caudate Lobe of Liver", "Portal Vein (Main, Left, and Right branches)", "Hepatic Veins (Left, Middle, and Right)", "Hepatic Artery", "Intrahepatic Bile Ducts", "Common Bile Duct (CBD)", "Gallbladder (Fundus, Body, Neck)", "Gallbladder Wall", "Spleen", "Morison's Pouch (Hepatorenal Recess)"],
      "Kidneys": ["Renal Cortex", "Renal Medulla (Pyramids)", "Renal Pelvis", "Renal Calyces (Major & Minor)", "Ureters (Proximal part)", "Urinary Bladder Wall", "Trigone of the Bladder", "Prostate Gland (in males)", "Seminal Vesicles (in males)"],
      "Thyroid": ["Right Lobe of Thyroid", "Left Lobe of Thyroid", "Isthmus of Thyroid", "Common Carotid Artery", "Internal Jugular Vein", "Trachea", "Esophagus", "Strap Muscles", "Sternocleidomastoid Muscle", "Cervical Lymph Node Chains"],
      "Pancreas": ["Head of the Pancreas", "Uncinate Process", "Neck of the Pancreas", "Body of the Pancreas", "Tail of the Pancreas", "Main Pancreatic Duct (Duct of Wirsung)", "Splenic Vein", "Superior Mesenteric Artery (SMA)", "Superior Mesenteric Vein (SMV)", "Common Bile Duct (Distal part)"]
    }

def clean_and_parse_json(text_blob: str):
    """Safely cleans and parses a JSON string that might be embedded in markdown."""
    if not isinstance(text_blob, str):
        return None
    
    # Remove markdown fences
    if text_blob.strip().startswith("```json"):
        text_blob = text_blob.strip()[7:]
    if text_blob.strip().startswith("```"):
        text_blob = text_blob.strip()[3:]
    if text_blob.strip().endswith("```"):
        text_blob = text_blob.strip()[:-3]
        
    start = text_blob.find('{')
    end = text_blob.rfind('}') + 1
    
    if start == -1 or end == 0:
        return None
        
    json_str = text_blob[start:end]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None

def calculate_score(rag_structures, llm_structures):
    """Calculates the score for an LLM based on the RAG ground truth."""
    if not rag_structures or not llm_structures:
        return 0, "N/A (Missing data for scoring)"

    score_map = {}
    total_possible_score = 0
    # Create the score map based on the RAG results: 3, 2, 1
    point_values = [3, 2, 1] + [1] * (len(rag_structures) - 3) # Handle cases with more than 3 results
    for i, structure in enumerate(rag_structures):
        points = point_values[i] if i < len(point_values) else 1
        score_map[structure] = points
        total_possible_score += points

    achieved_score = 0
    for structure in llm_structures:
        if structure in score_map:
            achieved_score += score_map[structure]
            
    return achieved_score, f"{achieved_score}/{total_possible_score}"


async def run_evaluation(question: str, output_dir: Path, question_file_path: Path):
    """
    Runs the full evaluation pipeline: RAG, Direct LLMs, Scoring, and Output generation.
    """
    # 1. Initialize services
    rag_service = MainRAGService() # Use the imported and renamed RAGService
    llm_configs = load_llm_configs()
    llm_services = [LLMService(config) for config in llm_configs]
    
    # 2. Run RAG query
    print("Querying RAG system...")
    rag_result_raw = rag_service.answer_query(query=question, custom_qa_prompt_template=SYSTEM_PROMPT_RAG)
    print("RAG system query complete.")

    # 3. Run direct LLM queries
    print(f"Querying {len(llm_services)} direct LLMs...")
    organ_structures_str = json.dumps(get_organ_structures(), indent=2)
    direct_prompt = SYSTEM_PROMPT_DIRECT.format(organ_structures=organ_structures_str)
    
    tasks = [service.get_response(direct_prompt, question) for service in llm_services]
    # 使用 return_exceptions=True 来防止一个任务失败导致整个 gather 失败
    direct_llm_results_raw = await asyncio.gather(*tasks, return_exceptions=True)
    print("Direct LLM queries complete.")

    # 4. Consolidate into a full report
    full_report = {
        "question": question,
        "rag_result": rag_result_raw,
        "direct_llm_results": direct_llm_results_raw,
        "evaluation_timestamp": datetime.now().isoformat()
    }
    
    # 5. Create summary and scores
    summary_report = {}
    
    # Parse RAG result for ground truth and summary
    rag_answer_json = clean_and_parse_json(rag_result_raw.get("answer"))
    rag_structures = []
    if rag_answer_json:
        rag_structures = rag_answer_json.get("Anatomical Structures", [])
        summary_report["rag_system"] = {
            "symptom_analysis": rag_answer_json.get("Symptom Analysis", ""),
            "recommended_structures": rag_structures
        }
    else:
        summary_report["rag_system"] = {"error": "Could not parse RAG response."}

    # Parse LLM results for summary and scoring
    llm_comparison = {}
    for result in direct_llm_results_raw:
        api_name = result.get("api_name", "unknown_api")
        
        # 检查 gather 是否返回了异常
        if isinstance(result, Exception):
            print(f"An exception occurred for {api_name}: {result}")
            llm_comparison[api_name] = {"error": f"An exception occurred: {result}"}
            continue

        llm_answer_json = clean_and_parse_json(result.get("answer"))
        
        if llm_answer_json:
            llm_structures = llm_answer_json.get("Anatomical Structures", [])
            score, score_str = calculate_score(rag_structures, llm_structures)
            llm_comparison[api_name] = {
                "symptom_analysis": llm_answer_json.get("Symptom Analysis", ""),
                "recommended_structures": llm_structures,
                "score_points": score,
                "score_str": score_str
            }
        else:
            llm_comparison[api_name] = {"error": "Could not parse LLM response."}
            
    summary_report["direct_llm_comparison"] = llm_comparison
    
    # 6. Write files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_report_path = output_dir / f"{timestamp}_full_report.json"
    summary_report_path = output_dir / f"{timestamp}_summary_and_scores.json"
    
    with open(full_report_path, 'w', encoding='utf-8') as f:
        json.dump(full_report, f, indent=2, ensure_ascii=False)
    print(f"Full report saved to: {full_report_path}")

    with open(summary_report_path, 'w', encoding='utf-8') as f:
        json.dump(summary_report, f, indent=2, ensure_ascii=False)
    print(f"Summary and scores saved to: {summary_report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a full RAG vs. LLM evaluation.")
    # The default path is now relative to the script's new location
    parser.add_argument(
        "--question_file", 
        type=str, 
        default="question.json",
        help="Path to the JSON file containing the question, relative to the script."
    )
    parser.add_argument(
        "--output_dir", 
        type=str, 
        default="../../RAG_output", # Navigate up to root, then to RAG_output
        help="Directory to save the output reports."
    )
    args = parser.parse_args()

    # Get the directory where the script is located
    script_dir = Path(__file__).parent
    
    # Resolve paths relative to the project root or script location
    question_path = script_dir / args.question_file
    output_path = script_dir / args.output_dir
    
    # Ensure output directory exists by resolving the path cleanly
    output_path.mkdir(parents=True, exist_ok=True)


    # Load question
    if not question_path.exists():
        print(f"Error: Question file not found at {question_path}")
        sys.exit(1)
        
    with open(question_path, 'r', encoding='utf-8') as f:
        question_data = json.load(f)
        main_question = question_data.get("question")

    if not main_question:
        print(f"Error: 'question' key not found in {question_path}")
        sys.exit(1)

    asyncio.run(run_evaluation(main_question, output_path, question_path)) 