# parser.py
import os, json, re
from dotenv import load_dotenv
from langchain.tools import tool
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import ChatOpenAI




from config import llm
from resume_module.db import save_resume_to_db_tool, save_jd_to_db_tool



from resume_module.db import save_resume_to_db_tool, save_jd_to_db_tool


def clean_json(raw):
    """Try to safely extract JSON even if LLM output has extra text."""
    if not raw:
        return "{}"
    raw = raw.strip().removeprefix("```json").removesuffix("```").strip()
    try:
        return raw if isinstance(raw, dict) else json.dumps(json.loads(raw))
    except:
        match = re.search(r"\{[\s\S]*\}", raw)
        return match.group(0) if match else "{}"

# ---------------- Tools ----------------
@tool
def extract_resume_info_tool(text: str) -> dict:
    """Extract structured information (name, phone, email, education, skills, experience type, career gaps) from resume text."""
    print(f"🔍 Extracting resume info from text (length: {len(text)})")
    text = text[:3000]
    prompt = f"""
You are a JSON parser. Extract ONLY:
{{
"name": "", "phone": "", "email": "",
"high_school_percentage": null, "intermediate_percentage": null, "btech_cgpa": null,
"technical_skills": [], "professional_skills": [], "internship_experience": null, "experience_years": null,
"experience_type": "", "has_career_gaps": false
}}
Rules: 
- numbers as numbers, null if missing
- donot use float number use integers only in experience years
- experience_type should be "internship", "full-time", "both", or "none" based on work experience mentioned
- has_career_gaps should be true if there are unexplained gaps in education/work timeline, false otherwise
Resume text:
{text}"""
    try:
        resp = llm.invoke(prompt)
        raw = resp.content if hasattr(resp, "content") else resp
        cleaned = clean_json(raw)
        result = json.loads(cleaned)
        print(f"✅ Resume extraction successful: {result.get('name', 'No name')}")
        return result
    except Exception as e:
        print(f"❌ ERR resume extract: {e}")
        return None

@tool
def extract_jd_info_tool(text: str) -> dict:
    """Extract structured requirements, skills, salary, and criteria from job description text."""
    print(f"🔍 Extracting JD info from text (length: {len(text)})")
    text = text[:3000]
    prompt = f"""
You are a JSON parser. Extract ONLY:
{{
"required_technical_skills": [], "required_soft_or_professional_skills": [], "salary_package": null,
"job_venue": null, "criteria": {{"10th_percentage_cutoff": null, "12th_percentage_cutoff": null, "graduation_percentage_cutoff": null, "experience_cutoff": null}}
}}
Rules: numbers as numbers, null if missing. Job description text:
{text}"""
    try:
        resp = llm.invoke(prompt)
        raw = resp.content if hasattr(resp, "content") else resp
        cleaned = clean_json(raw)
        result = json.loads(cleaned)
        print(f"✅ JD extraction successful")
        return result
    except Exception as e:
        print(f"❌ ERR JD extract: {e}")
        return None

@tool
def load_pdf_tool(path: str) -> str:
    """Load a PDF file and extract its text content."""
    print(f"📄 Loading PDF: {path}")
    try:
        loader = PyPDFLoader(path)
        pages = loader.load()
        text = "\n".join(p.page_content for p in pages)
        if text.strip():
            print(f"✅ PDF loaded successfully (length: {len(text)})")
            return text
        else:
            print(f"⚠️ Empty file: {path}")
            return f"Empty file: {path}"
    except Exception as e:
        print(f"❌ Error loading {path}: {e}")
        return f"Error loading {path}: {e}"

@tool
def process_pdf_tool(path: str, mode: str) -> str:
    """Process a PDF as either 'resume' or 'jd' and save ONLY to MongoDB database."""
    print(f"⚙️ Processing PDF: {path} as {mode}")
    name = os.path.splitext(os.path.basename(path))[0]
    text = load_pdf_tool.invoke({"path": path})
    if text.startswith(("Error", "Empty")): 
        print(f"❌ Failed to load PDF: {text}")
        return text
    
    if mode == "resume":
        print(f"📝 Extracting resume data for: {name}")
        data = extract_resume_info_tool.invoke({"text": text})
        # Save to database only
        if data:
            print(f"💾 Saving resume to database: {name}")
            db_result = save_resume_to_db_tool.invoke({"resume_data": data, "filename": name})
            return f"✅ Resume processed and saved to MongoDB: {name} - {db_result}"
        else:
            print(f"❌ Resume extraction failed for: {name}")
            return f"⚠️ Resume extraction failed for file: {path}"
    elif mode == "jd":
        print(f"📋 Extracting JD data for: {name}")
        data = extract_jd_info_tool.invoke({"text": text})
        # Save to database only
        if data:
            print(f"💾 Saving JD to database: {name}")
            db_result = save_jd_to_db_tool.invoke({"jd_data": data, "filename": name})
            return f"✅ JD processed and saved to MongoDB: {name} - {db_result}"
        else:
            print(f"❌ JD extraction failed for: {name}")
            return f"⚠️ JD extraction failed for file: {path}"
    else: 
        print(f"❌ Invalid mode: {mode}")
        return f"⚠️ Invalid mode: {mode}"

@tool
def parse_documents_tool() -> str:
    """Parse all PDFs in 'resumes' and 'job_descriptions' folders and save ONLY to MongoDB."""
    print("🚀 Starting document parsing to MongoDB...")
    results = ["📄 Parsing resumes to MongoDB:"]
    
    resume_count = 0
    if os.path.exists("resumes"):
        pdf_files = [f for f in os.listdir("resumes") if f.lower().endswith(".pdf")]
        print(f"📁 Found {len(pdf_files)} resume PDFs")
        for f in pdf_files:
            path = os.path.join("resumes", f)
            print(f"📄 Processing resume: {f}")
            res = process_pdf_tool.invoke({"path": path, "mode": "resume"})
            results.append(res)
            if "✅" in res:
                resume_count += 1
    else:
        results.append("⚠️ 'resumes' folder not found")

    results.append(f"\n📋 Parsing job descriptions to MongoDB:")
    jd_count = 0
    if os.path.exists("job_descriptions"):
        pdf_files = [f for f in os.listdir("job_descriptions") if f.lower().endswith(".pdf")]
        print(f"📁 Found {len(pdf_files)} JD PDFs")
        for f in pdf_files:
            path = os.path.join("job_descriptions", f)
            print(f"📋 Processing JD: {f}")
            res = process_pdf_tool.invoke({"path": path, "mode": "jd"})
            results.append(res)
            if "✅" in res:
                jd_count += 1
    else:
        results.append("⚠️ 'job_descriptions' folder not found")

    summary = f"\n🎯 Summary: {resume_count} resumes and {jd_count} JDs saved to MongoDB"
    results.append(summary)
    print(summary)
    
    return "\n".join(results)