import torch
import numpy as np


def predict_reaction(model, citizen, mean=None, std=None, policy_encoding=None):

    features = [
        citizen.age,
        citizen.income,
        citizen.traits["risk_tolerance"],
        citizen.traits["openness"],
        citizen.traits["political_leaning"],
        policy_encoding if policy_encoding is not None else 3  # default policy: general
    ]

    # Normalize if mean and std provided
    if mean is not None and std is not None:
        features = (np.array(features) - mean) / (std + 1e-8)

    x = torch.tensor(features, dtype=torch.float32)

    output = model(x)

    # Clamp outputs to realistic range [-1, 1]
    output = torch.clamp(output, -1, 1)

    return output.detach().numpy()

