from ai_models.llm_interface import simulate_population_reactions
from population.population_generator import generate_population

pop = generate_population(20, ['caste', 'student_status'])
reactions, sample = simulate_population_reactions(
    pop,
    'Increase scholarships for OBC students in rural areas',
    sample_size=20
)

print(f'Reactions collected: {len(reactions)}')
print()

for i, (r, c) in enumerate(zip(reactions[:3], sample[:3])):
    print(f'Citizen {i+1} — {c.occupation}, {c.caste}, {c.location}, income Rs{c.income:,}')
    print(f'  Happiness : {r["happiness_change"]}')
    print(f'  Support   : {r["support_change"]}')
    print(f'  Income d  : Rs{int(r["income_change"]):,}')
    print(f'  Diary     : {r["diary_entry"]}')
    print()