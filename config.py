# app/config.py
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load environment variables from .env file in the root directory
load_dotenv()

# --- LLM Configuration (Shared) ---
API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    raise ValueError("⚠️ OPENROUTER_API_KEY is missing from your .env file")

MODEL_NAME = "meta-llama/llama-3.3-70b-instruct:free"
BASE_URL = "https://openrouter.ai/api/v1"
TEMPERATURE = 0.3
MAX_TOKENS = 4096

# Create a single, shared LLM instance for the entire application
llm = ChatOpenAI(
    model=MODEL_NAME,
    temperature=TEMPERATURE,
    max_tokens=MAX_TOKENS,
    openai_api_key=API_KEY,
    base_url=BASE_URL,
    default_headers={
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "HR Assistant"
    }
)


# --- Database Configuration ---
# You can keep separate URIs if they connect to different databases
LEAVE_MONGO_URI = os.getenv("LEAVE_MONGODB_URI", "mongodb://localhost:27017/")
RESUME_MONGO_URI = os.getenv("RESUME_MONGODB_URI", "mongodb://localhost:27017/")


# --- Server Configuration ---
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
