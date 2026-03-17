import random
from population.citizen import Citizen


def generate_population(size):

    population = []

    for i in range(size):

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

            caste=random.choice([
                "general",
                "obc",
                "sc",
                "st"
            ]),

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
            }

        )

        population.append(citizen)

    return population
