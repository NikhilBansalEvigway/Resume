# app/leave_module/routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from datetime import date

# Use relative imports within the module
from  leave_module.database import db_manager
from leave_module.leave_agent import leave_agent

# Create an APIRouter instead of a FastAPI app
router = APIRouter()

# Pydantic Model for incoming requests
class LeaveRequest(BaseModel):
    employeeId: str
    startDate: date
    endDate: date
    typeOfLeave: str
    employeeName: str
    reason: str
    left: int

# --- API ENDPOINTS ---
@router.post("/apply")
def apply_leave(request: LeaveRequest):
    """
    Applies for leave using AI analysis.
    Uses the centralized leave_agent for consistent processing.
    """
    try:
        request_dict = {
            "employeeId": request.employeeId,
            "startDate": request.startDate.strftime('%Y-%m-%d'),
            "endDate": request.endDate.strftime('%Y-%m-%d'),
            "typeOfLeave": request.typeOfLeave,
            "employeeName": request.employeeName,
            "reason": request.reason,
            "left": request.left
        }
        result = leave_agent.analyze_request(request_dict)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing leave request: {str(e)}"
        )

@router.put("/policies/{leave_type}")
def update_policy(leave_type: str, policy_data: Dict[str, Any]):
    """Updates the company policy for a specific leave type in the database."""
    if db_manager.client is None:
        raise HTTPException(status_code=503, detail="Database connection is not available.")
    try:
        updated_policy = db_manager.update_policy(leave_type.lower(), policy_data)
        return {
            "status": "success",
            "message": f"Policy for '{leave_type}' leave updated successfully.",
            "updated_policy": {leave_type: updated_policy}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating policy: {str(e)}")

@router.get("/policies")
def get_policies():
    """Retrieves all current leave policies."""
    try:
        policies = db_manager.get_policies()
        return {
            "status": "success",
            "policies": policies
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting policies: {str(e)}")
