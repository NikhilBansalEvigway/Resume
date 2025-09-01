from pymongo import MongoClient
from typing import Dict
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

class DatabaseManager:
    def __init__(self, connection_string: str = None):
        if connection_string is None:
            connection_string = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        
        try:
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            self.client.server_info()  # Test connection
            #self.db = self.client.leave_management

            db_name = os.getenv("DB_NAME", "hr_assistant") 
            self.db = self.client[db_name]                          
            self.policies_collection = self.db.policies
            print("✅ Connected to MongoDB")
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")
            # Fallback to default policies
            self.client = None
            self._fallback_policies = {
                "leave_types": {
                    "casual": {"max_days_per_request": 5, "requires_notice": 1},
                    "sick": {"max_days_per_request": 10, "requires_notice": 0, "requires_medical_certificate_after": 3},
                    "annual": {"max_days_per_request": 15, "requires_notice": 7}
                }
            }
    
    def get_policies(self) -> Dict:
        if self.client is None:
            return self._fallback_policies
            
        try:
            policy_doc = self.policies_collection.find_one({"_id": "company_policies"})
            if not policy_doc:
                # Create default policies
                default_policies = {
                    "_id": "company_policies",
                    "leave_types": {
                        "casual": {"max_days_per_request": 5, "requires_notice": 1},
                        "sick": {"max_days_per_request": 10, "requires_notice": 0, "requires_medical_certificate_after": 3},
                        "annual": {"max_days_per_request": 15, "requires_notice": 7}
                    }
                }
                self.policies_collection.insert_one(default_policies)
                return default_policies
            return policy_doc
        except Exception as e:
            print(f"Error getting policies: {e}")
            return self._fallback_policies

    def update_policy(self, leave_type: str, policy_data: Dict) -> Dict:
        if self.client is None:
            self._fallback_policies["leave_types"][leave_type] = policy_data
            return policy_data
            
        try:
            self.get_policies()  # Ensure document exists
            
            result = self.policies_collection.update_one(
                {"_id": "company_policies"},
                {"$set": {f"leave_types.{leave_type}": policy_data}},
                upsert=True
            )

            updated_policies = self.get_policies()
            return updated_policies["leave_types"].get(leave_type, {})
            
        except Exception as e:
            print(f"❌ Error during policy update: {e}")
            return policy_data

# Global instance
db_manager = DatabaseManager()