import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BATCH_SIZE   = 10   # citizens per API call — 10 is sweet spot for Groq
SAMPLE_SIZE  = 200  # total citizens to simulate with LLM
MODEL        = "llama-3.3-70b-versatile"  # best free model on Groq

_groq_client = None


# ---------------------------------------------------------------------------
# Client initialization
# ---------------------------------------------------------------------------

def _get_client():
    """Return Groq client, initializing lazily on first call."""
    global _groq_client

    if _groq_client is not None:
        return _groq_client

    try:
        from groq import Groq

        api_key = os.getenv("GROQ_API_KEY")

        if not api_key or api_key == "your_groq_api_key_here":
            logger.warning(
                "GROQ_API_KEY not set. Running in mock mode. "
                "Get a free key at console.groq.com"
            )
            return None

        _groq_client = Groq(api_key=api_key)
        logger.info(f"Groq client initialized. Model: {MODEL}")
        return _groq_client

    except ImportError:
        logger.warning(
            "groq package not installed. Running in mock mode. "
            "Install with: pip install groq"
        )
        return None

    except Exception as e:
        logger.error(f"Failed to initialize Groq client: {e}")
        return None


# ---------------------------------------------------------------------------
# Mock fallback
# ---------------------------------------------------------------------------

def _mock_reaction(citizen, policy):
    """
    Realistic mock reaction when Groq is unavailable.
    Varied per citizen — not identical for all.
    """
    import random

    rng = random.Random(citizen.cid)

    income_factor = max(0, (citizen.income - 10000) / 190000)
    leaning  = citizen.traits.get("political_leaning", 0.5)
    openness = citizen.traits.get("openness", 0.5)

    happiness    = round(rng.uniform(-0.5, 0.5) + (openness - 0.5) * 0.6, 3)
    support      = round(rng.uniform(-0.4, 0.6) + (leaning - 0.5) * 0.4, 3)
    income_change = round(rng.uniform(-3000, 8000) * income_factor, 2)

    diary = (
        f"As a {citizen.occupation} in {citizen.location}, this policy "
        f"{'genuinely helps me' if happiness > 0.2 else 'concerns me significantly' if happiness < -0.2 else 'has mixed implications for me'}. "
        f"I {'strongly support' if support > 0.4 else 'oppose' if support < -0.2 else 'am neutral on'} this direction."
    )

    return {
        "happiness_change": max(-1.0, min(1.0, happiness)),
        "support_change":   max(-1.0, min(1.0, support)),
        "income_change":    income_change,
        "diary_entry":      diary
    }


# ---------------------------------------------------------------------------
# Core: batch prompt builder
# ---------------------------------------------------------------------------

def _build_batch_prompt(citizens, policy):
    """
    Build a single prompt for multiple citizens.
    Returns prompt string asking for a JSON array of reactions.
    """
    profiles = []
    for i, c in enumerate(citizens):
        profiles.append(f"""
Citizen {i + 1}:
  Age: {c.age}, Gender: {c.gender}, Occupation: {c.occupation}
  Income: ₹{c.income:,}/month, Location: {c.location}
  Caste: {c.caste}, Education: {c.education}
  Traits: risk_tolerance={c.traits.get('risk_tolerance', 0.5):.2f}, openness={c.traits.get('openness', 0.5):.2f}, political_leaning={c.traits.get('political_leaning', 0.5):.2f}
  Extra: {c.extra_attributes}""")

    profiles_text = "\n".join(profiles)

    prompt = f"""You are simulating how real Indian citizens react to a government policy.
You will be given {len(citizens)} citizen profiles and one policy. For EACH citizen, generate an honest, specific reaction based on their profile.

CRITICAL RULES:
- Be HONEST and SPECIFIC — not diplomatic. Real people have strong reactions.
- A farmer losing land gives happiness_change of -0.7 to -0.9, NOT -0.2.
- A student getting free education gives happiness_change of +0.6 to +0.9, NOT +0.2.
- If the policy does NOT affect this citizen's group, happiness_change should be near 0.
- income_change must be in realistic rupees — e.g. +2000, -5000, +15000. NOT 0.3 or 1.0.
- diary_entry must be 2-3 sentences in first person, mentioning their specific situation.
- Reactions must DIFFER between citizens based on their profiles.

Policy: {policy}

Citizen profiles:
{profiles_text}

Respond with ONLY a valid JSON array of exactly {len(citizens)} objects.
Each object must have these exact keys:
  "happiness_change": float from -1.0 to 1.0
  "support_change": float from -1.0 to 1.0
  "income_change": float in rupees (can be large — e.g. 5000, -3000)
  "diary_entry": string, 2-3 sentences, first person

Example format:
[
  {{"happiness_change": 0.7, "support_change": 0.8, "income_change": 2000, "diary_entry": "As a student in rural Bihar..."}},
  {{"happiness_change": -0.5, "support_change": -0.3, "income_change": -1500, "diary_entry": "I run a small business..."}}
]

Output ONLY the JSON array. No explanation, no markdown, no extra text."""

    return prompt


# ---------------------------------------------------------------------------
# Core: single batch call
# ---------------------------------------------------------------------------

def _call_groq_batch(citizens, policy):
    """
    Call Groq with a batch of citizens.
    Returns list of parsed reaction dicts, one per citizen.
    Falls back to mock for any failed citizen.
    """
    client = _get_client()

    if client is None:
        return [_mock_reaction(c, policy) for c in citizens]

    prompt = _build_batch_prompt(citizens, policy)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,   # higher = more varied, honest reactions
            max_tokens=4000,
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1]).strip()

        reactions = json.loads(raw)

        if not isinstance(reactions, list):
            raise ValueError("Response is not a JSON array")

        if len(reactions) != len(citizens):
            raise ValueError(
                f"Expected {len(citizens)} reactions, got {len(reactions)}"
            )

        # Validate and clean each reaction
        cleaned = []
        for i, (reaction, citizen) in enumerate(zip(reactions, citizens)):
            try:
                cleaned.append({
                    "happiness_change": float(max(-1.0, min(1.0, reaction["happiness_change"]))),
                    "support_change":   float(max(-1.0, min(1.0, reaction["support_change"]))),
                    "income_change":    float(reaction["income_change"]),
                    "diary_entry":      str(reaction.get("diary_entry", "No entry.")),
                })
            except Exception as e:
                logger.warning(f"Bad reaction for citizen {i} in batch: {e}. Using mock.")
                cleaned.append(_mock_reaction(citizen, policy))

        return cleaned

    except json.JSONDecodeError as e:
        logger.error(f"Groq batch JSON parse failed: {e}. Raw: {raw[:300]}")
        return [_mock_reaction(c, policy) for c in citizens]

    except Exception as e:
        logger.error(f"Groq batch call failed: {e}")
        return [_mock_reaction(c, policy) for c in citizens]


# ---------------------------------------------------------------------------
# Public API: simulate full sample population
# ---------------------------------------------------------------------------

def simulate_population_reactions(population, policy, sample_size=SAMPLE_SIZE):
    """
    Simulate reactions for a sample of the population using batch prompting.

    - Takes up to `sample_size` citizens from the population
    - Sends them to Groq in batches of BATCH_SIZE (10 per call)
    - Returns list of reaction dicts, one per sampled citizen

    With sample_size=200 and BATCH_SIZE=10:
      → 20 API calls total
      → ~15-25 seconds
      → well within Groq free tier limits
    """
    sample = population[:sample_size]
    total  = len(sample)
    reactions = []

    logger.info(
        f"Simulating {total} citizens in batches of {BATCH_SIZE}. "
        f"Total API calls: {(total + BATCH_SIZE - 1) // BATCH_SIZE}"
    )

    for batch_start in range(0, total, BATCH_SIZE):
        batch = sample[batch_start: batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

        logger.info(f"Batch {batch_num}/{total_batches} — {len(batch)} citizens")

        batch_reactions = _call_groq_batch(batch, policy)
        reactions.extend(batch_reactions)

    logger.info(f"Simulation complete. {len(reactions)} reactions collected.")
    return reactions, sample


def simulate_citizen_reaction(citizen, policy):
    """
    Simulate a single citizen reaction.
    Used for individual testing — in the main pipeline use simulate_population_reactions().
    """
    results = _call_groq_batch([citizen], policy)
    return results[0]


# ---------------------------------------------------------------------------
# Legacy compatibility
# ---------------------------------------------------------------------------

def generate_response(prompt):
    """
    Direct prompt call — used by policy_parser.py for policy extraction.
    Returns raw text string or None.
    """
    client = _get_client()

    if client is None:
        return None

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,  # low temperature for structured extraction
            max_tokens=1000,
        )
        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"Groq generate_response failed: {e}")
        return None


def parse_llm_output(response_text, citizen=None):
    """
    Parse JSON from a raw LLM response string.
    Kept for compatibility — main pipeline now uses simulate_population_reactions().
    """
    try:
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]).strip()

        data = json.loads(text)

        required = ["happiness_change", "support_change", "income_change", "diary_entry"]
        for key in required:
            if key not in data:
                raise ValueError(f"Missing key: {key}")

        return data

    except Exception as e:
        logger.warning(f"parse_llm_output failed: {e}")
        if citizen is not None:
            return _mock_reaction(citizen, None)
        return {
            "happiness_change": 0.0,
            "support_change":   0.0,
            "income_change":    0.0,
            "diary_entry":      "No response generated."
        }