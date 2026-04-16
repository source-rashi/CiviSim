import os
import sys
import time
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from ai_models.llm_interface import get_runtime_mode, simulate_population_reactions
from ai_models.training_model import create_training_data, encode_policy, train_model
from policy_engine.policy_mapper import map_policy_to_attributes
from policy_engine.policy_parser import parse_policy
from population.population_generator import generate_population
from simulation.simulation_engine import run_simulation
from utils.metrics import caste_distribution, occupation_distribution

app = FastAPI()


default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

configured_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins or default_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PolicyRequest(BaseModel):
    policy: str = Field(..., min_length=3, max_length=3000)
    population_size: int = Field(default=3000, ge=200, le=20000)
    sample_size: int = Field(default=120, ge=20, le=600)
    steps: int = Field(default=12, ge=3, le=80)
    training_epochs: int = Field(default=80, ge=20, le=500)


class PipelineTimings(BaseModel):
    parse_policy_ms: float
    map_attributes_ms: float
    population_generation_ms: float
    llm_sampling_ms: float
    model_training_ms: float
    simulation_ms: float
    total_ms: float


class PopulationStats(BaseModel):
    total: int
    occupations: Dict[str, int]
    castes: Dict[str, int]
    avg_income_start: float
    avg_income_end: float


class ReactionPreview(BaseModel):
    citizen_id: int
    occupation: str
    location: str
    happiness_change: float
    support_change: float
    income_change: float
    diary_entry: str


class SimulationResponse(BaseModel):
    happiness_trend: List[float]
    support_trend: List[float]
    income_trend: List[float]
    population_stats: PopulationStats
    policy_analysis: Dict[str, Any]
    pipeline: Dict[str, Any]
    reaction_preview: List[ReactionPreview]


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "llm_mode": get_runtime_mode(),
    }


@app.post("/api/simulate", response_model=SimulationResponse)
async def simulate(request: PolicyRequest):
    policy_text = request.policy.strip()
    if not policy_text:
        raise HTTPException(status_code=400, detail="Policy cannot be empty.")

    request_start = time.perf_counter()

    try:
        step_start = time.perf_counter()
        parsed_policy = parse_policy(policy_text)
        parse_policy_ms = (time.perf_counter() - step_start) * 1000

        step_start = time.perf_counter()
        attributes = map_policy_to_attributes(parsed_policy)
        map_attributes_ms = (time.perf_counter() - step_start) * 1000

        step_start = time.perf_counter()
        population = generate_population(request.population_size, attributes)
        population_generation_ms = (time.perf_counter() - step_start) * 1000

        step_start = time.perf_counter()
        safe_sample_size = min(request.sample_size, len(population))
        reactions, sample_population = simulate_population_reactions(
            population,
            policy_text,
            sample_size=safe_sample_size,
        )
        llm_sampling_ms = (time.perf_counter() - step_start) * 1000

        if not reactions or not sample_population:
            raise HTTPException(
                status_code=500,
                detail="No reaction data generated. Check Groq configuration and retry.",
            )

        step_start = time.perf_counter()
        X, y = create_training_data(sample_population, reactions, parsed_policy)
        model, mean, std = train_model(X, y, epochs=request.training_epochs)
        model_training_ms = (time.perf_counter() - step_start) * 1000

        step_start = time.perf_counter()
        policy_encoding = encode_policy(parsed_policy)[0]
        metrics = run_simulation(
            population,
            model,
            request.steps,
            mean,
            std,
            policy_encoding,
        )
        simulation_ms = (time.perf_counter() - step_start) * 1000

        total_ms = (time.perf_counter() - request_start) * 1000

        happiness_trend = [float(value) for value in metrics["happiness"]]
        support_trend = [float(value) for value in metrics["support"]]
        income_trend = [float(value) for value in metrics["income"]]

        preview: List[ReactionPreview] = []
        for citizen, reaction in list(zip(sample_population, reactions))[:5]:
            preview.append(
                ReactionPreview(
                    citizen_id=int(citizen.cid),
                    occupation=str(citizen.occupation),
                    location=str(citizen.location),
                    happiness_change=float(reaction.get("happiness_change", 0.0)),
                    support_change=float(reaction.get("support_change", 0.0)),
                    income_change=float(reaction.get("income_change", 0.0)),
                    diary_entry=str(reaction.get("diary_entry", "")),
                )
            )

        pipeline_timings = PipelineTimings(
            parse_policy_ms=round(parse_policy_ms, 2),
            map_attributes_ms=round(map_attributes_ms, 2),
            population_generation_ms=round(population_generation_ms, 2),
            llm_sampling_ms=round(llm_sampling_ms, 2),
            model_training_ms=round(model_training_ms, 2),
            simulation_ms=round(simulation_ms, 2),
            total_ms=round(total_ms, 2),
        )

        response: Dict[str, Any] = {
            "happiness_trend": happiness_trend,
            "support_trend": support_trend,
            "income_trend": income_trend,
            "population_stats": {
                "total": len(population),
                "occupations": occupation_distribution(population),
                "castes": caste_distribution(population),
                "avg_income_start": round(income_trend[0], 2),
                "avg_income_end": round(income_trend[-1], 2),
            },
            "policy_analysis": {
                "domain": parsed_policy.get("domain", "general"),
                "mechanism": parsed_policy.get("mechanism", "general"),
                "time_effect": parsed_policy.get("time_effect", "gradual"),
                "summary": parsed_policy.get("summary", policy_text),
                "affected_groups": parsed_policy.get("affected_groups", []),
                "key_attributes": parsed_policy.get("key_attributes", []),
                "potential_winners": parsed_policy.get("potential_winners", []),
                "potential_losers": parsed_policy.get("potential_losers", []),
                "parsed_by": parsed_policy.get("parsed_by", "keyword_fallback"),
            },
            "pipeline": {
                "llm_mode": get_runtime_mode(),
                "population_size": request.population_size,
                "sample_size": len(sample_population),
                "steps": request.steps,
                "training_epochs": request.training_epochs,
                "batch_size": int(os.getenv("GROQ_BATCH_SIZE", "10")),
                "timings_ms": pipeline_timings.dict(),
            },
            "reaction_preview": [entry.dict() for entry in preview],
        }

        return response

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {exc}") from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
