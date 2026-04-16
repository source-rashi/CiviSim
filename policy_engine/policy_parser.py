import json
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Keyword fallback (used when Gemini is unavailable)
# ---------------------------------------------------------------------------

DOMAIN_KEYWORDS = {
    "education":   ["education", "student", "school", "college", "scholarship",
                    "tuition", "university", "teacher", "curriculum", "literacy"],
    "tax":         ["tax", "income tax", "gst", "revenue", "fiscal",
                    "exemption", "deduction", "corporate tax"],
    "agriculture": ["farmer", "agriculture", "crop", "irrigation", "fertilizer",
                    "rural", "harvest", "kisan", "msp", "soil"],
    "health":      ["health", "hospital", "medicine", "doctor", "insurance",
                    "vaccine", "clinic", "disease", "mental health", "nutrition"],
}

ALLOWED_DOMAINS = {"education", "tax", "agriculture", "health", "general"}
ALLOWED_MECHANISMS = {
    "subsidy",
    "tax_change",
    "regulation",
    "restriction",
    "investment",
    "reform",
    "general",
}
ALLOWED_TIME_EFFECTS = {"immediate", "gradual", "long_term"}


def _coerce_choice(value, allowed, default):
    normalized = str(value).strip().lower()
    return normalized if normalized in allowed else default


def _coerce_string_list(value):
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _keyword_parse(policy_text):
    """
    Simple keyword-based fallback parser.
    Returns a basic policy dict with domain detected but groups/attributes empty.
    Used when Gemini is not available.
    """
    text = policy_text.lower()
    detected_domain = "general"

    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            detected_domain = domain
            break

    logger.warning(
        "Using keyword fallback for policy parsing. "
        "Affected groups and key attributes will be sparse. "
        "Install and configure Groq (GROQ_API_KEY) for full parsing quality."
    )

    return {
        "domain": detected_domain,
        "affected_groups": [],
        "key_attributes": [],
        "mechanism": "general",
        "time_effect": "gradual",
        "summary": policy_text,
        "potential_winners": [],
        "potential_losers": [],
        "parsed_by": "keyword_fallback"
    }


# ---------------------------------------------------------------------------
# LLM-based parser (primary path)
# ---------------------------------------------------------------------------

_PARSE_PROMPT = """
You are a policy analysis engine. Extract structured information from the policy text below.

Return ONLY a valid JSON object with exactly these keys:

{{
  "domain": one of ["education", "tax", "agriculture", "health", "general"],
  "affected_groups": list of specific groups affected (e.g. ["OBC students", "rural farmers", "small business owners"]),
  "key_attributes": list of citizen attributes needed to simulate this policy
                    (choose from: age, income, caste, occupation, education, location,
                     student_status, land_size, loan, crop_type, rural, tax_bracket,
                     education_level, health_status, gender),
  "mechanism": one of ["subsidy", "tax_change", "regulation", "restriction", "investment", "reform", "general"],
  "time_effect": one of ["immediate", "gradual", "long_term"],
  "summary": one concise sentence describing what this policy does and who it helps or affects,
  "potential_winners": list of groups likely to benefit,
  "potential_losers": list of groups likely to be negatively affected or left out
}}

Be specific. "OBC engineering students in rural areas" is better than "students".
If a field is genuinely unknown, use an empty list [] or "general".
Keep affected_groups, potential_winners, and potential_losers concise and concrete.
Use lower_snake_case for domain/mechanism/time_effect values exactly as listed.

Policy text:
{policy_text}

Output ONLY the JSON object. No markdown, no explanation, no extra text.
"""


def parse_policy(policy_text):
    """
    Parse a natural language policy into structured data.

    Primary: uses LLM parsing to extract domain, affected groups, mechanism, etc.
    Fallback: keyword-based detection if LLM is unavailable.

    Returns a dict with keys:
        domain, affected_groups, key_attributes, mechanism,
        time_effect, summary, potential_winners, potential_losers, parsed_by
    """
    if not policy_text or not policy_text.strip():
        return _keyword_parse("")

    # Try LLM-based parsing first
    try:
        from ai_models.llm_interface import generate_response

        prompt = _PARSE_PROMPT.format(policy_text=policy_text.strip())
        raw = generate_response(prompt)

        if raw is None:
            # LLM unavailable — use keyword fallback
            return _keyword_parse(policy_text)

        # Clean and parse the JSON response
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]).strip()

        parsed = json.loads(text)

        # Validate and fill missing keys with safe defaults
        result = {
            "domain": _coerce_choice(
                parsed.get("domain", "general"),
                ALLOWED_DOMAINS,
                "general",
            ),
            "affected_groups": _coerce_string_list(parsed.get("affected_groups", [])),
            "key_attributes": _coerce_string_list(parsed.get("key_attributes", [])),
            "mechanism": _coerce_choice(
                parsed.get("mechanism", "general"),
                ALLOWED_MECHANISMS,
                "general",
            ),
            "time_effect": _coerce_choice(
                parsed.get("time_effect", "gradual"),
                ALLOWED_TIME_EFFECTS,
                "gradual",
            ),
            "summary": str(parsed.get("summary", policy_text)).strip() or policy_text,
            "potential_winners": _coerce_string_list(parsed.get("potential_winners", [])),
            "potential_losers": _coerce_string_list(parsed.get("potential_losers", [])),
            "parsed_by":         "llm"
        }

        logger.info(
            f"Policy parsed by LLM — domain: {result['domain']}, "
            f"groups: {result['affected_groups']}, "
            f"mechanism: {result['mechanism']}"
        )

        return result

    except json.JSONDecodeError as e:
        logger.warning(f"LLM returned invalid JSON for policy parsing: {e}. Falling back to keywords.")
        return _keyword_parse(policy_text)

    except Exception as e:
        logger.warning(f"LLM policy parsing failed: {e}. Falling back to keywords.")
        return _keyword_parse(policy_text)