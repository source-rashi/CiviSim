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
        "Affected groups and key attributes will be empty. "
        "Install google-generativeai and set GEMINI_API_KEY for full parsing."
    )

    return {
        "domain": detected_domain,
        "affected_groups": [],
        "key_attributes": [],
        "mechanism": "general",
        "summary": policy_text,
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

Policy text:
{policy_text}

Output ONLY the JSON object. No markdown, no explanation, no extra text.
"""


def parse_policy(policy_text):
    """
    Parse a natural language policy into structured data.

    Primary: uses Gemini to extract domain, affected groups, mechanism, etc.
    Fallback: keyword-based detection if Gemini is unavailable.

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
            # Gemini not available — use keyword fallback
            return _keyword_parse(policy_text)

        # Clean and parse the JSON response
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]).strip()

        parsed = json.loads(text)

        # Validate and fill missing keys with safe defaults
        result = {
            "domain":            parsed.get("domain", "general"),
            "affected_groups":   parsed.get("affected_groups", []),
            "key_attributes":    parsed.get("key_attributes", []),
            "mechanism":         parsed.get("mechanism", "general"),
            "time_effect":       parsed.get("time_effect", "gradual"),
            "summary":           parsed.get("summary", policy_text),
            "potential_winners": parsed.get("potential_winners", []),
            "potential_losers":  parsed.get("potential_losers", []),
            "parsed_by":         "gemini"
        }

        logger.info(
            f"Policy parsed by Gemini — domain: {result['domain']}, "
            f"groups: {result['affected_groups']}, "
            f"mechanism: {result['mechanism']}"
        )

        return result

    except json.JSONDecodeError as e:
        logger.warning(f"Gemini returned invalid JSON for policy parsing: {e}. Falling back to keywords.")
        return _keyword_parse(policy_text)

    except Exception as e:
        logger.warning(f"LLM policy parsing failed: {e}. Falling back to keywords.")
        return _keyword_parse(policy_text)