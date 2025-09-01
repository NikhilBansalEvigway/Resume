

# main.py
import os
from dotenv import load_dotenv
from langchain.tools import tool
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage


from parser import *
from matcher import *
from db import *

from config import llm

# ---------------- Utility helpers ----------------
def folder_status(path, ext=".pdf"):
    """Return a string summarizing the count of files with `ext` in `path` (or Missing)."""
    if not os.path.exists(path):
        return f"⌚ {path}: Missing"
    files = [f for f in os.listdir(path) if f.lower().endswith(ext)]
    return f"✅ {path}: {len(files)} {ext.upper()} files"

def json_count(path, label):
    """Return a string counting `.json` files in path."""
    if not os.path.exists(path):
        return f"{label}: 0"
    return f"{label}: {len([f for f in os.listdir(path) if f.endswith('.json')])}"

def invoke_tool(tool_fn, **kwargs):
    """Safely invoke a LangChain tool function, catching & returning errors."""
    try:
        return tool_fn.invoke(kwargs or {})
    except Exception as e:
        return f"⌚ {getattr(tool_fn, '__name__', str(tool_fn))}: {e}"

# ---------------- Enhanced Tools ----------------
@tool
def check_system_status_tool() -> str:
    """Check the system folder structure, database status, and list available resumes, JDs, and JSON outputs."""
    db_stats = invoke_tool(get_db_stats_tool)
    
    return "\n".join([
        "🔍 System Status:",
        folder_status("resumes"), folder_status("job_descriptions"),
        json_count("output/resumes", "Parsed Resumes"),
        json_count("output/jds", "Parsed JDs"),
        json_count("finaloutput", "Matches"),
        "📊 Database Status:",
        str(db_stats) if isinstance(db_stats, dict) else db_stats
    ])

@tool
def run_parsing_step_tool() -> str:
    """Run the document parsing step for resumes and job descriptions with database integration."""
    print("=== Parsing Documents ===")
    result = invoke_tool(parse_documents_tool)
    
    # Also show database stats after parsing
    db_result = invoke_tool(load_data_from_db_tool)
    
    return f"{result}\n\n{db_result}"

@tool
def run_matching_step_tool() -> str:
    """Run the candidate-job matching step with database integration."""
    print("=== Matching Candidates ===")
    result = invoke_tool(match_candidates_tool)
    
    # Show database stats after matching
    db_stats = invoke_tool(get_db_stats_tool)
    
    return f"{result}\n\nDatabase after matching: {db_stats}"

@tool
def run_full_pipeline_tool() -> str:
    """Run the full pipeline: status → parsing → matching with database integration."""
    return "\n".join([
        "🚀 Full pipeline starting...",
        invoke_tool(check_system_status_tool), "",
        invoke_tool(run_parsing_step_tool), "",
        invoke_tool(run_matching_step_tool), "",
        "🎉 Done! Check 'finaloutput' and MongoDB database."
    ])

@tool
def cleanup_system_tool() -> str:
    """Clean up all temporary JSON output files."""
    results = []
    for folder in ["output/resumes", "output/jds", "finaloutput"]:
        if os.path.exists(folder):
            count = 0
            for f in [f for f in os.listdir(folder) if f.endswith(".json")]:
                os.remove(os.path.join(folder, f))
                count += 1
            results.append(f"🗑️ Cleaned {count} files from: {folder}")
        else:
            results.append(f"📁 Missing: {folder}")
    
    results.append("💡 Note: Database records are preserved. Use database management tools to clean DB if needed.")
    return "\n".join(results)

@tool
def get_processing_stats_tool() -> str:
    """Get comprehensive statistics on parsed and matched files from both files and database."""
    stats = [
        "📊 Processing Stats: ",
        json_count("output/resumes", "JSON Resumes"),
        json_count("output/jds", "JSON JDs")
    ]
    
    # Database stats
    db_stats = invoke_tool(get_db_stats_tool)
    if isinstance(db_stats, dict):
        stats.extend([
            f"📄 Database Resumes: {db_stats.get('total_resumes', 0)}",
            f"📋 Database JDs: {db_stats.get('total_job_descriptions', 0)}",  
            f"🎯 Database Matches: {db_stats.get('total_matches', 0)}"
        ])
    
    # File-based matches
    if os.path.exists("finaloutput"):
        import json
        jobs, total_matches = 0, 0
        for f in [f for f in os.listdir("finaloutput") if f.endswith(".json")]:
            jobs += 1
            try:
                with open(os.path.join("finaloutput", f), encoding="utf-8") as jf:
                    total_matches += len(json.load(jf) or [])
            except:
                pass
        stats.append(f"📁 File Matches: {jobs} jobs, {total_matches} matches")
    
    return "\n".join(stats)

@tool 
def database_operations_tool(operation: str) -> str:
    """Perform database operations like viewing data or getting specific matches."""
    if operation == "load_resumes":
        resumes = invoke_tool(load_resumes_from_db_tool)
        return f"📄 Found {len(resumes) if isinstance(resumes, list) else 0} resumes in database"
    elif operation == "load_jds":
        jds = invoke_tool(load_jds_from_db_tool) 
        return f"📋 Found {len(jds) if isinstance(jds, list) else 0} job descriptions in database"
    elif operation == "stats":
        return invoke_tool(get_db_stats_tool)
    else:
        return f"⚠️ Unknown database operation: {operation}"

# ---------------- Agent creation ----------------
def create_orchestration_agent():
    """Create a LangChain agent that can orchestrate parsing, matching, reporting, and database operations."""
    tools = [
        # System tools
        check_system_status_tool, run_parsing_step_tool, run_matching_step_tool, 
        run_full_pipeline_tool, cleanup_system_tool, get_processing_stats_tool,
        database_operations_tool,
        
        # Parser tools
        load_pdf_tool, extract_resume_info_tool, extract_jd_info_tool, 
         process_pdf_tool, parse_documents_tool,
        
        # Matcher tools
        calculate_skill_match_tool, check_eligibility_criteria_tool, 
        calculate_overall_match_tool,  match_candidate_to_jd_tool,  
        match_candidates_tool, load_data_from_db_tool,
        
        # Database tools
        save_resume_to_db_tool, save_jd_to_db_tool, save_matches_to_db_tool,
        get_db_stats_tool, load_resumes_from_db_tool, load_jds_from_db_tool,
        get_matches_from_db_tool
    ]
    
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content="""You are a helpful assistant for a resume-job matching system with MongoDB database integration. 

Your capabilities include:
1. Processing PDF documents (resumes and job descriptions)
2. Extracting structured information using AI
3. Saving data to  MongoDB database
4. Matching candidates to job requirements
5. Providing comprehensive statistics and analysis

Always save extracted data to  database. 
When users request operations, use the appropriate tools in logical sequence and provide clear status updates."""),
        MessagesPlaceholder("chat_history", optional=True),
        MessagesPlaceholder("agent_scratchpad"),
        ("human", "{input}")
    ])

    agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt) 

    return AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True, max_iterations=10)

# ---------------- Orchestration Runner ----------------
def run_orchestrator():
    """Run the orchestration agent with enhanced workflow including database operations."""
    agent = create_orchestration_agent()
    commands = [
        "Check system status including database connectivity", 
        "Run full pipeline with database integration", 
        "Get comprehensive processing statistics from both files and database",
        "Show database operations status - load resumes and JDs counts"
    ]
    for q in commands:
        print(f"\n🎯 Executing Command: {q}\n{'-'*50}")
        res = agent.invoke({"input": q})
        print(res.get('output', res))
    print("\n✅ Enhanced orchestration with database integration finished.")

# ---------------- Main Execution Block ----------------
if __name__ == "__main__":
    if llm is None:
        print("⌚ OPENROUTER_API_KEY is not set. Please add it to your .env file.")
    else:
        print("🚀 Starting Resume Matcher with MongoDB Integration...")
        run_orchestrator()





