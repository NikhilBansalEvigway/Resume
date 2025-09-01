import json
from datetime import datetime

# Updated import to use the centralized agent
from leave_agent import leave_agent
from database import db_manager


def get_user_input():
    """Get leave request input from console and format it correctly."""
    print("\n" + "="*60)
    print("LEAVE MANAGEMENT SYSTEM (CLI Edition)")
    print("="*60)
    
    try:
        # Get policies to show available leave types
        policies = db_manager.get_policies()
        
        print("\nAvailable Leave Types:", ", ".join(policies['leave_types'].keys()))
        
        # Get employee details
        emp_id = input("\nEnter Employee ID (e.g., E101): ").strip()
        emp_name = input("Enter Employee Name: ").strip()
        
        leave_type = input("Enter Leave Type: ").strip().lower()
        if leave_type not in policies['leave_types']:
            print("Invalid leave type.")
            return None

        # Get leave balance from user
        balance = input(f"Enter available '{leave_type}' leave balance: ").strip()
        try:
            balance = int(balance)
        except ValueError:
            print("Invalid balance. Please enter a number.")
            return None

        # Get dates and convert to YYYY-MM-DD
        while True:
            try:
                date_input = input("Enter Date Range (DD/MM/YY-DD/MM/YY): ").strip()
                date_from_str, date_to_str = date_input.split("-")
                start_date = datetime.strptime(date_from_str.strip(), "%d/%m/%y").strftime("%Y-%m-%d")
                end_date = datetime.strptime(date_to_str.strip(), "%d/%m/%y").strftime("%Y-%m-%d")
                break
            except Exception:
                print("Invalid date format. Please use DD/MM/YY-DD/MM/YY.")
        
        reason = input("Enter Reason for leave: ").strip()

        # Create the leave request in the correct format for the analyzer
        leave_request = {
            "employeeId": emp_id,
            "employeeName": emp_name,
            "startDate": start_date,
            "endDate": end_date,
            "typeOfLeave": leave_type,
            "reason": reason,
            "left": balance
        }
        
        return leave_request
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None


def main():
    print("Welcome to the Leave Management System!")

    while True:
        try:
            leave_request = get_user_input()
            if leave_request is None:
                continue
            
            print(f"\n{'='*60}\nPROCESSING LEAVE REQUEST\n{'='*60}")
            print(json.dumps(leave_request, indent=2))
            
            print(f"\n{'='*60}\nAGENT ANALYSIS\n{'='*60}")
            
            try:
                # Use centralized agent for analysis
                result = leave_agent.analyze_request(leave_request)
                
                print(f"\n{'='*60}\nFINAL RECOMMENDATION\n{'='*60}")
                print(result['summary'])
                
                # Show additional details if needed
                if not result.get('agent_used', True):
                    print(f"\n[Note: {result.get('note', 'Direct analysis used')}]")
                    
            except Exception as e:
                print(f"Complete processing error: {str(e)}")
            
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"An error occurred in the main loop: {str(e)}")
        
        continue_choice = input("\n\nProcess another leave request? (y/n): ").strip().lower()
        if continue_choice != 'y':
            break
    
    print("\nThank you for using the Leave Management System!")


if __name__ == "__main__":
    main()