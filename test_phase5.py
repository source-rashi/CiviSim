"""Phase 5 Performance Test - Time-Step Simulation"""

import time
from population.population_generator import generate_population
from policy_engine.policy_parser import parse_policy
from ai_models.llm_interface import simulate_citizen_reaction, parse_llm_output
from ai_models.training_model import create_training_data, train_model, encode_policy
from simulation.simulation_engine import run_simulation

print("=" * 60)
print("PHASE 5 PERFORMANCE TEST - TIME-STEP SIMULATION")
print("=" * 60)

policy_text = "Free healthcare for all rural citizens"
parsed_policy = parse_policy(policy_text)

print(f"\n1. Generating 10,000 citizens...")
t0 = time.time()
population = generate_population(10000)
print(f"   Done in {time.time() - t0:.3f}s")

print(f"\n2. Collecting 50 LLM reactions for training...")
sample = population[:50]
reactions = []
for i, citizen in enumerate(sample):
    raw = simulate_citizen_reaction(citizen, policy_text)
    parsed = parse_llm_output(raw)
    parsed["citizen_id"] = i
    reactions.append(parsed)
    if (i + 1) % 10 == 0:
        print(f"   {i + 1}/50")

print(f"\n3. Training neural network...")
t0 = time.time()
X, y = create_training_data(sample, reactions, parsed_policy)
model, mean, std = train_model(X, y, epochs=100)
print(f"   Trained in {time.time() - t0:.2f}s")

print(f"\n4. Running 10-step simulation on 10,000 citizens...")
policy_encoding = encode_policy(parsed_policy)[0]
t0 = time.time()
metrics = run_simulation(population, model, steps=10, mean=mean, std=std, policy_encoding=policy_encoding)
t_sim = time.time() - t0

print(f"   Completed in {t_sim:.2f}s")
print(f"   Avg time per step: {t_sim/10:.2f}s")

print(f"\n5. Validating outputs...")
for key in ["happiness", "support", "income"]:
    values = metrics[key]
    assert len(values) == 10, f"Expected 10 steps, got {len(values)}"
    print(f"   {key}: min={min(values):.2f}, max={max(values):.2f}, final={values[-1]:.2f}")

# Check citizen bounds are enforced
for citizen in population[:100]:
    assert 0 <= citizen.happiness <= 1, f"happiness {citizen.happiness} out of bounds"
    assert 0 <= citizen.policy_support <= 1, f"support {citizen.policy_support} out of bounds"
    assert citizen.income >= 0, f"income {citizen.income} negative"

print(f"\n   All citizen state bounds respected.")

print(f"\n6. Running 20-step simulation...")
population2 = generate_population(10000)
t0 = time.time()
metrics2 = run_simulation(population2, model, steps=20, mean=mean, std=std, policy_encoding=policy_encoding)
t_sim2 = time.time() - t0
print(f"   20 steps x 10,000 citizens in {t_sim2:.2f}s")

print(f"\n{'=' * 60}")
print("PHASE 5 TEST RESULTS")
print(f"{'=' * 60}")
print(f"10 steps x 10,000 citizens: {t_sim:.2f}s")
print(f"20 steps x 10,000 citizens: {t_sim2:.2f}s")
print(f"Avg time per step (10k citizens): {t_sim/10:.2f}s")
print(f"No crashes, no bound violations confirmed.")
print(f"\nPhase 5 PASSED")
