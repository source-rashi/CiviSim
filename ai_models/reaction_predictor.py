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

    # Add batch dimension for model forward pass (BatchNorm requires it)
    x = torch.tensor(np.array([features]), dtype=torch.float32)

    # Set model to eval mode for inference
    model.eval()
    
    with torch.no_grad():
        output = model(x)

    # Remove batch dimension and clamp outputs to realistic range [-1, 1]
    output = torch.clamp(output[0], -1, 1)

    return output.detach().numpy()

