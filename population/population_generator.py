import random
from population.citizen import Citizen


def generate_population(size, required_attributes=None):

    population = []

    for i in range(size):

        extra = {}

        if required_attributes:

            for attr in required_attributes:

                if attr == "caste":
                    extra["caste"] = random.choice(["general", "obc", "sc", "st"])

                elif attr == "student_status":
                    extra["student_status"] = random.choice([True, False])

                elif attr == "land_size":
                    extra["land_size"] = round(random.uniform(0.5, 5.0), 2)

                elif attr == "loan":
                    extra["loan"] = random.randint(10000, 100000)

        citizen = Citizen(

            cid=i,

            age=random.randint(18, 70),

            gender=random.choice(
                ["male", "female"]
            ),

            income=random.randint(
                10000,
                200000
            ),

            occupation=random.choice([
                "student",
                "worker",
                "business",
                "government",
                "unemployed"
            ]),

            caste=extra.get("caste", random.choice(["general", "obc", "sc", "st"])),

            education=random.choice([
                "school",
                "college",
                "phd"
            ]),

            location=random.choice([
                "urban",
                "semi-urban",
                "rural"
            ]),

            traits={
                "risk_tolerance": random.random(),
                "openness": random.random(),
                "political_leaning": random.random()
            },

            extra_attributes=extra

        )

        population.append(citizen)

    return population
