import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Gemini model is loaded lazily — only when first needed.
# This means the file can be imported safely even if google-generativeai
# is not installed. Tests and offline runs will use the mock fallback.
_gemini_model = None


def _get_model():
    """Return the Gemini model instance, initializing it on first call."""
    global _gemini_model

    if _gemini_model is not None:
        return _gemini_model

    try:
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key or api_key == "your_api_key_here":
            logger.warning(
                "GEMINI_API_KEY not set or is placeholder. "
                "Running in mock mode — reactions will be simulated locally."
            )
            return None

        genai.configure(api_key=api_key)
        _gemini_model = genai.GenerativeModel("gemini-2.5-flash")
        logger.info("Gemini model initialized successfully.")
        return _gemini_model

    except ImportError:
        logger.warning(
            "google-generativeai package not installed. "
            "Running in mock mode. Install with: pip install google-generativeai"
        )
        return None


def _mock_reaction(citizen, policy):
    """
    Generate a realistic-looking mock reaction when Gemini is unavailable.
    Uses citizen attributes to produce varied (not identical) fake reactions
    so the rest of the pipeline still exercises properly during testing.
    """
    import random

    # Seed randomness on citizen id so results are consistent per citizen
    rng = random.Random(citizen.cid)

    # Base reaction varies by income and political leaning
    income_factor = (citizen.income - 10000) / 190000  # 0 to 1
    leaning = citizen.traits.get("political_leaning", 0.5)
    openness = citizen.traits.get("openness", 0.5)

    happiness = round(rng.uniform(-0.3, 0.3) + (openness - 0.5) * 0.4, 3)
    support = round(rng.uniform(-0.2, 0.4) + (leaning - 0.5) * 0.3, 3)
    income_change = round(rng.uniform(-2000, 5000) * income_factor, 2)

    diary = (
        f"As a {citizen.occupation} in {citizen.location}, this policy "
        f"{'seems promising' if happiness > 0 else 'raises concerns for me'}. "
        f"I {'support' if support > 0 else 'am skeptical of'} this direction."
    )

    return {
        "happiness_change": max(-1.0, min(1.0, happiness)),
        "support_change": max(-1.0, min(1.0, support)),
        "income_change": income_change,
        "diary_entry": diary
    }


def generate_response(prompt):
    """Call Gemini API with the given prompt. Returns raw text response."""
    model = _get_model()

    if model is None:
        return None  # Caller should handle None by using mock

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        return None


def simulate_citizen_reaction(citizen, policy):
    """
    Simulate how a citizen reacts to a policy.
    Uses Gemini if available, falls back to mock otherwise.
    Returns a parsed reaction dict directly.
    """
    model = _get_model()

    if model is None:
        logger.debug(f"Mock reaction for citizen {citizen.cid}")
        return _mock_reaction(citizen, policy)

    prompt = f"""
You are a citizen in a simulated society. Respond authentically based on your profile.

Your profile:
- Age: {citizen.age}
- Occupation: {citizen.occupation}
- Income: {citizen.income}
- Location: {citizen.location}
- Caste: {citizen.caste}
- Education: {citizen.education}
- Personality traits: {citizen.traits}
- Extra attributes: {citizen.extra_attributes}

Policy being evaluated:
{policy}

Respond with a JSON object containing exactly these keys:
- happiness_change: float between -1.0 and 1.0 (how this affects your wellbeing)
- support_change: float between -1.0 and 1.0 (how much you support this policy)
- income_change: float in rupees, positive or negative (realistic monthly income impact)
- diary_entry: string, 2-3 sentences written in first person describing your reaction

Output ONLY valid JSON. No markdown, no explanation, no extra text.
"""

    raw = generate_response(prompt)
    if raw is None:
        logger.warning(f"Gemini returned None for citizen {citizen.cid}, using mock.")
        return _mock_reaction(citizen, policy)

    return parse_llm_output(raw, citizen)


def parse_llm_output(response_text, citizen=None):
    """
    Parse JSON from LLM response. Falls back to mock reaction on failure.
    Logs what went wrong so you can debug bad responses.
    """
    try:
        # Strip markdown code fences if present
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json or ```) and last line (```)
            text = "\n".join(lines[1:-1]).strip()

        data = json.loads(text)

        # Validate required keys exist
        required = ["happiness_change", "support_change", "income_change", "diary_entry"]
        for key in required:
            if key not in data:
                raise ValueError(f"Missing key in LLM response: {key}")

        return data

    except Exception as e:
        logger.warning(
            f"LLM parse failed: {e}. "
            f"Raw response (first 300 chars): {response_text[:300]}"
        )
        if citizen is not None:
            return _mock_reaction(citizen, None)
        return {
            "happiness_change": 0.0,
            "support_change": 0.0,
            "income_change": 0.0,
            "diary_entry": "No response could be generated."
        }