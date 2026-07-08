"""
config.py
 
Central configuration file for the AI Driving Coach.
"""
# os is a built-in Python module for talking to the operating system -
# reading environment variables, working with file paths, and so on.
# It's used here specifically so os.getenv() can read the API key.
import os
# dotenv is a third-party package (pip install python-dotenv).
# load_dotenv() reads the project's .env file and copies its contents
# into the environment, so os.getenv() can pick them up afterward.
# This is why the API key never needs to be hardcoded in source code.
from dotenv import load_dotenv
# anthropic is Anthropic's official Python SDK - a pre-built toolkit
# for calling the Claude API without writing raw HTTP requests by hand.
import anthropic
 
# Loads the .env file into the environment. This only loads the
# values - it doesn't return the API key itself, which is why
# os.getenv() is still needed below to actually retrieve it.
load_dotenv()
 
 
# ======================================================
# Claude API Configuration
# ======================================================
 
# Reads ANTHROPIC_API_KEY from the environment now that .env has been
# loaded. Returns the key if found, or None if it isn't set.
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY")
 
# Anthropic is a class provided by the SDK; calling it builds one
# reusable client object for making Claude API calls.
client = anthropic.Anthropic(
    api_key=CLAUDE_API_KEY
)
 
# ======================================================
# Claude Model
# ======================================================
 
MODEL_NAME = "claude-sonnet-5"
 
# ======================================================
# Retrieval Configuration
# ======================================================
 
# Number of top-ranked note chunks sent to Claude per question.
TOP_K = 5
 
# Maximum size of each text chunk
CHUNK_SIZE = 500
 
# Overlap between neighbouring chunks
CHUNK_OVERLAP = 100
 
# Closer to 1.0 produces more creative, varied responses; kept low
# here since answers should stay factual and grounded in lesson notes.
TEMPERATURE = 0.2
 