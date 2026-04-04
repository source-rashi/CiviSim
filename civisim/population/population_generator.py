import random
import logging
from population.citizen import Citizen

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Realistic attribute distributions (India-context defaults)
# ---------------------------------------------------------------------------

OCCUPATIONS = ["student", "worker", "business", "government", "unemployed", "farmer"]
CASTES      = ["general", "obc", "sc", "st"]
EDUCATIONS  = ["none", "primary", "secondary", "college", "graduate", "postgrad"]
LOCATIONS   = ["urban", "semi-urban", "rural"]
GENDERS     = ["male", "female", "other"]
CROPS       = ["wheat", "rice", "cotton", "sugarcane", "vegetables", "pulses"]
HEALTH      = ["excellent", "good", "fair", "poor"]


def _income_for(occupation, location):
    """
    Generate a realistic income range based on occupation and location.
    Rural incomes skew lower; government and business skew higher.
    """
    base_ranges = {
        "student":      (5_000,  30_000),
        "worker":       (12_000, 80_000),
        "business":     (20_000, 300_000),
        "government":   (25_000, 150_000),
        "unemployed":   (0,      15_000),
        "farmer":       (8_000,  60_000),
    }
    low, high = base_ranges.get(occupation, (10_000, 100_000))

    # Location modifier
    if location == "rural":
        high = int(high * 0.65)
    elif location == "semi-urban":
        high = int(high * 0.85)

    return random.randint(max(0, low), max(low + 1000, high))


def _generate_extra_attributes(required_attributes, occupation, income, location, education):
    """
    Generate extra citizen attributes based on what the policy mapper requested.
    All attributes are generated with realistic distributions — not pure random.
    """
    extra = {}

    for attr in required_attributes:

        # --- identity / demographic ---
        if attr == "caste":
            # Approximate Indian population distribution
            extra["caste"] = random.choices(
                CASTES, weights=[50, 27, 16, 7], k=1
            )[0]

        elif attr == "gender":
            extra["gender"] = random.choices(
                GENDERS, weights=[49, 49, 2], k=1
            )[0]

        # --- education ---
        elif attr == "student_status":
            extra["student_status"] = occupation == "student" or (
                random.random() < 0.15 and occupation == "worker"
            )

        elif attr == "education_level":
            # Education correlates with income
            if income > 100_000:
                extra["education_level"] = random.choices(
                    EDUCATIONS, weights=[1, 2, 10, 20, 40, 27], k=1
                )[0]
            elif income > 40_000:
                extra["education_level"] = random.choices(
                    EDUCATIONS, weights=[2, 10, 25, 30, 25, 8], k=1
                )[0]
            else:
                extra["education_level"] = random.choices(
                    EDUCATIONS, weights=[10, 25, 35, 20, 8, 2], k=1
                )[0]

        # --- economic ---
        elif attr == "tax_bracket":
            # Derived from income — not random
            if income < 25_000:
                extra["tax_bracket"] = "none"
            elif income < 50_000:
                extra["tax_bracket"] = "low"
            elif income < 150_000:
                extra["tax_bracket"] = "mid"
            else:
                extra["tax_bracket"] = "high"

        elif attr == "loan":
            # Farmers and workers more likely to have loans
            has_loan = random.random() < (0.6 if occupation in ["farmer", "worker"] else 0.3)
            extra["loan"] = random.randint(10_000, 500_000) if has_loan else 0

        elif attr == "savings":
            # Savings correlate with income
            extra["savings"] = random.randint(0, int(income * 12 * 0.2))

        # --- agriculture ---
        elif attr == "land_size":
            # Farmers have more land; others may have small plots
            if occupation == "farmer":
                extra["land_size"] = round(random.uniform(0.5, 10.0), 2)
            else:
                extra["land_size"] = round(random.uniform(0.0, 1.0), 2)

        elif attr == "crop_type":
            extra["crop_type"] = random.choice(CROPS)

        elif attr == "irrigation":
            # Rural farmers more likely to have irrigation
            extra["irrigation"] = random.random() < (
                0.55 if location == "rural" else 0.3
            )

        # --- location ---
        elif attr == "rural":
            # Derived from location — not random
            extra["rural"] = location == "rural"

        elif attr == "state":
            extra["state"] = random.choice([
                "UP", "Maharashtra", "Bihar", "West Bengal",
                "MP", "Rajasthan", "Tamil Nadu", "Karnataka",
                "Gujarat", "Andhra Pradesh"
            ])

        # --- health ---
        elif attr == "health_status":
            # Health correlates inversely with income
            if income > 100_000:
                extra["health_status"] = random.choices(
                    HEALTH, weights=[35, 45, 15, 5], k=1
                )[0]
            else:
                extra["health_status"] = random.choices(
                    HEALTH, weights=[15, 35, 35, 15], k=1
                )[0]

        elif attr == "insurance":
            extra["insurance"] = random.random() < (0.6 if income > 60_000 else 0.2)

        # --- unknown attribute ---
        else:
            logger.debug(f"Unknown attribute requested: '{attr}' — skipping.")

    return extra


def generate_population(size, required_attributes=None):
    """
    Generate a synthetic population of `size` citizens.

    required_attributes: list of attribute names from the policy mapper.
    All requested attributes are generated with realistic distributions.
    """
    if required_attributes is None:
        required_attributes = []

    population = []

    for i in range(size):

        # Core demographics — generated first so extras can depend on them
        location   = random.choices(LOCATIONS, weights=[35, 25, 40], k=1)[0]
        occupation = random.choices(
            OCCUPATIONS, weights=[15, 30, 15, 10, 10, 20], k=1
        )[0]
        income     = _income_for(occupation, location)
        education  = random.choices(
            EDUCATIONS, weights=[8, 20, 30, 20, 15, 7], k=1
        )[0]
        caste      = random.choices(CASTES, weights=[50, 27, 16, 7], k=1)[0]
        gender     = random.choices(GENDERS, weights=[49, 49, 2], k=1)[0]

        # Extra attributes driven by policy domain
        extra = _generate_extra_attributes(
            required_attributes, occupation, income, location, education
        )

        citizen = Citizen(
            cid=i,
            age=random.randint(18, 70),
            gender=gender,
            income=income,
            occupation=occupation,
            caste=caste,
            education=education,
            location=location,
            traits={
                "risk_tolerance":    round(random.random(), 3),
                "openness":          round(random.random(), 3),
                "political_leaning": round(random.random(), 3),
            },
            extra_attributes=extra,
        )

        population.append(citizen)

    logger.info(
        f"Generated {size} citizens. "
        f"Extra attributes: {required_attributes or 'none'}."
    )
    return population