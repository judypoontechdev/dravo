import os
from dotenv import load_dotenv
import anthropic

# Load the .env file
load_dotenv()

# Read the API key
api_key = os.getenv("ANTHROPIC_API_KEY")

# Create the Claude client
client = anthropic.Anthropic(
    api_key=api_key
)

# Ask Claude a question
response = client.messages.create(

    model="claude-sonnet-5",

    max_tokens=200,

    messages=[
        {
            "role": "user",
            "content": "Hello Claude! Please introduce yourself in one sentence."
        }
    ]
)

# Print Claude's answer
print(response.content[0].text)