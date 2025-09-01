#matcher.py
import os, json
from dotenv import load_dotenv
from langchain.tools import tool
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage

from config import llm
from resume_module.db import save_matches_to_db_tool, load_resumes_from_db_tool, load_jds_from_db_tool




# ---------------- Tools ----------------
@tool
def calculate_skill_match_tool(required_skills: list, candidate_skills: list) -> dict:
    """Calculate percentage match between required and candidate skills with skill details."""
    print(f"🔍 Calculating skill match - Required: {len(required_skills)}, Candidate: {len(candidate_skills)}")
    
    if not required_skills or not candidate_skills:
        result = {
            "match_percentage": 0,
            "matched_skills": [],
            "missing_skills": required_skills or []
        }
        print(f"❌ No skills to match: {result}")
        return result
    
    req = [s.lower().strip() for s in required_skills]
    cand = [s.lower().strip() for s in candidate_skills]
    
    matched_skills = []
    missing_skills = []
    
    for skill in req:
        found = False
        for c_skill in cand:
            if skill in c_skill or c_skill in skill:
                matched_skills.append(skill)
                found = True
                break
        if not found:
            missing_skills.append(skill)
    
    match_percentage = int(len(matched_skills) / len(req) * 100) if req else 0
    
    result = {
        "match_percentage": match_percentage,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills
    }
    
    print(f"✅ Skill match result: {match_percentage}% ({len(matched_skills)}/{len(req)} matched)")
    return result

@tool
def check_eligibility_criteria_tool(resume_data: dict, criteria: dict) -> bool:
    """
    Check if a candidate meets eligibility criteria.
    - Supports percentage-based (10th, 12th, graduation CGPA).
    - Supports experience-based (years of experience).
    - Works with either type or both.
    """
    print(f"Checking eligibility criteria")
    
    if not criteria:
        print("No criteria specified - candidate is eligible")
        return True
    
    # Check percentage criteria
    if criteria.get("10th_percentage_cutoff"):
        if not resume_data.get("high_school_percentage") or resume_data["high_school_percentage"] < criteria["10th_percentage_cutoff"]:
            print(f"Failed 10th percentage check: {resume_data.get('high_school_percentage')} < {criteria['10th_percentage_cutoff']}")
            return False
    
    if criteria.get("12th_percentage_cutoff"):
        if not resume_data.get("intermediate_percentage") or resume_data["intermediate_percentage"] < criteria["12th_percentage_cutoff"]:
            print(f"Failed 12th percentage check: {resume_data.get('intermediate_percentage')} < {criteria['12th_percentage_cutoff']}")
            return False
    
    if criteria.get("graduation_percentage_cutoff"):
        if not resume_data.get("btech_cgpa") or resume_data["btech_cgpa"] < criteria["graduation_percentage_cutoff"]:
            print(f"Failed graduation CGPA check: {resume_data.get('btech_cgpa')} < {criteria['graduation_percentage_cutoff']}")
            return False
    
    if criteria.get("experience_cutoff"):
        exp_years = resume_data.get("experience_years", 0) or 0
        if exp_years < criteria["experience_cutoff"]:
            print(f"Failed experience check: {exp_years} < {criteria['experience_cutoff']}")
            return False
    
    print("Candidate meets all eligibility criteria")
    return True

@tool
def calculate_overall_match_tool(
    tech_match: int, 
    soft_match: int, 
    experience_years: int = 0, 
    tech_weight: float = 0.7, 
    soft_weight: float = 0.3
) -> int:
    """Calculate single overall match percentage with experience bonus."""
    
    # Weighted score
    score = (tech_match * tech_weight) + (soft_match * soft_weight)
    # Bonus points for experience
    if experience_years > 0:
        score += min(experience_years * 2, 10)  # max +10% bonus
    # Ensure it doesn't exceed 100
    final_score = round(min(score, 100))

    
    print(f"Overall match calculation: Tech:{tech_match}% * {tech_weight} + Soft:{soft_match}% * {soft_weight} + Exp bonus:{min(experience_years * 2, 10) if experience_years > 0 else 0} = {final_score}%")
    return final_score

@tool
def match_candidate_to_jd_tool(resume_data: dict, jd_data: dict, candidate_name: str) -> dict:
    """Match a single candidate resume to a job description with skill analysis."""
    print(f"Matching candidate {candidate_name} to job")
    
    # Check eligibility first
    is_eligible = check_eligibility_criteria_tool.invoke({
        "resume_data": resume_data,
        "criteria": jd_data.get("criteria", {})
    })
    
    if not is_eligible:
        print(f"Candidate {candidate_name} is not eligible")
        return None

    # Technical skills analysis
    tech_analysis = calculate_skill_match_tool.invoke({
        "required_skills": jd_data.get("required_technical_skills", []),
        "candidate_skills": resume_data.get("technical_skills") or []
    })

    # Soft skills analysis
    soft_analysis = calculate_skill_match_tool.invoke({
        "required_skills": jd_data.get("required_soft_or_professional_skills", []),
        "candidate_skills": resume_data.get("professional_skills") or []
    })

    # Calculate overall match percentage
    experience_years = resume_data.get("experience_years", 0)
    if experience_years is None:
        experience_years = 0
    
    overall_match = calculate_overall_match_tool.invoke({
        "tech_match": tech_analysis["match_percentage"],
        "soft_match": soft_analysis["match_percentage"],
        "experience_years": experience_years
    })

    if overall_match <= 0:
        print(f"No match for candidate {candidate_name} - overall score: {overall_match}")
        return None

    # Combine all candidate skills
    candidate_skills = (resume_data.get("technical_skills") or []) + (resume_data.get("professional_skills") or [])
    
    # Combine all matched and missing skills
    all_matched_skills = tech_analysis["matched_skills"] + soft_analysis["matched_skills"]
    all_missing_skills = tech_analysis["missing_skills"] + soft_analysis["missing_skills"]

    match_result = {
        "name": resume_data.get("name") or candidate_name,
        "email": resume_data.get("email"),
        "phone": resume_data.get("phone"),
        "match_percentage": overall_match,
        "candidate_skills": candidate_skills,
        "matched_skills": all_matched_skills,
        "missing_skills": all_missing_skills,
        "experience_years": experience_years,
        "experience_type": resume_data.get("experience_type"),
        "has_career_gaps": resume_data.get("has_career_gaps", False),
        "stipend": jd_data.get("salary_package"),
        "job_location": jd_data.get("job_venue"),
        "internship_experience": resume_data.get("internship_experience")
    }
    
    print(f"Match successful: {candidate_name} - {overall_match}%")
    return match_result

@tool
def match_candidates_tool() -> str:
    """Match all candidates to all job descriptions and save results ONLY to MongoDB database."""
    print("Starting candidate matching process...")
    
    # Load from database instead of JSON files
    resumes_list = load_resumes_from_db_tool.invoke({})
    jds_list = load_jds_from_db_tool.invoke({})
    
    if not resumes_list: 
        print("No resumes found in database")
        return "No resumes in database"
    if not jds_list: 
        print("No JDs found in database")
        return "No JDs in database"
    
    print(f"Found {len(resumes_list)} resumes and {len(jds_list)} JDs in database")
    
    summary = []
    total_matches = 0
    
    for jd_info in jds_list:
        jd_name = jd_info.get('filename', 'unknown')
        print(f"Processing job: {jd_name}")
        matches = []
        
        for res_info in resumes_list:
            res_name = res_info.get('filename', 'unknown')
            candidate_name = res_info.get('name', res_name)
            print(f"  Checking candidate: {candidate_name}")
            
            m = match_candidate_to_jd_tool.invoke({
                "resume_data": res_info, 
                "jd_data": jd_info, 
                "candidate_name": candidate_name
            })
            if m: 
                matches.append(m)
                print(f"    Match found: {m['match_percentage']}%")
        
        # Save to database only (no JSON files)
        if matches:
            print(f"Saving {len(matches)} matches to database for job: {jd_name}")
            db_result = save_matches_to_db_tool.invoke({
                "matches": matches, 
                "job_filename": jd_name
            })
            print(f"Database save result: {db_result}")
            total_matches += len(matches)
        
        summary.append(f"{jd_name}: {len(matches)} matches saved to MongoDB")
    
    final_summary = f"Matching completed - {total_matches} total matches saved to MongoDB\n" + "\n".join(summary)
    print(final_summary)
    return final_summary

@tool
def load_data_from_db_tool() -> str:
    """Load and display data from database for verification."""
    print("Loading data from database for verification...")
    resumes = load_resumes_from_db_tool.invoke({})
    jds = load_jds_from_db_tool.invoke({})
    
    result = f"Database Status:\nResumes: {len(resumes)}\nJob Descriptions: {len(jds)}"
    print(result)
    return result