import json
import logging
import os
import random
import time

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BATCH_SIZE = int(os.getenv("GROQ_BATCH_SIZE", "10"))
SAMPLE_SIZE = int(os.getenv("GROQ_SAMPLE_SIZE", "200"))
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
MOCK_BATCH_DELAY_SECONDS = float(os.getenv("MOCK_BATCH_DELAY_SECONDS", "0.25"))

_groq_client = None
_client_init_attempted = False
_runtime_mode = "mock"


# ---------------------------------------------------------------------------
# Client initialization and runtime metadata
# ---------------------------------------------------------------------------

def _get_client():
    """Return Groq client, initializing lazily on first call."""
    global _groq_client
    global _client_init_attempted
    global _runtime_mode

    if _groq_client is not None:
        return _groq_client

    if _client_init_attempted:
        return None

    _client_init_attempted = True

    try:
        from groq import Groq

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or api_key in {"your_api_key_here", "your_groq_api_key_here"}:
            _runtime_mode = "mock"
            logger.warning(
                "GROQ_API_KEY not set or is placeholder. Running in mock mode."
            )
            return None

        _groq_client = Groq(api_key=api_key)
        _runtime_mode = "groq"
        logger.info("Groq client initialized. Model: %s", MODEL)
        return _groq_client

    except ImportError:
        _runtime_mode = "mock"
        logger.warning(
            "groq package not installed. Running in mock mode. Install with: pip install groq"
        )
        return None

    except Exception as exc:
        _runtime_mode = "mock"
        logger.error("Failed to initialize Groq client: %s", exc)
        return None


def get_runtime_mode():
    """Return current LLM runtime mode: 'groq' or 'mock'."""
    _get_client()
    return _runtime_mode


def is_live_llm_mode():
    """Return True when Groq is configured and available."""
    return get_runtime_mode() == "groq"


# ---------------------------------------------------------------------------
# Mock fallback
# ---------------------------------------------------------------------------

def _mock_reaction(citizen, policy):
    """
    Realistic mock reaction when Groq is unavailable.
    Varied per citizen so training data is still non-trivial.
    """
    rng = random.Random()

    income_factor = max(0, (citizen.income - 10000) / 190000)
    leaning = citizen.traits.get("political_leaning", 0.5)
    openness = citizen.traits.get("openness", 0.5)

    happiness = round(rng.uniform(-0.5, 0.5) + (openness - 0.5) * 0.6, 3)
    support = round(rng.uniform(-0.4, 0.6) + (leaning - 0.5) * 0.4, 3)
    income_change = round(rng.uniform(-3000, 8000) * income_factor, 2)

    diary = (
        f"As a {citizen.occupation} in {citizen.location}, this policy "
        f"{'genuinely helps me' if happiness > 0.2 else 'concerns me significantly' if happiness < -0.2 else 'has mixed implications for me'}. "
        f"I {'strongly support' if support > 0.4 else 'oppose' if support < -0.2 else 'am neutral on'} this direction."
    )

    return {
        "happiness_change": max(-1.0, min(1.0, happiness)),
        "support_change": max(-1.0, min(1.0, support)),
        "income_change": income_change,
        "diary_entry": diary,
    }


# ---------------------------------------------------------------------------
# Prompting helpers
# ---------------------------------------------------------------------------

def _build_batch_prompt(citizens, policy):
    """Build a single prompt for multiple citizens."""
    profiles = []
    for i, citizen in enumerate(citizens):
        profiles.append(
            f"""
Citizen {i + 1}:
  Age: {citizen.age}, Gender: {citizen.gender}, Occupation: {citizen.occupation}
  Income: Rs {citizen.income:,}/month, Location: {citizen.location}
  Caste: {citizen.caste}, Education: {citizen.education}
  Traits: risk_tolerance={citizen.traits.get('risk_tolerance', 0.5):.2f}, openness={citizen.traits.get('openness', 0.5):.2f}, political_leaning={citizen.traits.get('political_leaning', 0.5):.2f}
  Extra: {citizen.extra_attributes}"""
        )

    profiles_text = "\n".join(profiles)

    return f"""You are simulating how real Indian citizens react to a government policy.
You will be given {len(citizens)} citizen profiles and one policy. For EACH citizen, generate an honest and specific reaction based on their profile.

CRITICAL RULES:
- Be honest and specific, not diplomatic.
- Strongly affected citizens can have strong changes (for example +/-0.7 or more).
- If the policy does not affect a citizen's group, happiness_change should be near 0.
- income_change must be in realistic rupees (for example +2000, -5000, +15000), not normalized values.
- diary_entry must be 2-3 first-person sentences and mention specific context.
- Reactions must differ between citizens based on profile differences.

Policy: {policy}

Citizen profiles:
{profiles_text}

Respond with ONLY a valid JSON array of exactly {len(citizens)} objects.
Each object must have these exact keys:
  \"happiness_change\": float from -1.0 to 1.0
  \"support_change\": float from -1.0 to 1.0
  \"income_change\": float in rupees
  \"diary_entry\": string, 2-3 sentences, first person

Output ONLY the JSON array. No markdown, no explanation, no extra text."""


def _strip_markdown_fence(text):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]).strip()
    return cleaned


RECOMMENDATION_CHOICES = {"implement", "conditional", "do_not_implement"}


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_recommendation_payload(payload):
    if not isinstance(payload, dict):
        return None

    recommendation = str(payload.get("recommendation", "")).strip().lower()
    if recommendation not in RECOMMENDATION_CHOICES:
        return None

    confidence_score = _safe_float(payload.get("confidence_score", 0.5), default=0.5)
    confidence_score = max(0.0, min(1.0, confidence_score))

    reasoning = str(payload.get("reasoning", "")).strip() or "No reasoning provided."

    key_risks_raw = payload.get("key_risks", [])
    key_risks = key_risks_raw if isinstance(key_risks_raw, list) else []
    key_risks = [str(item).strip() for item in key_risks if str(item).strip()][:5]

    conditions_raw = payload.get("conditions", [])
    conditions = conditions_raw if isinstance(conditions_raw, list) else []
    conditions = [str(item).strip() for item in conditions if str(item).strip()][:5]

    return {
        "recommendation": recommendation,
        "confidence_score": confidence_score,
        "reasoning": reasoning,
        "key_risks": key_risks,
        "conditions": conditions,
    }


# ---------------------------------------------------------------------------
# Groq calls
# ---------------------------------------------------------------------------

def _call_groq_batch(citizens, policy):
    """
    Call Groq with a batch of citizens.
    Returns one cleaned reaction dict per citizen.
    Falls back to mock when Groq is unavailable or malformed.
    """
    client = _get_client()

    if client is None:
        if MOCK_BATCH_DELAY_SECONDS > 0:
            time.sleep(MOCK_BATCH_DELAY_SECONDS)
        return [_mock_reaction(c, policy) for c in citizens]

    prompt = _build_batch_prompt(citizens, policy)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=4000,
        )

        raw = _strip_markdown_fence(response.choices[0].message.content)
        parsed = json.loads(raw)

        if not isinstance(parsed, list):
            raise ValueError("Groq response is not a JSON array")

        if len(parsed) != len(citizens):
            raise ValueError(
                f"Expected {len(citizens)} reactions, got {len(parsed)}"
            )

        cleaned = []
        for idx, (reaction, citizen) in enumerate(zip(parsed, citizens)):
            try:
                cleaned.append(
                    {
                        "happiness_change": float(
                            max(-1.0, min(1.0, reaction["happiness_change"]))
                        ),
                        "support_change": float(
                            max(-1.0, min(1.0, reaction["support_change"]))
                        ),
                        "income_change": float(reaction["income_change"]),
                        "diary_entry": str(reaction.get("diary_entry", "No entry.")),
                    }
                )
            except Exception as exc:
                logger.warning(
                    "Bad reaction for citizen %s in batch: %s. Using mock.", idx, exc
                )
                cleaned.append(_mock_reaction(citizen, policy))

        return cleaned

    except json.JSONDecodeError as exc:
        preview = raw[:300] if "raw" in locals() else "<no raw response>"
        logger.error("Groq batch JSON parse failed: %s. Raw: %s", exc, preview)
        return [_mock_reaction(c, policy) for c in citizens]

    except Exception as exc:
        logger.error("Groq batch call failed: %s", exc)
        return [_mock_reaction(c, policy) for c in citizens]


def generate_response(prompt):
    """
    Direct prompt call used by policy parsing.
    Returns raw text or None.
    """
    client = _get_client()
    if client is None:
        return None

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1000,
        )
        return response.choices[0].message.content

    except Exception as exc:
        logger.error("Groq generate_response failed: %s", exc)
        return None


def generate_policy_recommendation(policy_text, parsed_policy, final_metrics, population_stats):
    """
    Generate a structured policy recommendation after simulation results are available.
    Returns None when LLM output is unavailable or invalid.
    """
    metrics = final_metrics or {}
    stats = population_stats or {}

    prompt = f"""You are a public policy decision assistant.
Given the policy details and simulation outcomes, return a strict recommendation.

Return ONLY valid JSON with exactly these keys:
{{
  "recommendation": one of ["implement", "conditional", "do_not_implement"],
  "confidence_score": float from 0.0 to 1.0,
  "reasoning": string with 2-4 concise sentences,
  "key_risks": list of short risk statements,
  "conditions": list of conditions that must be satisfied before rollout
}}

Decision guidance:
- Recommend "implement" only when support and welfare indicators are convincingly positive.
- Recommend "conditional" when outcomes are mixed or uncertain but salvageable.
- Recommend "do_not_implement" when risks outweigh benefits.
- Base confidence on evidence quality and metric consistency.

Policy text:
{policy_text}

Parsed policy:
- domain: {parsed_policy.get("domain", "general")}
- mechanism: {parsed_policy.get("mechanism", "general")}
- affected_groups: {parsed_policy.get("affected_groups", [])}
- potential_winners: {parsed_policy.get("potential_winners", [])}
- potential_losers: {parsed_policy.get("potential_losers", [])}

Simulation metrics:
- final_happiness: {metrics.get("final_happiness", 0.0)}
- final_support: {metrics.get("final_support", 0.0)}
- income_start: {metrics.get("income_start", 0.0)}
- income_end: {metrics.get("income_end", 0.0)}
- income_change: {metrics.get("income_change", 0.0)}
- happiness_trend_delta: {metrics.get("happiness_trend_delta", 0.0)}
- support_trend_delta: {metrics.get("support_trend_delta", 0.0)}

Population stats:
- total_population: {stats.get("total", 0)}
- occupation_distribution: {stats.get("occupations", {})}
- caste_distribution: {stats.get("castes", {})}

Output only the JSON object. No markdown. No explanation outside JSON."""

    raw = generate_response(prompt)
    if raw is None:
        return None

    try:
        parsed = json.loads(_strip_markdown_fence(raw))
    except json.JSONDecodeError as exc:
        logger.warning("Policy recommendation JSON parse failed: %s", exc)
        return None

    normalized = _normalize_recommendation_payload(parsed)
    if normalized is None:
        logger.warning("Policy recommendation response failed schema validation.")
        return None

    normalized["source"] = "llm"
    return normalized


# ---------------------------------------------------------------------------
# Public APIs
# ---------------------------------------------------------------------------

def simulate_population_reactions(population, policy, sample_size=SAMPLE_SIZE):
    """
    Simulate reactions for a sampled subset of the population.

    - Takes up to sample_size citizens.
    - Sends them to Groq in BATCH_SIZE chunks.
    - Returns (reactions, sample_population).
    """
    bounded_size = max(1, min(int(sample_size), len(population))) if population else 0
    sample_population = random.sample(population, bounded_size) if population else []

    if not sample_population:
        return [], []

    total = len(sample_population)
    total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    reactions = []

    logger.info(
        "Simulating %s citizens in %s batches (batch_size=%s, mode=%s).",
        total,
        total_batches,
        BATCH_SIZE,
        get_runtime_mode(),
    )

    for batch_start in range(0, total, BATCH_SIZE):
        batch = sample_population[batch_start : batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        logger.info("Batch %s/%s with %s citizens", batch_num, total_batches, len(batch))

        batch_reactions = _call_groq_batch(batch, policy)
        reactions.extend(batch_reactions)

    logger.info("Reaction simulation complete. Collected %s reactions.", len(reactions))
    return reactions, sample_population


def simulate_citizen_reaction(citizen, policy):
    """Simulate reaction for a single citizen."""
    results = _call_groq_batch([citizen], policy)
    return results[0]


def parse_llm_output(response_text, citizen=None):
    """
    Parse a single JSON reaction payload for compatibility with older flows.
    """
    try:
        data = json.loads(_strip_markdown_fence(response_text))
        required = [
            "happiness_change",
            "support_change",
            "income_change",
            "diary_entry",
        ]
        for key in required:
            if key not in data:
                raise ValueError(f"Missing key: {key}")

        return {
            "happiness_change": float(max(-1.0, min(1.0, data["happiness_change"]))),
            "support_change": float(max(-1.0, min(1.0, data["support_change"]))),
            "income_change": float(data["income_change"]),
            "diary_entry": str(data.get("diary_entry", "No response generated.")),
        }

    except Exception as exc:
        logger.warning("parse_llm_output failed: %s", exc)
        if citizen is not None:
            return _mock_reaction(citizen, None)
        return {
            "happiness_change": 0.0,
            "support_change": 0.0,
            "income_change": 0.0,
            "diary_entry": "No response generated.",
        }
