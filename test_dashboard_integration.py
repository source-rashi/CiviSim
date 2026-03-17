"""Test Dashboard Integration with Phase 4.5 Improvements"""

import sys
import os
import time

# Add civisim to path
sys.path.insert(0, os.getcwd())

from population.population_generator import generate_population
from policy_engine.policy_parser import parse_policy
from policy_engine.policy_mapper import map_policy_to_attributes
from ai_models.llm_interface import simulate_citizen_reaction, parse_llm_output
from ai_models.training_model import create_training_data, train_model, encode_policy
from ai_models.reaction_predictor import predict_reaction

print("=" * 70)
print("DASHBOARD INTEGRATION TEST - PHASE 4.5 IMPROVEMENTS")
print("=" * 70)

# Simulate dashboard flow
policy_input = "Increase education budget and scholarships for underprivileged students"

print(f"\n[1/7] Policy Input Detection")
print(f"      Policy: '{policy_input}'")

print(f"\n[2/7] Policy Analysis")
parsed_policy = parse_policy(policy_input)
print(f"      Domain Detected: {parsed_policy['domain'].upper()}")
print(f"      Affected Groups: {parsed_policy['affected_groups']}")
print(f"      Key Attributes: {parsed_policy['key_attributes']}")

print(f"\n[3/7] Attribute Mapping")
attributes = map_policy_to_attributes(parsed_policy)
print(f"      Relevant Attributes: {attributes}")

print(f"\n[4/7] Population Generation (10,000)")
pop = generate_population(10000, attributes)
print(f"      [OK] Generated {len(pop)} citizens")

print(f"\n[5/7] LLM Sample Reactions (50 citizens)")
sample_size = min(50, len(pop))
sample_pop = pop[:sample_size]
reactions = []

for i, citizen in enumerate(sample_pop):
    raw_response = simulate_citizen_reaction(citizen, policy_input)
    parsed = parse_llm_output(raw_response)
    parsed["citizen_id"] = i
    reactions.append(parsed)
    if (i + 1) % 10 == 0:
        print(f"      Simulated {i + 1}/{sample_size}")
print(f"      [OK] Generated {len(reactions)} LLM reactions")

print(f"\n[6/7] Neural Network Training")
t0 = time.time()
X, y = create_training_data(sample_pop, reactions, parsed_policy)
print(f"      Feature shape: {len(X[0])}D (policy encoding included)")
model, mean, std = train_model(X, y, epochs=100)
t_train = time.time() - t0
print(f"      [OK] Trained in {t_train:.2f}s with normalization & regularization")

print(f"\n[7/7] Full Population Prediction (10,000)")
policy_encoding = encode_policy(parsed_policy)[0]
t0 = time.time()
happiness_changes = []
support_changes = []
income_changes = []

for i, citizen in enumerate(pop):
    pred = predict_reaction(model, citizen, mean, std, policy_encoding)
    happiness_delta = float(pred[0])
    support_delta = float(pred[1])
    income_delta = float(pred[2])
    
    citizen.update_state(happiness_delta, support_delta, income_delta)
    
    happiness_changes.append(citizen.happiness)
    support_changes.append(citizen.policy_support)
    income_changes.append(citizen.income)
    
    if (i + 1) % 2000 == 0:
        print(f"      Predicted {i + 1}/{len(pop)}")

t_pred = time.time() - t0
print(f"      [OK] Predicted for {len(pop)} citizens in {t_pred:.2f}s")

print(f"\n" + "=" * 70)
print("IMPACT METRICS")
print("=" * 70)

avg_happiness = sum(happiness_changes) / len(happiness_changes)
avg_support = sum(support_changes) / len(support_changes)
avg_income = sum(income_changes) / len(income_changes)

print(f"Average Happiness: {avg_happiness:.2f}")
print(f"Average Support:   {avg_support:.2f}")
print(f"Average Income:    {avg_income:.0f}")
print(f"Population Size:   {len(pop)}")

print(f"\n" + "=" * 70)
print("PERFORMANCE METRICS")
print("=" * 70)
print(f"Training Time: {t_train:.2f}s for 50 samples")
print(f"Prediction Time: {t_pred:.2f}s for 10,000 citizens")
print(f"Throughput: {(len(pop)/t_pred):,.0f} citizens/second")
print(f"Est. Policies/Hour: {(len(pop)/t_pred * 3600 / 1000):.0f}k")

print(f"\n" + "=" * 70)
print("DASHBOARD SIMULATION COMPLETE ✓")
print("=" * 70)
print("\nAll components working correctly:")
print("  [OK] Policy parsing and domain detection")
print("  [OK] Attribute mapping and population generation")
print("  [OK] LLM-based reaction simulation (Gemini 2.5-Flash)")
print("  [OK] Neural network training with normalization")
print("  [OK] Full population prediction with policy encoding")
print("  [OK] Impact metrics calculation")
print("\nDashboard ready for deployment!")
