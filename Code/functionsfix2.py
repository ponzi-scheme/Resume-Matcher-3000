import pdfplumber
import spacy
import os
import json
import heapq
import re
import warnings

#1. SETUP & AUTH

# FIX: We filter warnings BEFORE importing the Google library
# This silences the "FutureWarning"
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# NOW we import the library
import google.generativeai as genai

# Configure Google Gemini
api_key = os.getenv("GOOGLE_API_KEY", "ENTER THE API KEY HERE")
genai.configure(api_key=api_key)

# Load Spacy
nlp = spacy.load('en_core_web_lg')
config = {"overwrite_ents": True}
ruler = nlp.add_pipe("entity_ruler", after="ner", config=config)

# Load Patterns
script_dir = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(script_dir)
files_to_load = [
    "Skills.jsonl", "Education_DegreesOnly.jsonl", "Education_Relaxed.jsonl",
    "Experience_Skills_Relaxed.jsonl", "KnowledgeTraining_Abilities_Relaxed.jsonl",
    "Education_Broad.jsonl", "Education.jsonl"
]

for file in files_to_load:
    filePath = os.path.join(root, "Documents", file)
    if os.path.exists(filePath):
        try:
            with open(filePath, "r", encoding="utf-8") as f:
                try:
                    patterns = json.load(f)
                except:
                    f.seek(0)
                    patterns = [json.loads(line) for line in f if line.strip()]
            ruler.add_patterns(patterns)
        except:
            pass


#2. CORE FUNCTIONS

def convertPdfToText(pdfPath, outPath):
    with pdfplumber.open(pdfPath) as pdf, open(outPath, 'w', encoding="utf-8") as f:
        for page in pdf.pages:
            t = page.extract_text()
            if t: f.write(t + "\n")
    return outPath


def resumeFileParser(inFilePth, outFilePath):
    """
    Parses a single resume PDF.
    UPDATED: Returns both the Entities List AND the Raw Text for fallback matching.
    """
    resumeList = [[], [], [], [], [], []]
    tempfile = convertPdfToText(inFilePth, outFilePath)

    raw_text_content = ""

    with open(tempfile, 'r', encoding='utf-8') as f:
        text_content = f.read()
        # Save lowercase version for easy searching later
        raw_text_content = text_content.lower()

        if len(text_content) > 1000000:
            nlp.max_length = len(text_content) + 100
        doc = nlp(text_content)

    for item in doc.ents:
        val = item.text.strip()
        if item.label_ == "SKILL" and val.lower() not in resumeList[0]:
            resumeList[0].append(val.lower())
        elif item.label_ == "KNOWLEDGE" and val.lower() not in resumeList[1]:
            resumeList[1].append(val.lower())
        elif item.label_ == "ABILITY" and val.lower() not in resumeList[2]:
            resumeList[2].append(val.lower())
        elif item.label_ == "EDUCATION" and val.lower() not in resumeList[3]:
            resumeList[3].append(val.lower())
        elif item.label_ == "EXPERIENCE" and val.lower() not in resumeList[4]:
            resumeList[4].append(val.lower())
        elif item.label_ == "TRAINING" and val.lower() not in resumeList[5]:
            resumeList[5].append(val.lower())

    if os.path.exists(tempfile):
        os.remove(tempfile)

    # UPDATED RETURN: Now returns a Tuple (List, String)
    return resumeList, raw_text_content


def jFileParser(inFilePth):
    jList = [[], [], [], [], [], []]
    with open(inFilePth, 'r', encoding='utf-8') as f:
        text_content = f.read()
        doc = nlp(text_content)

    for item in doc.ents:
        val = item.text.strip()
        if item.label_ == "SKILL" and val.lower() not in jList[0]:
            jList[0].append(val.lower())
        elif item.label_ == "KNOWLEDGE" and val.lower() not in jList[1]:
            jList[1].append(val.lower())
        elif item.label_ == "ABILITY" and val.lower() not in jList[2]:
            jList[2].append(val.lower())
        elif item.label_ == "EDUCATION" and val.lower() not in jList[3]:
            jList[3].append(val.lower())
        elif item.label_ == "EXPERIENCE" and val.lower() not in jList[4]:
            jList[4].append(val.lower())
        elif item.label_ == "TRAINING" and val.lower() not in jList[5]:
            jList[5].append(val.lower())
    return jList


def listInterp(rsms, jdesc, x):
    """
    IMPROVED SCORING ENGINE:
    1. Weighted Scoring: Skills/Exp are worth 3x more than generic Abilities.
    2. Precise Matching: Uses Regex to prevent "Go" matching "Good".
    """
    jDescCompList = jFileParser(jdesc)

    # Weights for each category (Index 0-5)
    # 0:Skill(3pts), 1:Knowledge(1pt), 2:Ability(1pt), 3:Edu(2pts), 4:Exp(2pts), 5:Train(1pt)
    weights = [3, 1, 1, 2, 2, 1]

    # Calculate MAX possible weighted score for this specific Job Description
    max_weighted_score = 0
    for cat_idx, category_list in enumerate(jDescCompList):
        max_weighted_score += len(category_list) * weights[cat_idx]

    resume_data = {}

    for res in rsms:
        details_log = []
        current_weighted_score = 0

        # Unpack the Entities AND the Raw Text
        lR, raw_resume_text = resumeFileParser(res, "temp_parsing.txt")

        for cat_idx, spec_list in enumerate(jDescCompList):
            cat_weight = weights[cat_idx]

            for spec in spec_list:
                # CHECK 1: Precise Entity Match (Spacy found it)
                if spec in lR[cat_idx]:
                    current_weighted_score += cat_weight
                    details_log.append([spec, "met"])

                # CHECK 2: Precise Text Match (Regex found whole word)
                # \b means "Word Boundary" (start or end of a word)
                elif re.search(r'\b' + re.escape(spec) + r'\b', raw_resume_text):
                    current_weighted_score += cat_weight
                    details_log.append([spec, "met (text match)"])

                else:
                    details_log.append([spec, "not met"])

        # Final Score Calculation
        if max_weighted_score > 0:
            fScr = (current_weighted_score / max_weighted_score) * 100
        else:
            fScr = 0

        resume_data[res] = {'score': fScr, 'details': details_log}

    top_items = heapq.nlargest(x, resume_data.items(), key=lambda item: item[1]['score'])
    return dict(top_items)


#3. GOOGLE GEMINI BATCH FUNCTION

def ask_gemini_batch(placeholder1, placeholder2, full_text_corpus):
    prompt = f"""
    ### ROLE
    You are an expert Technical Recruiter and Data Analyst integration. 

    ### CONTEXT
    You have been provided with multiple resume files. The 'file_path' provided in the datasets below corresponds exactly to the names/paths of these uploaded files.

    HERE IS THE RAW CONTENT OF THE RESUMES:
    {full_text_corpus}

    ### DATA INPUTS
    1. PLACEHOLDER: {placeholder1}
    2. PLACEHOLDER_2: {placeholder2}

    ### TASK
    1. Match the metadata in the placeholders to the specific content of the uploaded resumes using the 'file_path' as the unique identifier.
    2. For each applicant, perform a deep synthesis:
       - Analyze the raw content of the resume file associated with the 'file_path'.
       - Cross-reference this with the "met/not met" status in PLACEHOLDER_2.
    3. Generate a "feedback" string for each applicant:
       - STRENGTHS: Mention specific evidence (projects, years of experience, or tools) found in the resume file that supports the "met" qualifications.
       - Make sure there is two new lines between STRENGTHS & WEAKNESSES
       - WEAKNESSES: Identify specific gaps or lack of detail in the resume file that resulted in "not met" qualifications.
    4. Sort the final collection by 'match_percentage' in descending order (highest to lowest).
    5. Account for any acronyms while looking for degrees. ex: B.S in computer science would mean a bachelors in computer science.

    ### OUTPUT CONSTRAINTS
    - Return ONLY a valid array of arrays.
    - Do not include conversational text, markdown code blocks (```json), or headers.
    - Output Schema: [[string: file_path, float: match_percentage, string: feedback], ...]
    - Do not include any applicant names

    ### EXECUTION
    Synthesize the uploaded files with the provided metadata and return the sorted 2D array.
    """

    print("Sending batch request to Google Gemini (Stable)...")
    try:
        model = genai.GenerativeModel('gemini-3-flash-preview')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini Error: {e}")
        return json.dumps([["Error", 0, f"AI Connection Failed: {str(e)}"]])


#4. THE CONNECTOR (CHONKER)

def chonker(job_desc_list, resumes_list, n):
    if not job_desc_list: return []
    jd_path = job_desc_list[0]

    # 1. Get Math Scores
    top_candidates = listInterp(resumes_list, jd_path, n)

    # 2. Prepare Data
    placeholder_1 = []
    placeholder_2 = []
    full_text_corpus = ""

    for full_path, data in top_candidates.items():
        fname = os.path.basename(full_path)
        placeholder_1.append([fname, f"{data['score']:.2f}%"])
        placeholder_2.append([fname, data['details']])

        temp_txt = convertPdfToText(full_path, "temp_ai.txt")
        with open(temp_txt, "r", encoding="utf-8") as f:
            content = f.read()
            full_text_corpus += f"\n--- START FILE: {fname} ---\n{content}\n--- END FILE: {fname} ---\n"
        if os.path.exists(temp_txt): os.remove(temp_txt)

    # 3. Call AI
    ai_response_str = ask_gemini_batch(placeholder_1, placeholder_2, full_text_corpus)

    # 4. Parse AI Response
    parsed_results = []

    clean_str = ai_response_str.strip()
    if clean_str.startswith("```json"):
        clean_str = clean_str.replace("```json", "").replace("```", "")
    elif clean_str.startswith("```"):
        clean_str = clean_str.replace("```", "")

    try:
        parsed_results = json.loads(clean_str)
    except Exception as e:
        print(f"JSON Parse Error: {e}")
        if len(placeholder_1) > 0:
            first_candidate = placeholder_1[0][0]
            first_score = placeholder_1[0][1]
            parsed_results.append([
                first_candidate,
                first_score,
                f"**JSON Error (Raw AI Output):**\n\n{clean_str}"
            ])

    #5. Save to Feedback Folder
    gui_results = []

    feedback_folder = os.path.join(root, "Feedback")
    os.makedirs(feedback_folder, exist_ok=True)

    for item in parsed_results:
        if isinstance(item, list) and len(item) >= 3:
            r_name = str(item[0])
            r_score = str(item[1])
            r_feedback = str(item[2])

            fb_filename = f"feedback_{r_name}.txt"
            fb_path = os.path.join(feedback_folder, fb_filename)

            with open(fb_path, "w", encoding="utf-8") as f:
                f.write(f"Resume: {r_name}\n")
                f.write(f"Match Score: {r_score}\n")
                f.write("------------------------------------------------\n")
                f.write("")
                f.write(r_feedback)


            gui_results.append([r_name, r_score, fb_path])

    return gui_results


if __name__ == "__main__":
    print("--- RUNNING IN DEBUG MODE ---")