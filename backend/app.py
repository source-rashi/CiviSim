import os
import sys
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from civisim.policy_engine.policy_parser import parse_policy
from civisim.population.population_generator import generate_population

app = FastAPI()

default_origins = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]

configured_origins = [
    origin.strip()
    for origin in os.getenv('CORS_ORIGINS', '').split(',')
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins or default_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

class PolicyRequest(BaseModel):
    policy: str

@app.post("/api/simulate")
async def simulate(request: PolicyRequest):
    if not request.policy or not request.policy.strip():
        raise HTTPException(status_code=400, detail='Policy cannot be empty.')

    try:
        # Parse policy (for now, just acknowledge)
        _parsed_policy = parse_policy(request.policy)

        # Generate population
        population = generate_population(100)

        # Mock results for now
        results: Dict[str, Any] = {
            'happiness_trend': [0.5, 0.6, 0.7, 0.8, 0.9, 0.85, 0.9, 0.95, 0.92, 0.88],
            'support_trend': [0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.82, 0.78],
            'population_stats': {
                'total': len(population),
                'occupations': {},
            },
        }
        return results
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Simulation failed: {exc}') from exc

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)