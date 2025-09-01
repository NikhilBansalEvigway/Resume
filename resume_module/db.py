import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from dotenv import load_dotenv
from langchain.tools import tool

# Load environment variables
load_dotenv()

class DatabaseManager:
    def __init__(self):
        # MongoDB connection string - add this to your .env file
        self.mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        self.database_name = os.getenv("DB_NAME", "resume_matcher")
        
        print(f"🔌 Connecting to MongoDB: {self.mongo_uri}")
        print(f"📂 Using database: {self.database_name}")
        
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.database_name]
            
            # Test connection
            self.client.admin.command('ping')
            print("✅ Connected to MongoDB successfully")
            
            # Collections
            self.resumes_collection = self.db.resumes
            self.job_descriptions_collection = self.db.job_descriptions
            self.matches_collection = self.db.matches
            
            print(f"📊 Collections created/accessed:")
            print(f"  - Resumes: {self.resumes_collection.name}")
            print(f"  - Job Descriptions: {self.job_descriptions_collection.name}")
            print(f"  - Matches: {self.matches_collection.name}")
            
            # Create indexes for better performance
            self.create_indexes()
            
            # Show current counts
            self.show_current_counts()
            
        except ConnectionFailure as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    def show_current_counts(self):
        """Show current document counts in all collections"""
        try:
            resume_count = self.resumes_collection.count_documents({})
            jd_count = self.job_descriptions_collection.count_documents({})
            match_count = self.matches_collection.count_documents({})
            
            print(f"📈 Current Database Counts:")
            print(f"  - Resumes: {resume_count}")
            print(f"  - Job Descriptions: {jd_count}")
            print(f"  - Matches: {match_count}")
        except Exception as e:
            print(f"⚠️ Error getting counts: {e}")
    
    def create_indexes(self):
        """Create indexes for better query performance"""
        try:
            # Resume indexes
            self.resumes_collection.create_index("filename", unique=True)
            self.resumes_collection.create_index("name")
            
            # Job description indexes
            self.job_descriptions_collection.create_index("filename", unique=True)
            
            # Matches indexes
            self.matches_collection.create_index("job_filename")
            self.matches_collection.create_index("match_percentage")
            self.matches_collection.create_index([("job_filename", 1), ("candidate_name", 1)])
            
            print("✅ Database indexes created successfully")
            
        except Exception as e:
            print(f"⚠️  Warning: Could not create indexes: {e}")
    
    def save_resume(self, resume_data: Dict, filename: str) -> str:
        """Save resume data to MongoDB with detailed logging"""
        try:
            print(f"💾 Saving resume: {filename}")
            print(f"📝 Resume data keys: {list(resume_data.keys()) if resume_data else 'None'}")
            
            if not resume_data:
                return "❌ Error: No resume data provided"
            
            resume_doc = {
                **resume_data,
                "filename": filename,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "document_type": "resume"
            }
            
            # Use filename as unique identifier with replace operation
            result = self.resumes_collection.replace_one(
                {"filename": filename},
                resume_doc,
                upsert=True
            )
            
            if result.upserted_id:
                print(f"✅ Resume inserted with new ID: {result.upserted_id}")
                success_msg = f"✅ Resume saved with ID: {result.upserted_id}"
            elif result.modified_count > 0:
                print(f"🔄 Resume updated for existing filename: {filename}")
                success_msg = f"✅ Resume updated for: {resume_data.get('name', filename)}"
            else:
                print(f"ℹ️ Resume already exists with same data: {filename}")
                success_msg = f"✅ Resume confirmed in database: {resume_data.get('name', filename)}"
            
            # Verify the save by querying back
            saved_doc = self.resumes_collection.find_one({"filename": filename})
            if saved_doc:
                print(f"✅ Verification: Resume found in database with _id: {saved_doc['_id']}")
            else:
                print(f"❌ Verification failed: Resume not found after save")
                return "❌ Error: Resume not found after save operation"
            
            # Show updated count
            total_resumes = self.resumes_collection.count_documents({})
            print(f"📊 Total resumes in database: {total_resumes}")
            
            return success_msg
                
        except Exception as e:
            error_msg = f"❌ Error saving resume: {e}"
            print(error_msg)
            return error_msg
    
    def save_job_description(self, jd_data: Dict, filename: str) -> str:
        """Save job description data to MongoDB with detailed logging"""
        try:
            print(f"💾 Saving job description: {filename}")
            print(f"📝 JD data keys: {list(jd_data.keys()) if jd_data else 'None'}")
            
            if not jd_data:
                return "❌ Error: No job description data provided"
            
            jd_doc = {
                **jd_data,
                "filename": filename,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "document_type": "job_description"
            }
            
            # Use replace_one for consistent behavior
            result = self.job_descriptions_collection.replace_one(
                {"filename": filename},
                jd_doc,
                upsert=True
            )
            
            if result.upserted_id:
                print(f"✅ JD inserted with new ID: {result.upserted_id}")
                success_msg = f"✅ Job Description saved with ID: {result.upserted_id}"
            elif result.modified_count > 0:
                print(f"🔄 JD updated for existing filename: {filename}")
                success_msg = f"✅ Job Description updated: {filename}"
            else:
                print(f"ℹ️ JD already exists with same data: {filename}")
                success_msg = f"✅ Job Description confirmed in database: {filename}"
            
            # Verify the save
            saved_doc = self.job_descriptions_collection.find_one({"filename": filename})
            if saved_doc:
                print(f"✅ Verification: JD found in database with _id: {saved_doc['_id']}")
            else:
                print(f"❌ Verification failed: JD not found after save")
                return "❌ Error: Job Description not found after save operation"
            
            # Show updated count
            total_jds = self.job_descriptions_collection.count_documents({})
            print(f"📊 Total JDs in database: {total_jds}")
            
            return success_msg
                
        except Exception as e:
            error_msg = f"❌ Error saving job description: {e}"
            print(error_msg)
            return error_msg
    
    def save_match_results(self, matches: List[Dict], job_filename: str) -> str:
        """Save matching results to MongoDB with detailed logging"""
        try:
            print(f"💾 Saving {len(matches)} matches for job: {job_filename}")
            
            if not matches:
                return "❌ Error: No matches data provided"
            
            saved_count = 0
            
            # Clear existing matches for this job first
            delete_result = self.matches_collection.delete_many({"job_filename": job_filename})
            if delete_result.deleted_count > 0:
                print(f"🗑️ Deleted {delete_result.deleted_count} existing matches for {job_filename}")
            
            for i, match in enumerate(matches):
                print(f"📝 Saving match {i+1}: {match.get('name')} - {match.get('match_percentage')}%")
                
                match_doc = {
                    "job_filename": job_filename,
                    "candidate_name": match.get("name"),
                    "match_percentage": match.get("match_percentage"),
                    "matched_skills": match.get("matched_skills", []),
                    "missing_skills": match.get("missing_skills", []),
                    "candidate_skills": match.get("candidate_skills", []),
                    "experience_years": match.get("experience_years"),
                    "experience_type": match.get("experience_type"),
                    "has_career_gaps": match.get("has_career_gaps", False),
                    "email": match.get("email"),
                    "phone": match.get("phone"),
                    "stipend": match.get("stipend"),
                    "job_location": match.get("job_location"),
                    "internship_experience": match.get("internship_experience"),
                    "created_at": datetime.utcnow()
                }
                
                # Insert match
                result = self.matches_collection.insert_one(match_doc)
                print(f"✅ Match saved with ID: {result.inserted_id}")
                saved_count += 1
            
            # Show updated count
            total_matches = self.matches_collection.count_documents({})
            print(f"📊 Total matches in database: {total_matches}")
            
            success_msg = f"✅ Saved {saved_count} matches for {job_filename}"
            print(success_msg)
            return success_msg
            
        except Exception as e:
            error_msg = f"❌ Error saving matches: {e}"
            print(error_msg)
            return error_msg
    
    def get_all_resumes(self) -> List[Dict]:
        """Get all resumes from database with logging"""
        try:
            cursor = self.resumes_collection.find({})
            resumes = []
            for doc in cursor:
                # Convert ObjectId to string for JSON serialization
                doc['_id'] = str(doc['_id'])
                resumes.append(doc)
            
            print(f"📖 Retrieved {len(resumes)} resumes from database")
            
            # Log first resume if exists
            if resumes:
                first_resume = resumes[0]
                print(f"📝 Sample resume: {first_resume.get('name')} (filename: {first_resume.get('filename')})")
            
            return resumes
        except Exception as e:
            print(f"❌ Error fetching resumes: {e}")
            return []
    
    def get_all_job_descriptions(self) -> List[Dict]:
        """Get all job descriptions from database with logging"""
        try:
            cursor = self.job_descriptions_collection.find({})
            jds = []
            for doc in cursor:
                # Convert ObjectId to string for JSON serialization
                doc['_id'] = str(doc['_id'])
                jds.append(doc)
            
            print(f"📖 Retrieved {len(jds)} job descriptions from database")
            
            # Log first JD if exists
            if jds:
                first_jd = jds[0]
                print(f"📝 Sample JD: filename: {first_jd.get('filename')}")
            
            return jds
        except Exception as e:
            print(f"❌ Error fetching job descriptions: {e}")
            return []
    
    def get_matches_for_job(self, job_filename: str) -> List[Dict]:
        """Get all matches for a specific job with logging"""
        try:
            cursor = self.matches_collection.find({"job_filename": job_filename}).sort("match_percentage", -1)
            matches = []
            for doc in cursor:
                # Convert ObjectId to string for JSON serialization
                doc['_id'] = str(doc['_id'])
                matches.append(doc)
            
            print(f"📖 Retrieved {len(matches)} matches for job: {job_filename}")
            return matches
        except Exception as e:
            print(f"❌ Error fetching matches: {e}")
            return []
    
    def get_database_stats(self) -> Dict:
        """Get statistics about the database with detailed logging"""
        try:
            resume_count = self.resumes_collection.count_documents({})
            jd_count = self.job_descriptions_collection.count_documents({})
            match_count = self.matches_collection.count_documents({})
            
            stats = {
                "total_resumes": resume_count,
                "total_job_descriptions": jd_count,
                "total_matches": match_count,
                "database_name": self.database_name,
                "connection_uri": self.mongo_uri.split('@')[-1] if '@' in self.mongo_uri else self.mongo_uri  # Hide credentials
            }
            
            print(f"📊 Database Statistics:")
            print(f"  - Database: {self.database_name}")
            print(f"  - Resumes: {resume_count}")
            print(f"  - Job Descriptions: {jd_count}")
            print(f"  - Matches: {match_count}")
            
            return stats
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
            return {}
    
    def list_all_collections(self) -> Dict:
        """List all collections in the database for debugging"""
        try:
            collections = self.db.list_collection_names()
            print(f"📚 All collections in database '{self.database_name}': {collections}")
            
            collection_stats = {}
            for col_name in collections:
                count = self.db[col_name].count_documents({})
                collection_stats[col_name] = count
                print(f"  - {col_name}: {count} documents")
            
            return collection_stats
        except Exception as e:
            print(f"❌ Error listing collections: {e}")
            return {}
    
    def close_connection(self):
        """Close database connection"""
        if hasattr(self, 'client'):
            self.client.close()
            print("📴 Database connection closed")

# Global database instance
db_manager = DatabaseManager()

# ---------------- LangChain Tools ----------------
@tool
def save_resume_to_db_tool(resume_data: dict, filename: str) -> str:
    """Save parsed resume data to MongoDB database."""
    print(f"🔧 Tool called: save_resume_to_db_tool with filename: {filename}")
    print(f"📋 Resume data received: {bool(resume_data)} (has data: {resume_data is not None})")
    if resume_data:
        print(f"📝 Resume data keys: {list(resume_data.keys())}")
    return db_manager.save_resume(resume_data, filename)

@tool  
def save_jd_to_db_tool(jd_data: dict, filename: str) -> str:
    """Save parsed job description data to MongoDB database."""
    print(f"🔧 Tool called: save_jd_to_db_tool with filename: {filename}")
    print(f"📋 JD data received: {bool(jd_data)} (has data: {jd_data is not None})")
    if jd_data:
        print(f"📝 JD data keys: {list(jd_data.keys())}")
    return db_manager.save_job_description(jd_data, filename)

@tool
def save_matches_to_db_tool(matches: list, job_filename: str) -> str:
    """Save matching results to MongoDB database."""
    print(f"🔧 Tool called: save_matches_to_db_tool with job_filename: {job_filename}")
    print(f"📋 Matches data received: {len(matches) if matches else 0} matches")
    return db_manager.save_match_results(matches, job_filename)

@tool
def get_db_stats_tool() -> dict:
    """Get database statistics including counts of resumes, job descriptions, and matches."""
    print(f"🔧 Tool called: get_db_stats_tool")
    return db_manager.get_database_stats()

@tool
def load_resumes_from_db_tool() -> list:
    """Load all resumes from MongoDB database."""
    print(f"🔧 Tool called: load_resumes_from_db_tool")
    return db_manager.get_all_resumes()

@tool
def load_jds_from_db_tool() -> list:
    """Load all job descriptions from MongoDB database."""
    print(f"🔧 Tool called: load_jds_from_db_tool")
    return db_manager.get_all_job_descriptions()

@tool
def get_matches_from_db_tool(job_filename: str) -> list:
    """Get all matches for a specific job from MongoDB database."""
    print(f"🔧 Tool called: get_matches_from_db_tool with job_filename: {job_filename}")
    return db_manager.get_matches_for_job(job_filename)

@tool
def debug_db_tool() -> dict:
    """Debug tool to show all collections and their contents"""
    print(f"🔧 Tool called: debug_db_tool")
    return db_manager.list_all_collections()