def create_training_data(population, llm_results):

    X = []
    y = []

    for citizen, result in zip(population, llm_results):

        features = [
            citizen.age,
            citizen.income,
            len(citizen.traits),
            citizen.traits["risk_tolerance"],
            citizen.traits["openness"],
            citizen.traits["political_leaning"]
        ]

        targets = [
            result["happiness_change"],
            result["support_change"],
            result["income_change"]
        ]

        X.append(features)
        y.append(targets)

    return X, y

