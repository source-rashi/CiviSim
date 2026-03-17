import google.generativeai as genai
import os
from dotenv import load_dotenv
import json

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if api_key and api_key != "your_api_key_here":
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
else:
    model = None


def generate_response(prompt):

    if model is None:
        return "Error: GEMINI_API_KEY not configured. Please add your API key to .env file."

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error calling Gemini API: {str(e)}"


def simulate_citizen_reaction(citizen, policy):

    prompt = f"""
    You are a citizen in a simulated society.

    Profile:
    Age: {citizen.age}
    Occupation: {citizen.occupation}
    Income: {citizen.income}
    Location: {citizen.location}
    Traits: {citizen.traits}

    Additional Attributes: {citizen.extra_attributes}

    Policy:
    {policy}

    Respond with a JSON object containing:
    - happiness_change: number between -1 and 1
    - support_change: number between -1 and 1
    - income_change: number (positive or negative)
    - diary_entry: short paragraph (2-3 sentences) describing how this policy affects you

    Output ONLY valid JSON, no other text.
    """

    return generate_response(prompt)


def parse_llm_output(response_text):

    try:
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        data = json.loads(response_text)
        return data
    except:
        return {
            "happiness_change": 0,
            "support_change": 0,
            "income_change": 0,
            "diary_entry": "No response generated"
        }

