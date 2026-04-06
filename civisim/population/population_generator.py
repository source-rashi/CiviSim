import random
import logging
from population.citizen import Citizen

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Distributions
# ---------------------------------------------------------------------------

CASTES     = ["general", "obc", "sc", "st"]
EDUCATIONS = ["none", "primary", "secondary", "college", "graduate", "postgrad"]
LOCATIONS  = ["urban", "semi-urban", "rural"]
GENDERS    = ["male", "female", "other"]
CROPS      = ["wheat", "rice", "cotton", "sugarcane", "vegetables", "pulses"]
HEALTH     = ["excellent", "good", "fair", "poor"]


def _occupation_for_age(age):
    """
    Assign occupation based on age — realistically.
    Students are 17-25. Retired/unemployed skew older.
    Farmers and workers span all working ages.
    """
    if age <= 22:
        return random.choices(
            ["student", "worker", "unemployed"],
            weights=[70, 20, 10], k=1
        )[0]
    elif age <= 30:
        return random.choices(
            ["student", "worker", "business", "government", "unemployed", "farmer"],
            weights=[15, 35, 15, 15, 10, 10], k=1
        )[0]
    elif age <= 55:
        return random.choices(
            ["worker", "business", "government", "unemployed", "farmer"],
            weights=[30, 20, 15, 10, 25], k=1
        )[0]
    else:
        # Older citizens — mostly farmer, worker, or unemployed/retired
        return random.choices(
            ["farmer", "worker", "unemployed", "business", "government"],
            weights=[35, 25, 25, 10, 5], k=1
        )[0]


def _education_for(occupation, age):
    """Education correlates with occupation and age."""
    if occupation == "student":
        if age <= 18:
            return random.choices(
                EDUCATIONS, weights=[0, 5, 60, 30, 5, 0], k=1
            )[0]
        else:
            return random.choices(
                EDUCATIONS, weights=[0, 0, 10, 55, 30, 5], k=1
            )[0]
    elif occupation == "government":
        return random.choices(
            EDUCATIONS, weights=[0, 2, 10, 25, 45, 18], k=1
        )[0]
    elif occupation == "business":
        return random.choices(
            EDUCATIONS, weights=[1, 5, 20, 35, 30, 9], k=1
        )[0]
    elif occupation == "farmer":
        return random.choices(
            EDUCATIONS, weights=[15, 35, 35, 12, 2, 1], k=1
        )[0]
    elif occupation == "worker":
        return random.choices(
            EDUCATIONS, weights=[5, 20, 40, 25, 8, 2], k=1
        )[0]
    else:  # unemployed
        return random.choices(
            EDUCATIONS, weights=[10, 25, 40, 18, 5, 2], k=1
        )[0]


def _location_for(occupation):
    """Farmers skew rural. Government and business skew urban."""
    if occupation == "farmer":
        return random.choices(LOCATIONS, weights=[5, 20, 75], k=1)[0]
    elif occupation in ["government", "business"]:
        return random.choices(LOCATIONS, weights=[50, 30, 20], k=1)[0]
    else:
        return random.choices(LOCATIONS, weights=[35, 25, 40], k=1)[0]


def _income_for(occupation, location, age):
    """Realistic income ranges by occupation, location, and age."""
    base_ranges = {
        "student":    (2_000,   15_000),
        "worker":     (10_000,  80_000),
        "business":   (20_000, 300_000),
        "government": (25_000, 150_000),
        "unemployed": (0,       12_000),
        "farmer":     (8_000,   70_000),
    }
    low, high = base_ranges.get(occupation, (10_000, 100_000))

    # Location modifier
    if location == "rural":
        high = int(high * 0.65)
    elif location == "semi-urban":
        high = int(high * 0.82)

    # Age modifier — older workers earn more (experience)
    if age > 40 and occupation in ["worker", "government", "business"]:
        low = int(low * 1.2)

    return random.randint(max(0, low), max(low + 500, high))


def _generate_extra_attributes(required_attributes, occupation, income, location, education, age):
    """Generate policy-specific extra attributes with realistic distributions."""
    extra = {}

    for attr in required_attributes:

        if attr == "caste":
            extra["caste"] = random.choices(
                CASTES, weights=[50, 27, 16, 7], k=1
            )[0]

        elif attr == "gender":
            extra["gender"] = random.choices(
                GENDERS, weights=[49, 49, 2], k=1
            )[0]

        elif attr == "student_status":
            # Only realistic for younger citizens or part-time students
            extra["student_status"] = (
                occupation == "student" or
                (age <= 28 and occupation == "worker" and random.random() < 0.15)
            )

        elif attr == "education_level":
            extra["education_level"] = education

        elif attr == "tax_bracket":
            if income < 25_000:
                extra["tax_bracket"] = "none"
            elif income < 50_000:
                extra["tax_bracket"] = "low"
            elif income < 150_000:
                extra["tax_bracket"] = "mid"
            else:
                extra["tax_bracket"] = "high"

        elif attr == "loan":
            has_loan = random.random() < (
                0.65 if occupation in ["farmer", "worker"] else 0.3
            )
            extra["loan"] = random.randint(10_000, 500_000) if has_loan else 0

        elif attr == "savings":
            extra["savings"] = random.randint(0, int(income * 12 * 0.2))

        elif attr == "land_size":
            extra["land_size"] = (
                round(random.uniform(0.5, 10.0), 2)
                if occupation == "farmer"
                else round(random.uniform(0.0, 1.0), 2)
            )

        elif attr == "crop_type":
            extra["crop_type"] = random.choice(CROPS)

        elif attr == "irrigation":
            extra["irrigation"] = random.random() < (
                0.55 if location == "rural" else 0.3
            )

        elif attr == "rural":
            extra["rural"] = location == "rural"

        elif attr == "state":
            extra["state"] = random.choice([
                "UP", "Maharashtra", "Bihar", "West Bengal",
                "MP", "Rajasthan", "Tamil Nadu", "Karnataka",
                "Gujarat", "Andhra Pradesh"
            ])

        elif attr == "health_status":
            extra["health_status"] = random.choices(
                HEALTH,
                weights=[35, 45, 15, 5] if income > 100_000 else [15, 35, 35, 15],
                k=1
            )[0]

        elif attr == "insurance":
            extra["insurance"] = random.random() < (
                0.6 if income > 60_000 else 0.2
            )

        else:
            logger.debug(f"Unknown attribute requested: '{attr}' — skipping.")

    return extra


def generate_population(size, required_attributes=None):
    """
    Generate a synthetic population of `size` citizens.
    All demographics are correlated — age drives occupation,
    occupation drives location, income, and education.
    """
    if required_attributes is None:
        required_attributes = []

    population = []

    for i in range(size):
        # Age first — everything else flows from it
        age        = random.randint(18, 70)
        occupation = _occupation_for_age(age)
        location   = _location_for(occupation)
        education  = _education_for(occupation, age)
        income     = _income_for(occupation, location, age)
        caste      = random.choices(CASTES, weights=[50, 27, 16, 7], k=1)[0]
        gender     = random.choices(GENDERS, weights=[49, 49, 2], k=1)[0]

        extra = _generate_extra_attributes(
            required_attributes, occupation, income, location, education, age
        )

        citizen = Citizen(
            cid=i,
            age=age,
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