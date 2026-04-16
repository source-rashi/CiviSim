import os
import sys
import time
import uuid
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from ai_models.llm_interface import (
    generate_policy_recommendation,
    get_runtime_mode,
    simulate_population_reactions,
)
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


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _build_fallback_recommendation(final_metrics: Dict[str, float]) -> Dict[str, Any]:
    final_happiness = float(final_metrics.get("final_happiness", 0.0))
    final_support = float(final_metrics.get("final_support", 0.0))
    income_change = float(final_metrics.get("income_change", 0.0))
    happiness_delta = float(final_metrics.get("happiness_trend_delta", 0.0))
    support_delta = float(final_metrics.get("support_trend_delta", 0.0))

    if final_support >= 0.62 and final_happiness >= 0.58 and income_change >= 0:
        recommendation = "implement"
        confidence = _clamp(0.58 + final_support * 0.22 + final_happiness * 0.2, 0.0, 0.94)
        reasoning = (
            "Population-level support and wellbeing are both positive, with no average income decline. "
            "The simulation indicates strong near-term acceptance and manageable downside risk."
        )
        conditions: List[str] = []
    elif final_support >= 0.5 and final_happiness >= 0.5:
        recommendation = "conditional"
        confidence = _clamp(0.5 + final_support * 0.15 + final_happiness * 0.15, 0.0, 0.86)
        reasoning = (
            "The policy shows mixed but promising signals. "
            "A staged rollout with monitoring is advisable before full implementation."
        )
        conditions = [
            "Run a pilot in high-impact districts before scaling.",
            "Track support and income indicators for at least one full cycle.",
        ]
    else:
        recommendation = "do_not_implement"
        confidence = _clamp(0.52 + (1.0 - max(final_support, final_happiness)) * 0.35, 0.0, 0.9)
        reasoning = (
            "Support or wellbeing outcomes are insufficient under current design assumptions. "
            "The policy should be redesigned before deployment."
        )
        conditions = [
            "Rework targeting to reduce adverse effects on vulnerable groups.",
            "Re-test with revised incentives and safeguards.",
        ]

    key_risks: List[str] = []
    if final_support < 0.5:
        key_risks.append("Weak public support may create implementation friction.")
    if final_happiness < 0.5:
        key_risks.append("Projected wellbeing uplift is below desirable threshold.")
    if income_change < 0:
        key_risks.append("Average income trajectory declines under current configuration.")
    if support_delta < 0:
        key_risks.append("Support trend deteriorates over time.")
    if happiness_delta < 0:
        key_risks.append("Happiness trend deteriorates over time.")

    return {
        "recommendation": recommendation,
        "confidence_score": float(round(confidence, 4)),
        "reasoning": reasoning,
        "key_risks": key_risks,
        "conditions": conditions,
        "source": "heuristic",
    }


def _resolve_recommendation(
    policy_text: str,
    parsed_policy: Dict[str, Any],
    final_metrics: Dict[str, float],
    population_stats_data: Dict[str, Any],
) -> Dict[str, Any]:
    recommendation = generate_policy_recommendation(
        policy_text,
        parsed_policy,
        final_metrics,
        population_stats_data,
    )

    if recommendation and recommendation.get("recommendation") in {
        "implement",
        "conditional",
        "do_not_implement",
    }:
        return recommendation

    return _build_fallback_recommendation(final_metrics)


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
        model, mean, std, training_diagnostics = train_model(
            X,
            y,
            epochs=request.training_epochs,
            return_metrics=True,
        )
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

        avg_income_start = round(income_trend[0], 2) if income_trend else 0.0
        avg_income_end = round(income_trend[-1], 2) if income_trend else 0.0

        population_stats_data = {
            "total": len(population),
            "occupations": occupation_distribution(population),
            "castes": caste_distribution(population),
            "avg_income_start": avg_income_start,
            "avg_income_end": avg_income_end,
        }

        final_metrics = {
            "final_happiness": happiness_trend[-1] if happiness_trend else 0.0,
            "final_support": support_trend[-1] if support_trend else 0.0,
            "income_start": income_trend[0] if income_trend else 0.0,
            "income_end": income_trend[-1] if income_trend else 0.0,
            "income_change": (income_trend[-1] - income_trend[0]) if len(income_trend) >= 2 else 0.0,
            "happiness_trend_delta": (happiness_trend[-1] - happiness_trend[0]) if len(happiness_trend) >= 2 else 0.0,
            "support_trend_delta": (support_trend[-1] - support_trend[0]) if len(support_trend) >= 2 else 0.0,
        }

        recommendation = _resolve_recommendation(
            policy_text,
            parsed_policy,
            final_metrics,
            population_stats_data,
        )

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
            "population_stats": population_stats_data,
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
                "recommendation": recommendation.get("recommendation", "conditional"),
                "recommendation_confidence": recommendation.get("confidence_score", 0.5),
                "recommendation_reasoning": recommendation.get("reasoning", "No recommendation rationale available."),
                "recommendation_key_risks": recommendation.get("key_risks", []),
                "recommendation_conditions": recommendation.get("conditions", []),
                "recommendation_source": recommendation.get("source", "heuristic"),
            },
            "pipeline": {
                "run_id": str(uuid.uuid4()),
                "llm_mode": get_runtime_mode(),
                "population_size": request.population_size,
                "sample_size": len(sample_population),
                "steps": request.steps,
                "training_epochs": request.training_epochs,
                "batch_size": int(os.getenv("GROQ_BATCH_SIZE", "10")),
                "sample_strategy": "random_without_replacement",
                "model_validation": training_diagnostics,
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
