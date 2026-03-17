def parse_policy(policy_text):

    policy_text = policy_text.lower()

    policy = {
        "domain": None,
        "affected_groups": [],
        "key_attributes": [],
        "summary": policy_text
    }

    # Detect domain
    if "education" in policy_text or "student" in policy_text:
        policy["domain"] = "education"
    elif "tax" in policy_text:
        policy["domain"] = "tax"
    elif "farmer" in policy_text or "agriculture" in policy_text:
        policy["domain"] = "agriculture"
    else:
        policy["domain"] = "general"

    return policy
