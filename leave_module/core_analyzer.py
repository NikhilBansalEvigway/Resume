# This file is confirmed to be compatible with the latest app.py updates.
from datetime import datetime

def run_leave_analysis(request: dict, policies: dict) -> dict:
    """
    Performs a complete analysis of a leave request against company policies.
    This function checks for hard violations and soft flags.
    
    Args:
        request (dict): The leave request data.
        policies (dict): The company's leave policies.
        
    Returns:
        dict: A structured dictionary containing the full analysis, including
              status, violations, flags, and other details.
    """
    violations = []
    flags = []
    
    leave_type = request["typeOfLeave"]
    leave_policy = policies.get("leave_types", {}).get(leave_type)
    
    # --- Date Calculation ---
    try:
        start_date = datetime.strptime(request["startDate"], "%Y-%m-%d")
        end_date = datetime.strptime(request["endDate"], "%Y-%m-%d")
        requested_days = (end_date - start_date).days + 1
        if requested_days <= 0:
            violations.append("Invalid date range: End date must be on or after the start date.")
    except Exception as e:
        violations.append(f"Invalid date format: {str(e)}")
        # If dates are invalid, we cannot proceed with further checks.
        return build_response(request, requested_days=0, violations=violations, flags=flags)

    # --- Policy and Balance Checks (Violations) ---
    if not leave_policy:
        violations.append(f"Unknown leave type: '{leave_type}' is not a valid leave category.")
    else:
        # Check 1: Sufficient balance
        available_balance = request.get("left", 0)
        if available_balance < requested_days:
            violations.append(f"Insufficient Balance: You requested {requested_days} days but only have {available_balance} available.")
        
        # Check 2: Maximum days per request
        max_days = leave_policy.get("max_days_per_request", float('inf'))
        if requested_days > max_days:
            violations.append(f"Exceeds Limit: Your request for {requested_days} days exceeds the maximum of {max_days} days allowed per request.")
            
        # Check 3: Notice period
        notice_required = leave_policy.get("requires_notice", 0)
        if notice_required > 0:
            notice_given = (start_date.date() - datetime.now().date()).days
            if notice_given < notice_required:
                violations.append(f"Insufficient Notice: This leave requires {notice_required} days notice, but you provided {notice_given}.")

        # Check 4: Medical certificate for sick leave
        if leave_type == "sick":
            cert_after = leave_policy.get("requires_medical_certificate_after", float('inf'))
            if requested_days > cert_after:
                violations.append(f"Medical Certificate Required: A doctor's note is needed for sick leave longer than {cert_after} days.")

    # If there are any violations, return immediately. No need to check for flags.
    if violations:
        return build_response(request, requested_days, violations=violations, flags=[])

    # --- Further Checks (Flags for HR Review) ---
    # Flag 1: High usage (using > 50% of remaining balance)
    if available_balance > 0 and requested_days > (available_balance * 0.5):
        flags.append("High Usage: This request uses a significant portion of the remaining leave balance.")
        
    # Flag 2: Reason mismatch
    reason = request.get("reason", "").lower()
    if leave_type == "sick" and not any(word in reason for word in ["sick", "ill", "medical", "doctor",  "hospital", "fever", "injury", "disease","accident","suffering"]):
        flags.append("Reason Mismatch: The reason provided may not align with a sick leave request. Please ensure it is for a medical issue.")
        
    # Flag 3: Leave bridges a weekend
    if start_date.weekday() == 4 and end_date.weekday() > 4 : # Friday to Monday or beyond
         flags.append("Weekend Bridge: This leave extends over a weekend, which might impact weekly handovers.")

    return build_response(request, requested_days, violations=[], flags=flags)


def build_response(request: dict, requested_days: int, violations: list, flags: list) -> dict:
    """Helper to construct the final analysis dictionary."""
    status = "rejected" if violations else ("flagged" if flags else "approved")
    
    message = ""
    if status == "rejected":
        message = "The leave request is rejected due to policy violations."
    elif status == "flagged":
        message = "The leave request is approved but has been flagged for HR review."
    else:
        message = "The leave request is fully approved."

    return {
        "status": status,
        "message": message,
        "employee_name": request["employeeName"],
        "leave_type": request["typeOfLeave"],
        "requested_days": requested_days,
        "date_range": f"{request['startDate']} to {request['endDate']}",
        "available_balance": request.get("left", 0),
        "violations": violations,
        "flags": flags
    }