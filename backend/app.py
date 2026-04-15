from fastapi import FastAPI
from pydantic import BaseModel
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from civisim.simulation.simulation_engine import run_simulation
from civisim.policy_engine.policy_parser import parse_policy
from civisim.population.population_generator import generate_population

app = FastAPI()

class PolicyRequest(BaseModel):
    policy: str

@app.post("/api/simulate")
async def simulate(request: PolicyRequest):
    # Parse policy (for now, just acknowledge)
    parsed_policy = parse_policy(request.policy)
    
    # Generate population
    population = generate_population(100)
    
    # Mock results for now
    results = {
        "happiness_trend": [0.5, 0.6, 0.7, 0.8, 0.9, 0.85, 0.9, 0.95, 0.92, 0.88],
        "support_trend": [0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.82, 0.78],
        "population_stats": {
            "total": len(population),
            "occupations": {}  # Can add more
        }
    }
    
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)