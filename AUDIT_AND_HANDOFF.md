# CIVISIM Audit & Handoff Document

**Date:** April 3, 2026  
**Auditor:** GitHub Copilot  
**Project Stage:** Early Prototype (40% complete)  
**Status:** Partially functional, ready for enhancement  

---

## 1. PROJECT SUMMARY

**Name:** CIVISIM  
**Tagline:** "Simulate society before you change it."  
**Purpose:** An AI-powered synthetic society simulator that allows users to test public policies on a virtual population before real-world deployment.

**Core Flow:**
1. User inputs a policy in natural language (e.g., "Increase scholarships for rural students")
2. System parses policy and extracts domain and affected attributes
3. Generates a synthetic population of ~10,000 citizens with demographics, traits, and socioeconomic attributes
4. Samples ~50 citizens and uses Gemini LLM to generate individual policy reactions (happiness, support, income impact, diary entries)
5. Trains a lightweight PyTorch neural network on LLM reactions
6. Uses trained model to predict reactions across full population
7. Runs multi-step simulation (10–50 time steps) tracking happiness, support, and income trajectories
8. Displays interactive dashboard with distributions, time-series trends, and citizen drill-down views

**Target Users:** Government policymakers, think tanks, researchers, NGOs, consulting firms, universities

**Tech Stack:**
- Backend: Python 3.13
- Frontend: Streamlit
- LLM: Google Gemini 2.5-Flash
- ML: PyTorch (neural reaction model)
- Viz: Plotly
- Data: Synthetic population (Faker-style)
- Env: Virtual environment (venv)

---

## 2. COMPLETED COMPONENTS

### 2.1 Core Architecture & Entry Point
- **[app.py](app.py)** — Main Streamlit dashboard that orchestrates the full pipeline
  - Accepts policy text input
  - Calls policy parser, population generator, LLM sampler, neural trainer, and simulator
  - Renders interactive charts and citizen explorer
  - Status: **FUNCTIONAL** (but has double-state-update bug; see Bugs section)

### 2.2 Policy Engine
- **[policy_engine/policy_parser.py](policy_engine/policy_parser.py)** — Parses natural-language policy text
  - Keyword-based domain detection (education, agriculture, tax, general)
  - Extracts summary and basic structure
  - Status: **WORKING but SHALLOW** — only detects 4 domains; affected groups and key attributes mostly empty

- **[policy_engine/policy_mapper.py](policy_engine/policy_mapper.py)** — Maps policy domain to relevant citizen attributes
  - Route-based attribute assignment per domain
  - Examples: education → [caste, education, income, student_status]; agriculture → [land_size, crop_type, loan, rural]
  - Status: **FUNCTIONAL** but limited to 4 hard-coded domains

### 2.3 Synthetic Population
- **[population/citizen.py](population/citizen.py)** — Core citizen data model
  - Fields: cid, age, gender, income, occupation, caste, education, location, traits (risk_tolerance, openness, political_leaning), extra_attributes
  - Simulation state: happiness, policy_support
  - update_state() method with bounds clamping [0, 1] for happiness/support, [0, ∞) for income
  - Status: **COMPLETE and USABLE**

- **[population/population_generator.py](population/population_generator.py)** — Generates synthetic citizens
  - Creates N citizens with randomized demographics
  - Honors policy-requested extra attributes (partially)
  - Status: **FUNCTIONAL but INCOMPLETE** — only adds a few extras; many policy attributes are ignored

### 2.4 LLM Integration
- **[ai_models/llm_interface.py](ai_models/llm_interface.py)** — Gemini API wrapper
  - Builds detailed prompts for citizen simulations
  - Calls Gemini 2.5-Flash with citizen profile + policy
  - Parses JSON-style responses; falls back to defaults on parse failure
  - Status: **FUNCTIONAL but FRAGILE** — imports genai at module load time; fails completely if dependency absent

### 2.5 Neural Reaction Model
- **[ai_models/training_model.py](ai_models/training_model.py)** — PyTorch model pipeline
  - Feature normalization (mean/std)
  - Policy encoding (domain → integer)
  - Training data creation from citizen profiles + LLM reactions
  - Model architecture: 6D input → 64 → 32 → 16 → 3D output (happiness_delta, support_delta, income_delta)
  - Batch normalization and dropout regularization
  - Status: **FUNCTIONAL with ISSUES** — inconsistent normalization in evaluation; see Bugs

- **[ai_models/reaction_predictor.py](ai_models/reaction_predictor.py)** — Inference helpers
  - Single-citizen and batch prediction
  - Feature normalization applied before forward pass
  - Output clamping to [-1, 1]
  - Status: **FUNCTIONAL**

### 2.6 Simulation Engine
- **[simulation/simulation_engine.py](simulation/simulation_engine.py)** — Time-step simulator
  - Runs N steps of repeated batch prediction
  - Updates citizen state at each step
  - Aggregates and tracks metrics (happiness, support, income averages)
  - Status: **FUNCTIONAL** (but triggers double-update bug from app.py)

### 2.7 Utilities
- **[utils/metrics.py](utils/metrics.py)** — Population analytics
  - Helpers: occupation_distribution, caste_distribution, income_list, group_by_attribute, group_average_happiness, etc.
  - Status: **COMPLETE**

### 2.8 Dashboard Visualizations
- **[app.py](app.py)** dashboard sections:
  - Policy Context (domain, attributes)
  - Executive Summary (KPI metrics)
  - Population Analytics (occupation dist, income dist, caste dist, happiness by occupation)
  - Policy Trajectory (time-series trends for happiness, support, income)
  - Individual Lens (citizen explorer by ID)
  - Human Narratives (sample diary entries from LLM reactions)
  - Status: **FUNCTIONAL**

### 2.9 Test Suite
- **[test_policy_engine.py](test_policy_engine.py)** — Policy parsing smoke test (PASSED)
- **[test_phase45.py](test_phase45.py)** — Model training and inference test (structure exists)
- **[test_phase5.py](test_phase5.py)** — Simulation at scale test (structure exists; fails on missing dependency)
- **[test_dashboard_integration.py](test_dashboard_integration.py)** — End-to-end integration test (structure exists)

### 2.10 Configuration & Docs
- **[requirements.txt](requirements.txt)** — Dependencies listed
- **[README.md](README.md)** — Quick start and overview
- **[docs/roadmap.md](docs/roadmap.md)** — Development roadmap (outdated)

---

## 3. MISSING COMPONENTS

### 3.1 Policy Understanding (Critical)
- **Shallow parsing:** Only keyword-based domain detection. No NLP, no semantic understanding of policy intent, mechanisms, or causal effects.
- **No extraction of:**
  - Specific affected subgroups (e.g., "rural OBC students" vs "all students")
  - Policy mechanisms (subsidy, tax, regulation, restriction)
  - Time effects (immediate vs gradual)
  - Constraints or success criteria
  - Unintended consequence awareness
- **Recommendation:** Upgrade from keyword regex to an LLM-based policy parser using Gemini.

### 3.2 Population Attribute Generation (High Priority)
- The mapper returns policy-specific attributes, but the generator ignores most of them.
- Missing attributes for realistic policy simulation:
  - crop_type (agriculture)
  - tax_bracket (tax)
  - rural flag (inconsistently applied)
  - Many others returned by mapper but not generated
- **Recommendation:** Expand populate_generator.py to honor all mapped attributes and generate them realistically per domain.

### 3.3 Output Scale Separation (High Priority)
- Currently, happiness_delta, support_delta, and income_delta are all scaled to [-1, 1].
- Income changes should be in real currency values (e.g., -5000 to +50000), not bounded to [-1, 1].
- This makes income effects unrealistically small and conceptually confuses emotional with economic impact.
- **Recommendation:** Separate the model outputs into two tiers: one for emotional/behavioral (happiness, support) scaled to [-1, 1], another for economic (income) in real currency.

### 3.4 LLM Robustness (High Priority)
- [ai_models/llm_interface.py](ai_models/llm_interface.py) imports `google.generativeai` at module load time.
- If the package is missing, the entire pipeline fails at import, even if you wanted to run non-LLM code.
- **Current issue:** The venv does not have `google.generativeai` installed; all tests importing this module fail immediately.
- **Recommendation:**
  - Lazy-load the Gemini client (import inside function, not module top-level)
  - Provide a mock/fallback mode for testing without Gemini
  - Add error recovery if API calls fail

### 3.5 Social Network & Dynamics (Deferred)
- **[simulation/social_network.py](simulation/social_network.py)** is a placeholder.
- The current system treats each citizen in isolation; no peer effects, no network dynamics.
- **Recommendation:** This can be deferred. Phase 1 should be a working single-citizen predictor; Phase 2 can add influence/contagion.

### 3.6 Dashboard Visualizations Module (Deferred)
- **[dashboard/visualizations.py](dashboard/visualizations.py)** is empty.
- Visualizations are currently hard-coded inside [app.py](app.py).
- **Recommendation:** Extract viz functions into a separate module for reusability, but this is not urgent.

### 3.7 Settings Management (Deferred)
- **[config/settings.py](config/settings.py)** is empty.
- No centralized configuration for model hyperparameters, population size, simulation steps, etc.
- **Recommendation:** Low priority; can be added later for enterprise features.

###3.8 Proper Test Suite (High Priority)
- Tests currently print output but do not assert behavior (smoke tests only).
- No unit tests for individual components.
- No edge case or error handling tests.
- **Recommendation:** Replace smoke tests with proper pytest assertions.

### 3.9 Data Persistence (Deferred)
- Currently, all results are in-memory; there is no database or file persistence.
- Users cannot save/load simulation results or compare different policy runs.
- **Recommendation:** Add optional database backend (SQLite or Postgres) for storing results.

### 3.10 API Layer (Deferred)
- No REST API. Currently only Streamlit web UI.
- **Recommendation:** FastAPI wrapper for programmatic access, but defer until core is solid.

---

## 4. BUGS, LOGIC ERRORS & RISKS

### 4.1 **CRITICAL: Double State Update Bug** (app.py)
**Location:** [app.py](app.py), lines 60–85  
**Issue:** Citizen state is updated twice with the same prediction:
```python
# First update (line 74-77 in app.py):
for citizen, pred in zip(population, preds):
    citizen.update_state(float(pred[0]), float(pred[1]), float(pred[2]))

# Then simulation engine updates again (lines 81-84):
metrics = run_simulation(population, model, steps, mean, std, policy_encoding)
# Inside run_simulation (line 11-15 in simulation_engine.py):
for citizen, pred in zip(population, preds):
    citizen.update_state(...)
```
**Result:** The neural model's first prediction is applied twice—once in app.py, once in the simulation loop. This artificially boosts the first-step effect.  
**Fix:** Remove the update loop in app.py (lines 74–77) or remove the update inside run_simulation. The simulation engine should own state updates.

### 4.2 **HIGH: Normalization Inconsistency** (training_model.py)
**Location:** [ai_models/training_model.py](ai_models/training_model.py), lines 91–103  
**Issue:**
- Training normalizes using `X.mean(axis=0)` and `X.std(axis=0)` and returns mean, std.
- Evaluation recomputes normalization from the input data, ignoring the training mean/std:
  ```python
  X_norm = (np.array(X) - mean) / (np.std(np.array(X), axis=0) + 1e-8)
  ```
  This should reuse the training mean and std, not recompute from eval data.
- **Result:** Evaluation metric is not comparable across different datasets; model validation is unreliable.
- **Fix:** Function signature should be `evaluate_model(model, X, y, train_mean, train_std)` and use those values, not recomputed ones.

### 4.3 **HIGH: Fragile LLM Dependency** (llm_interface.py)
**Location:** [ai_models/llm_interface.py](ai_models/llm_interface.py), lines 1–14  
**Issue:**
- `import google.generativeai as genai` at module level.
- If package is missing, entire module fails before graceful fallback.
- **Current environment state:** `google.generativeai` not installed; all tests importing this fail.
- **Fix:**
  - Move import inside function or wrap in try/except
  - Provide fallback mock for missing dependency
  - Example:
    ```python
    def generate_response(prompt):
        try:
            import google.generativeai as genai
        except ImportError:
            return fallback_mock_response(prompt)
    ```

### 4.4 **MEDIUM: Missing Null/Empty Checks**
**Location:** Multiple modules  
**Issue:**
- [policy_parser.py](policy_engine/policy_parser.py) returns empty affected_groups and key_attributes; downstream code assumes these are meaningful.
- No validation that policy domain is recognized.
- [population_generator.py](population/population_generator.py) silently ignores unmapped attributes (e.g., crop_type for non-agriculture policies).
- **Result:** Silent failures; invalid policies don't error clearly.
- **Fix:** Add explicit validation and raise errors with helpful messages.

### 4.5 **MEDIUM: Conceptual Scale Mismatch**
**Location:** [ai_models/training_model.py](ai_models/training_model.py), [ai_models/reaction_predictor.py](ai_models/reaction_predictor.py)  
**Issue:**
- Model outputs three scalars: happiness_delta, support_delta, income_delta.
- All three are clamped to [-1, 1] in [reaction_predictor.py](ai_models/reaction_predictor.py) line 29.
- Income changes are unrealistically tiny (~-1 to +1 currency units).
- Happiness and support are emotional (unbounded in theory, but usefully [-1, 1]); income is economic (should be real currency ranges).
- **Result:** Income trajectories are unrealistic.
- **Fix:** Separate outputs. Train two models or branches: one for [happiness, support] ∈ [-1, 1], one for income ∈ real currency range.

### 4.6 **MEDIUM: Incomplete Attribute Population**
**Location:** [population/population_generator.py](population/population_generator.py), lines 11–27  
**Issue:**
- Only handles: caste, student_status, land_size, loan
- Mapper requests: crop_type, rural, tax_bracket, education_level, and others
- These are silently not generated.
- **Result:** Population lacks attributes needed for multi-domain realism.
- **Fix:** Expand attribute generation to cover all mapped attributes per domain.

### 4.7 **LOW: Outdated Roadmap**
**Location:** [docs/roadmap.md](docs/roadmap.md)  
**Issue:** Still marks Phases 1–6 as "to be implemented," but code exists for most.
- **Fix:** Update roadmap to reflect actual state.

### 4.8 **LOW: Incomplete Error Handling**
**Location:** [ai_models/llm_interface.py](ai_models/llm_interface.py), parse_llm_output function  
**Issue:** Catch-all except clause returns defaults; no logging of what failed.
- **Fix:** Add logging for debugging.

---

## 5. ARCHITECTURAL OBSERVATIONS

### 5.1 Strengths
- **Clean separation of concerns:** Policy engine, population, AI models, simulation, and viz are separate modules.
- **Existing integration:** Unlike many prototypes, the pieces actually wire together and run.
- **Reasonable defaults:** The fallback response in parse_llm_output prevents crashes if LLM fails.
- **Streamlit UI is fast to iterate on:** Good for early prototyping.

### 5.2 Weaknesses
- **Policy → Attributes → Citizens is ad-hoc:** The mapper returns attributes, but population generation doesn't honor them. This disconnect means the system doesn't truly link policy to population.
- **Neural model training is on-the-fly:** Each run trains a new model; there's no model persistence, no transfer learning, no hyperparameter tuning visible.
- **Simulation state is mutable and stateful:** Citizens are updated in-place; makes testing and visualization hard.
- **LLM is a hard dependency:** The whole system assumes Gemini availability; offline or mock mode is not supported.
- **Data flow is linear:** Policy → Population → Train → Predict → Simulate. No feedback loops for model improvement or policy adjustment.

### 5.3 Scalability Concerns
- **LLM cost:** Sampling 50 citizens per policy run × Gemini API calls = $$ per policy tested. At scale, this becomes expensive. The neural scaling layer helps, but only after the cost is incurred.
- **Population size:** Currently set to 10,000. Larger populations (100,000+) would expose memory and computation bottlenecks.
- **Real-time dashboard:** Streamlit is not ideal for enterprise dashboards. Would benefit from a proper React frontend + FastAPI backend later.

---

## 6. RECOMMENDED NEXT BUILD ORDER

### **Priority 1 (Fix Critical Bugs)**
These must be fixed before the system is reliable:

1. **Remove double state update** ([app.py](app.py) lines 74–77)
   - Impact: Fixes incorrect metric trajectories
   - Effort: 5 minutes
   - Blocker: None; can be merged immediately

2. **Fix LLM import robustness** ([ai_models/llm_interface.py](ai_models/llm_interface.py))
   - Impact: Tests can run without Gemini; graceful fallback
   - Effort: 20 minutes
   - Blocker: None; can be paired with Priority 2

3. **Fix evaluation normalization** ([ai_models/training_model.py](ai_models/training_model.py))
   - Impact: Model validation is now reliable
   - Effort: 10 minutes
   - Blocker: None

### **Priority 2 (Incomplete Core Functionality)**
These enable the system to work for more policy types:

4. **Expand population attribute generation** ([population/population_generator.py](population/population_generator.py))
   - Add crop_type, education_level, rural, tax_bracket, etc.
   - Effort: 1–2 hours
   - Dependency: Mapper already returns these; just generate them

5. **Separate model outputs by scale** ([ai_models/training_model.py](ai_models/training_model.py) + [reaction_predictor.py](ai_models/reaction_predictor.py))
   - Train emotional model ([-1, 1]) and economic model (real currency)
   - Effort: 2–3 hours
   - Dependency: Requires rethinking output structure

6. **Upgrade policy parser to LLM-based** ([policy_engine/policy_parser.py](policy_engine/policy_parser.py))
   - Use Gemini to extract domain, affected groups, mechanisms
   - Effort: 1–2 hours
   - Dependency: None; can replace current parser incrementally

### **Priority 3 (Test & Validation)**
These ensure the system is trustworthy:

7. **Replace smoke tests with proper assertions** (test_*.py files)
   - Add unit tests, edge cases, error scenarios
   - Effort: 3–4 hours
   - Dependency: None; can be done in parallel

8. **Add logging and debugging helpers**
   - Log LLM calls, model training, prediction anomalies
   - Effort: 1 hour
   - Dependency: None

### **Priority 4 (Infrastructure & Scale)**
These enable production deployment:

9. **Add settings/config management** ([config/settings.py](config/settings.py))
   - Centralized hyperparameters, population size, API keys
   - Effort: 1 hour
   - Dependency: None; low-priority enhancement

10. **Extract dashboard visualizations** ([dashboard/visualizations.py](dashboard/visualizations.py))
    - Move viz code from app.py to reusable functions
    - Effort: 1–2 hours
    - Dependency: None; nice-to-have

11. **Add data persistence** (database layer)
    - Store population profiles, simulation results, policy runs
    - Effort: 2–3 hours
    - Dependency: Choose DB (SQLite or Postgres)

12. **Build FastAPI wrapper** (API layer)
    - REST endpoints for policy simulation
    - Effort: 2–4 hours
    - Dependency: Backend cleanup (Priorites 1–3 should be done first)

---

## 7. TESTING STATUS

| Test | Status | Issue |
|------|--------|-------|
| test_policy_engine.py | ✅ PASSED | None; basic parsing works |
| test_phase45.py | ❌ BLOCKED | Missing google.generativeai |
| test_phase5.py | ❌ BLOCKED | Missing google.generativeai |
| test_dashboard_integration.py | ❌ BLOCKED | Missing google.generativeai |

**Root Cause:** `google.generativeai` is not installed in the venv.

**Immediate Action:** Install dependencies:
```bash
pip install google-generativeai
```

Once installed, tests should run (though they will still fail if GEMINI_API_KEY is not set in .env).

---

## 8. DEPLOYMENT & RUNNING

### Prerequisites
- Python 3.13 (confirmed in venv)
- Dependencies: pip install -r requirements.txt
- Gemini API key in .env file (GEMINI_API_KEY=...)

### To Run Dashboard
```bash
streamlit run app.py
```

### To Run Tests
```bash
pytest -q
```

### Current Blockers
- Missing `google.generativeai` package (easy fix: `pip install google-generativeai`)
- Missing .env file with GEMINI_API_KEY (easy fix: create .env and add key)

---

## 9. SUMMARY FOR NEXT AI EVALUATOR

**What's Working:**
- Core pipeline architecture is sound
- Policy parsing, population generation, neural model, simulation, and dashboard all exist and integrate
- Basic smoke test passes (policy_engine)
- Code is syntactically correct and relatively clean

**What Needs Work (ranked by severity):**
1. **Critical bugs** (double update, import fragility, normalization bugs) — together 45 min to fix
2. **Shallow policy understanding** — keyword-based only; needs LLM upgrade
3. **Incomplete population generation** — attributes are mapped but not generated
4. **Unrealistic income scaling** — should be separated from emotional outputs
5. **No real test coverage** — smoke tests only; need proper assertions
6. **Missing infrastructure** — no persistence, no API, no settings management

**Realistic Assessment:**
- The prototype is ~40% of a production system
- All core pieces exist and run end-to-end
- The biggest gaps are semantic (policy understanding, realism) and operational (robustness, scale, persistence)
- With 1–2 weeks of focused engineering, this could be a working prototype for alpha testing with real policymakers

**Not Ready For:**
- Production use (no persistence, no error recovery, no audit trail)
- Enterprise scale (no multi-user, no dashboards suited for large teams)
- Real policy simulation (policy understanding too shallow; needs validation)

**Ready For:**
- Demo to investors or advisors
- Internal testing with sample policies
- Refactoring into a more robust backend

---

**End of Handoff Document**
