# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import the routers from your modules
from leave_module import routes as leave_routes
from resume_module import routes as resume_routes

# Import server configuration
from config import API_HOST, API_PORT

# Create the main FastAPI application instance
app = FastAPI(
    title="Unified HR Assistant API",
    description="A single API for both Leave Management and Resume Matching.",
    version="1.0.0"
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Include Module Routers ---

# Include the leave module endpoints under the "/leave" prefix
app.include_router(
    leave_routes.router,
    prefix="/leave",
    tags=["Leave Management"]  # This groups the endpoints in the API docs
)

# Include the resume module endpoints under the "/resume" prefix
app.include_router(
    resume_routes.router,
    prefix="/resume",
    tags=["Resume Matching"] # This groups the endpoints in the API docs
)


# --- Root Endpoint ---
@app.get("/", tags=["Home"])
def read_root():
    """
    A welcome message for the unified API.
    """
    return {
        "message": "Welcome to the Unified HR Assistant API!",
        "api_docs": "/docs"
    }

# --- How to Run ---
if __name__ == "__main__":
    import uvicorn
    # To run this app, navigate to the `hr_assistant_project` directory
    # and run the command: uvicorn app.main:app --reload
    uvicorn.run(app, host=API_HOST, port=API_PORT)
