import torch


def predict_reaction(model, citizen):

    features = [
        citizen.age,
        citizen.income,
        len(citizen.traits),
        citizen.traits["risk_tolerance"],
        citizen.traits["openness"],
        citizen.traits["political_leaning"]
    ]

    x = torch.tensor(features, dtype=torch.float32)

    output = model(x)

    return output.detach().numpy()

