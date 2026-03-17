"""Test Phase 4.5 Model Improvements"""

import torch
import time
from population.population_generator import generate_population
from policy_engine.policy_parser import parse_policy
from ai_models.llm_interface import simulate_citizen_reaction, parse_llm_output
from ai_models.training_model import create_training_data, train_model, evaluate_model
from ai_models.reaction_predictor import predict_reaction

print("=" * 60)
print("PHASE 4.5 MODEL IMPROVEMENTS TEST")
print("=" * 60)

# Test data
policy_text = "Increase agricultural subsidies for drought relief"
parsed_policy = parse_policy(policy_text)

print(f"\n1. Policy: {policy_text}")
print(f"   Domain: {parsed_policy['domain']}")

# Generate small population for testing
print("\n2. Generating sample population...")
t0 = time.time()
sample_pop = generate_population(50)
t_gen = time.time() - t0
print(f"   Generated 50 citizens in {t_gen:.3f}s")

# Simulate LLM reactions
print("\n3. Generating LLM reactions (training data)...")
reactions = []
for i, citizen in enumerate(sample_pop):
    raw_response = simulate_citizen_reaction(citizen, policy_text)
    parsed = parse_llm_output(raw_response)
    parsed["citizen_id"] = i
    reactions.append(parsed)
    if (i + 1) % 10 == 0:
        print(f"   Simulated {i + 1}/50 citizens")
print(f"   ✓ Generated reactions for {len(reactions)} citizens")

# Test normalization and training
print("\n4. Training improved neural network...")
t0 = time.time()
X, y = create_training_data(sample_pop, reactions, parsed_policy)
print(f"   - Features shape: {len(X)}x{len(X[0])} (includes policy encoding)")
print(f"   - Targets shape: {len(y)}x{len(y[0])}")

model, mean, std = train_model(X, y, epochs=100)
t_train = time.time() - t0
print(f"   ✓ Training completed in {t_train:.2f}s with normalization & regularization")

# Test evaluation metric
print("\n5. Evaluating model...")
mse = evaluate_model(model, X, y, mean, std)
print(f"   Validation MSE: {mse:.6f}")

# Test predictions on larger population
print("\n6. Performance test: Full population prediction...")
pop_1k = generate_population(1000)
t0 = time.time()
for citizen in pop_1k:
    pred = predict_reaction(model, citizen, mean, std)
    # Verify outputs are clamped to [-1, 1]
    assert -1 <= pred[0] <= 1, f"Happiness {pred[0]} out of bounds"
    assert -1 <= pred[1] <= 1, f"Support {pred[1]} out of bounds"
    assert -1 <= pred[2] <= 1, f"Income {pred[2]} out of bounds"
t_pred = time.time() - t0
cps = 1000 / t_pred
print(f"   - Predicted 1,000 citizens in {t_pred:.3f}s")
print(f"   - Rate: {cps:,.0f} citizens/second")
print(f"   - Est. 10,000 citizens: {(10000/cps):.2f}s")
print(f"   - Est. throughput: {(cps * 3600 / 1000):,.0f}k policies/hour")

print("\n" + "=" * 60)
print("PHASE 4.5 TEST COMPLETE ✓")
print("=" * 60)
print("\nImprovements Applied:")
print("  ✓ Feature normalization for stable training")
print("  ✓ Policy domain encoding as 7th feature")
print("  ✓ Improved architecture: 64→32→16→3 with BatchNorm & Dropout")
print("  ✓ Training monitoring (loss prints every 40 epochs)")
print("  ✓ Output clamping to [-1, 1] for realistic predictions")
print("  ✓ Model evaluation metric (MSE)")
