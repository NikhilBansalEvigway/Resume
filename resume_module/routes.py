# app/resume_module/routes.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
import shutil, os, tempfile
from typing import Dict

# Use relative imports within the module
from .parser import extract_resume_info_tool, load_pdf_tool, extract_jd_info_tool
from .matcher import match_candidate_to_jd_tool
from .db import save_resume_to_db_tool, save_jd_to_db_tool, save_matches_to_db_tool, get_db_stats_tool, load_resumes_from_db_tool, load_jds_from_db_tool, debug_db_tool

# Create an APIRouter
router = APIRouter()

# Helper function to process JD text
def process_jd_text(jd_text: str, jd_name: str) -> Dict:
    """Process job description text and save to DB."""
    jd_data = extract_jd_info_tool.invoke({"text": jd_text})
    if jd_data:
        save_jd_to_db_tool.invoke({"jd_data": jd_data, "filename": jd_name})
    return jd_data or {}

# --- API ENDPOINTS ---
@router.post("/upload/text")
async def upload_text(
    resume: UploadFile = File(...),
    jd_text: str = Form(...),
    jd_name: str = Form(...)
):
    """Upload resume PDF and JD text, process both, match, and store in MongoDB."""
    if not resume.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported for resume")

    temp_resume_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            shutil.copyfileobj(resume.file, tmp_file)
            temp_resume_path = tmp_file.name

        resume_filename = os.path.splitext(resume.filename)[0]
        resume_text = load_pdf_tool.invoke({"path": temp_resume_path})
        if resume_text.startswith(("Error", "Empty")):
            raise HTTPException(status_code=400, detail=f"Failed to read PDF: {resume_text}")

        resume_data = extract_resume_info_tool.invoke({"text": resume_text})
        if not resume_data:
            raise HTTPException(status_code=400, detail="Failed to extract resume information")

        save_resume_result = save_resume_to_db_tool.invoke({
            "resume_data": resume_data,
            "filename": resume_filename
        })

        jd_data = process_jd_text(jd_text, jd_name)
        if not jd_data:
            raise HTTPException(status_code=400, detail="Failed to extract job description information")

        match_result = match_candidate_to_jd_tool.invoke({
            "resume_data": resume_data,
            "jd_data": jd_data,
            "candidate_name": resume_data.get('name', resume_filename)
        })

        if not match_result:
            return {"success": False, "message": "Candidate did not meet job requirements"}

        save_match_result = save_matches_to_db_tool.invoke({
            "matches": [match_result],
            "job_filename": jd_name
        })

        return {
            "success": True,
            "message": "Resume and JD processed successfully, stored in MongoDB",
            "score": match_result.get("match_percentage", 0),
            "full_match_data": match_result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    finally:
        if temp_resume_path and os.path.exists(temp_resume_path):
            os.unlink(temp_resume_path)

@router.get("/stats")
async def get_stats():
    """Get comprehensive system statistics from MongoDB."""
    try:
        db_stats = get_db_stats_tool.invoke({})
        return { "success": True, "database_stats": db_stats }
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/debug")
async def debug_database():
    """Debug endpoint to check database connection and collections."""
    try:
        collections = debug_db_tool.invoke({})
        return {"success": True, "collections": collections}
    except Exception as e:
        return {"success": False, "error": str(e)}
