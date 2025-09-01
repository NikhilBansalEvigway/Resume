# leave_agent.py
"""
Centralized leave analysis agent logic.
This module contains all the shared logic for leave request analysis,
eliminating duplication between API and CLI implementations.
"""

import json
from typing import Dict, Any, Optional
from langchain.agents import create_react_agent, AgentExecutor
from langchain.tools import tool
from langchain.prompts import PromptTemplate

from config import llm
from leave_module.database import db_manager
from leave_module.core_analyzer import run_leave_analysis


# --- CENTRALIZED TOOL DEFINITION ---
@tool
def analyze_leave_request(request_data: str) -> str:
    """
    Analyzes a leave request and returns a simple text summary with approval/rejection decision.
    Input: JSON string of leave request data
    Output: Human-readable text summary with decision and reasons
    """
    try:
        # Parse the JSON string
        if isinstance(request_data, str):
            parsed_data = json.loads(request_data)
        else:
            parsed_data = request_data
        
        # Get policies and run analysis
        policies = db_manager.get_policies()
        analysis_result = run_leave_analysis(parsed_data, policies)
        
        # Convert structured result to simple text using centralized formatter
        return format_analysis_response(analysis_result)
        
    except Exception as e:
        return f"ERROR: Unable to process leave request - {str(e)}"


def format_analysis_response(analysis_result: Dict[str, Any]) -> str:
    """
    Centralized function to format analysis results into human-readable text.
    
    Args:
        analysis_result: The structured analysis result from core_analyzer
        
    Returns:
        str: Formatted text response
    """
    employee_name = analysis_result.get('employee_name', 'Employee')
    leave_type = analysis_result.get('leave_type', 'leave')
    requested_days = analysis_result.get('requested_days', 0)
    date_range = analysis_result.get('date_range', 'unknown dates')
    available_balance = analysis_result.get('available_balance', 0)
    violations = analysis_result.get('violations', [])
    flags = analysis_result.get('flags', [])
    status = analysis_result.get('status', 'unknown')
    
    # Create simple text response
    response_lines = []
    response_lines.append(f"LEAVE REQUEST ANALYSIS FOR {employee_name.upper()}")
    response_lines.append(f"Leave Type: {leave_type.title()}")
    response_lines.append(f"Duration: {requested_days} days ({date_range})")
    response_lines.append(f"Available Balance: {available_balance} days")
    response_lines.append("")
    
    if status == "approved":
        if flags:
            response_lines.append("DECISION: APPROVED WITH NOTES")
            response_lines.append("This leave request can be approved but has some points for HR attention:")
            for i, flag in enumerate(flags, 1):
                response_lines.append(f"{i}. {flag}")
        else:
            response_lines.append("DECISION: FULLY APPROVED")
            response_lines.append("This leave request meets all company policies and can be approved without any concerns.")
    
    elif status == "rejected":
        response_lines.append("DECISION: REJECTED")
        response_lines.append("This leave request cannot be approved due to the following policy violations:")
        for i, violation in enumerate(violations, 1):
            response_lines.append(f"{i}. {violation}")
    
    elif status == "flagged":
        response_lines.append("DECISION: REQUIRES HR REVIEW")
        response_lines.append("This leave request needs manual review by HR due to:")
        for i, flag in enumerate(flags, 1):
            response_lines.append(f"{i}. {flag}")
    
    return "\n".join(response_lines)


class LeaveAnalysisAgent:
    """
    Centralized class for leave analysis agent functionality.
    Contains all shared logic for both API and CLI usage.
    """
    
    def __init__(self):
        self.tools = [analyze_leave_request]
        self.agent_executor = self._create_agent()
    
    def _create_agent(self) -> AgentExecutor:
        """Create and configure the agent executor."""
        # --- CENTRALIZED PROMPT TEMPLATE ---
        prompt_template = """You are an HR assistant that analyzes leave requests. 

Available tools:
{tools}

Use this exact format:

Question: {input}
Thought: I need to analyze this leave request using the analyze_leave_request tool.
Action: analyze_leave_request
Action Input: [the JSON data from the question]
Observation: [the result from the tool will appear here]
Thought: Based on the analysis, I can now provide the final answer.
Final Answer: [repeat the exact text from the Observation - do not modify or summarize it]

{agent_scratchpad}"""

        prompt = PromptTemplate.from_template(prompt_template).partial(
            tools="\n".join([f"{tool.name}: {tool.description}" for tool in self.tools]),
            tool_names=", ".join([tool.name for tool in self.tools]),
        )

        agent = create_react_agent(llm, self.tools, prompt)
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3,
            early_stopping_method="force"
        )
    
    def analyze_request(self, request_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a leave request using the agent, with fallback to direct analysis.
        
        Args:
            request_dict: The leave request data as a dictionary
            
        Returns:
            dict: Analysis result containing summary, decision, and details
        """
        request_json = json.dumps(request_dict)
        
        try:
            # Try agent first
            agent_prompt = f"Analyze this leave request: {request_json}"
            agent_result = self.agent_executor.invoke({"input": agent_prompt})
            
            final_answer = agent_result.get('output', '')
            
            # Check if agent provided a valid response
            if final_answer and "LEAVE REQUEST ANALYSIS" in final_answer:
                # Also get structured data for additional details
                policies = db_manager.get_policies()
                structured_data = run_leave_analysis(request_dict, policies)
                
                return {
                    "status": "success",
                    "summary": final_answer,
                    "decision": structured_data.get('status', 'unknown').upper(),
                    "details": {
                        "employee_name": structured_data.get('employee_name'),
                        "leave_type": structured_data.get('leave_type'),
                        "requested_days": structured_data.get('requested_days'),
                        "available_balance": structured_data.get('available_balance'),
                        "date_range": structured_data.get('date_range'),
                        "has_violations": len(structured_data.get('violations', [])) > 0,
                        "has_flags": len(structured_data.get('flags', [])) > 0
                    },
                    "agent_used": True
                }
            else:
                # Agent failed, raise exception to trigger fallback
                raise Exception("Agent did not provide valid output")
                
        except Exception as agent_error:
            # Fallback to direct analysis
            print(f"Agent failed: {agent_error}, using direct analysis")
            
            policies = db_manager.get_policies()
            analysis_result = run_leave_analysis(request_dict, policies)
            
            # Use the centralized formatter
            summary_text = format_analysis_response(analysis_result)
            
            return {
                "status": "success",
                "summary": summary_text,
                "decision": analysis_result.get('status', 'unknown').upper(),
                "details": {
                    "employee_name": analysis_result.get('employee_name'),
                    "leave_type": analysis_result.get('leave_type'),
                    "requested_days": analysis_result.get('requested_days'),
                    "available_balance": analysis_result.get('available_balance'),
                    "date_range": analysis_result.get('date_range'),
                    "has_violations": len(analysis_result.get('violations', [])) > 0,
                    "has_flags": len(analysis_result.get('flags', [])) > 0
                },
            }


# Global instance to be shared between API and CLI
leave_agent = LeaveAnalysisAgent()