from policy_engine.policy_parser import parse_policy
from policy_engine.policy_mapper import map_policy_to_attributes
from population.population_generator import generate_population

test_policies = [
    'Increase scholarships for students',
    'Reduce tax for middle class',
    'Subsidy for farmers'
]

for i, policy_text in enumerate(test_policies, 1):
    print(f'\n--- Policy {i}: {policy_text} ---')
    
    parsed = parse_policy(policy_text)
    attributes = map_policy_to_attributes(parsed)
    
    print(f'Domain: {parsed["domain"]}')
    print(f'Attributes: {attributes}')
    
    pop = generate_population(1000, attributes)
    print(f'Generated {len(pop)} citizens')
    print(f'Sample citizen extra attributes: {pop[0].extra_attributes}')

print('\n✓ All tests passed!')
