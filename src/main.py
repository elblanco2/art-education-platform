"""
Art Education Platform - Main Application
"""
import os
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join("config", ".env"))

# Initialize FastAPI application
app = FastAPI(
    title="Art Education Platform",
    description="A platform for converting art textbooks to digital format with AI enhancements and Canvas LMS integration.",
    version="0.1.0",
)

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def home():
    """
    Home page route
    """
    return {"message": "Welcome to the Art Education Platform"}

@app.get("/health")
async def health():
    """
    Health check endpoint
    """
    return {"status": "healthy"}

if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "False").lower() == "true",
    )
