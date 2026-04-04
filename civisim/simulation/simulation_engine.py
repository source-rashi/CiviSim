from utils.metrics import (
    average_happiness,
    average_support,
    average_income
)
from ai_models.reaction_predictor import predict_batch


def run_simulation(population, model, steps, mean=None, std=None, policy_encoding=None):

    metrics_history = {
        "happiness": [],
        "support": [],
        "income": []
    }

    for step in range(steps):

        preds = predict_batch(model, population, mean, std, policy_encoding)

        for citizen, pred in zip(population, preds):
            citizen.update_state(
                float(pred[0]),
                float(pred[1]),
                float(pred[2])
            )

        metrics_history["happiness"].append(
            average_happiness(population)
        )

        metrics_history["support"].append(
            average_support(population)
        )

        metrics_history["income"].append(
            average_income(population)
        )

    return metrics_history
