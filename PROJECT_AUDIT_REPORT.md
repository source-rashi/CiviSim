# CIVISIM — COMPLETE PROJECT AUDIT REPORT

**Date:** April 3, 2026  
**Auditor:** Senior Software Engineer & AI Architect  
**Project Stage:** Early-stage prototype with functional core

---

## EXECUTIVE SUMMARY

**Overall Assessment:** CIVISIM is a **working prototype with several strong architectural decisions** but **significant gaps in production readiness**, testing, and edge case handling.

**Bottom Line:**
- ✅ Core pipeline works end-to-end
- ✅ Recent improvements (LLM robustness, income scaling, normalization) are solid
- ❌ No test coverage, no error handling, no model validation
- ❌ Training on 50 samples is statistically insufficient
- ❌ Dashboard is feature-complete but lacks saving/comparison
- ⚠️ Several bugs lurking in type conversions and missing validations

---

## PART 1: COMPLETION STATUS BY MODULE

### 1. population/citizen.py
**Status:** ✅ COMPLETE

- Clean, minimal design
- State clamping is correct
- `update_state()` correctly bounds happiness/support to [0, 1] and income ≥ 0
- `to_dict()` is incomplete (only returns 5 fields, should serialize all)

**Issues:**
- Missing: Type hints
- Missing: `__repr__` or `__str__` for debugging

---

### 2. population/population_generator.py
**Status:** ✅ WELL IMPLEMENTED

- Excellent use of realistic India-context distributions
- Income derivation based on occupation + location is solid
- Extra attribute generation is comprehensive (15+ attributes supported)
- Proper use of weighted random choices for caste, education, health

**Strengths:**
- Defensive `.get()` calls with defaults
- Logging integration
- Realistic income bounds per occupation

**Issues:**
- ❌ **BUG:** Silently ignores unmapped attribute requests
  - If mapper requests `health_status` but generator doesn't recognize it, no error is raised
  - This can hide bugs silently
- Missing: Validation that all required attributes are actually generated

---

### 3. policy_engine/policy_parser.py
**Status:** ✅ WELL IMPLEMENTED

- **Dual-path architecture is excellent:**
  - Primary: LLM-based structured extraction
  - Fallback: keyword-based backup
- Prompt is well-designed and specific
- JSON parsing is robust with code fence stripping
- Logs failures clearly

**Strengths:**
- Handles Gemini unavailability gracefully
- Validates required keys in response
- Safe defaults on parse failure

**Issues:**
- ❌ **MISSING:** Health domain is NOT handled in `policy_mapper.py`
  - Parser extracts `"health"` domain but mapper doesn't map it
  - Fall-through to generic `["income", "occupation"]` = BUG
- Missing: Validation that policy domain matches supported domains

---

### 4. policy_engine/policy_mapper.py
**Status:** ❌ INCOMPLETE

- Only handles 3 domains (education, agriculture, tax)
- Generic fallback for unknown domains
- Hard-coded mappings with no flexibility

**Issues:**
- ❌ **CRITICAL:** Health domain from parser is not mapped
- ❌ Missing validation: should check if domain is recognized
- No error handling for unknown domains
- Strongly coupled to policy_parser assumptions

**Recommendation:**
```python
# Should add:
elif domain == "health":
    return ["health_status", "insurance", "income", "occupation"]
```

---

### 5. ai_models/llm_interface.py
**Status:** ✅ WELL IMPLEMENTED (RECENTLY UPGRADED)

- Great lazy-loading design (import only when needed)
- Excellent fallback mock generation
- New google-genai integration (deprecated package fixed)
- Proper error handling with logging

**Strengths:**
- Works with or without API key
- Realistic mock reactions (seeded by citizen.cid for consistency)
- Validates JSON response structure

**Issues:**
- ⚠️ Mock reactions are too simplistic
  - Income factor calculation: `(citizen.income - 10000) / 190000` assumes max income ~200k, which is unrealistic for India
  - Should use actual income distribution stats
- Missing: Timeout handling on API calls (Gemini might hang)
- Missing: Retry logic on API failures

---

### 6. ai_models/training_model.py
**Status:** ✅ WELL IMPLEMENTED

- Excellent normalization with saved mean/std
- `apply_normalization()` helper prevents recomputation bug
- Proper feature engineering (6D vector)
- Good model architecture: 6 → 64 → 32 → 16 → 3

**Strengths:**
- Fixed the normalization bug from earlier audit
- Uses BatchNorm and Dropout for regularization
- Logging for training progress

**CRITICAL ISSUES:**
- ❌ **No train/val/test split** — all 50 reactions used for both training and implied validation
- ❌ **Extremely small training set** (50 samples)
  - 6D input space with 50 data points = severe underfitting/overfitting risk
  - Model may memorize rather than generalize
- ❌ **No evaluation metrics** beyond MSE
  - No R² score, no MAE, no per-output analysis
- ❌ **Fixed hyperparameters**
  - epochs=100 is hardcoded in app.py
  - learning rate = 0.001 (no justification)
  - No hyperparameter tuning
- ❌ **No convergence check** — just trains for fixed epochs regardless of loss

**ML Recommendation:**
Need **at least 500 LLM reactions** for reliable training, or use:
- Early stopping on validation loss
- K-fold cross-validation
- Transfer learning from pre-trained models

---

### 7. ai_models/reaction_predictor.py
**Status:** ✅ WELL IMPLEMENTED (RECENTLY FIXED)

- Income scaling fixed (now 1.0 instead of 10_000)
- Proper normalization using `apply_normalization()`
- Batch prediction is efficient

**Recent Good Work:**
- Separated income_delta (rupees) from emotional outputs (scores)
- Returns tuples instead of numpy arrays for clarity

**Issues:**
- ❌ **TYPE MISMATCH:** Returns tuples but `simulation_engine.py` expects arrays
  ```python
  # predictor returns: (float, float, float)
  # but update_state expects: float(pred[0]), float(pred[1]), float(pred[2])
  ```
- Actually this works because tuples are subscriptable, but it's fragile
- Missing: Type hints would catch this

---

### 8. simulation/simulation_engine.py
**Status:** ✅ COMPLETE (CORRECT)

- Simple and correct timestep loop
- Batched predictions are efficient
- Metrics aggregation is straightforward

**Good:**
- Fixed the double-update bug from earlier

**Issues:**
- ❌ **No state validation**
  - Should check if mean/std are None
  - Should check if policy_encoding is None
- ❌ **No convergence detection**
  - Happiness/support might plateau, but simulation runs full steps anyway
  - Wastes computation
- Missing: Early stopping conditions

---

### 9. utils/metrics.py
**Status:** ✅ COMPLETE

- Simple, functional helper module
- All aggregations are correct

**Issues:**
- Mental: Average without checking population length (will crash if empty)
- Missing: Gini coefficient (mentioned in vision but not implemented)
- Missing: Inequality metrics
- Missing: Demographic breakdowns

---

### 10. dashboard/visualizations.py
**Status:** ❌ STUB / PLACEHOLDER

- File is literally just a comment: `# Dashboard Visualizations`
- All viz functions are hard-coded in app.py (code smell)

**Recommendation:**
Extract all `px.bar()`, `px.line()`, `px.pie()`, etc. into reusable functions.

---

### 11. app.py
**Status:** ✅ WELL STRUCTURED

- Good pipeline orchestration
- Clear section comments
- Proper error handling for empty input
- Nice KPI formatting with currency symbols

**Strengths:**
- Fixed double-update bug
- Reactive caching (runs full pipeline on button click)
- Good UX flow

**Issues:**
- ❌ **Hardcoded constants:**
  ```python
  population = generate_population(10000, attributes)  # hardcoded
  sample_size = min(50, len(population))              # hardcoded
  model, mean, std = train_model(X, y, epochs=100)    # hardcoded
  ```
- ❌ **No saving of results** — users can't export or compare
- ❌ **No error recovery**
  - If LLM fails, partial results shown
  - If training fails, no graceful degradation
- ❌ **No progress indication**
  - Users don't know if system is still running
  - API calls can take 50-100 seconds
- Missing: Ability to run comparison (policy A vs B)

---

## PART 2: FUNCTIONAL CORRECTNESS & DATA FLOW

### Pipeline Verification

```
Policy Input
    ↓
Policy Parser (LLM + fallback) ✅
    ↓
Policy Mapper → Attributes ❌ MISSING: health domain
    ↓
Population Generator ✅ (ignores unknown attributes silently)
    ↓
Sample 50 Citizens ✅
    ↓
LLM Reactions (Gemini 2.0-Flash) ✅
    ↓
Training Data Assembly ✅
    ↓
Neural Training ❌ INSUFFICIENT DATA (50 samples)
    ↓
Full Population Prediction ✅
    ↓
Time Simulation (10-50 steps) ✅
    ↓
Dashboard Visualization ✅
```

### Critical Data Flow Issues

| Issue | Severity | Impact |
|-------|----------|--------|
| Health domain parsed but not mapped | HIGH | Some policies misclassified |
| 50-sample training set | HIGH | Model unreliable, overfit likely |
| No input validation on population update | MEDIUM | Potential crashes with bad data |
| Type ambiguity (tuple vs array) | MEDIUM | Works but fragile, bad for refactoring |
| Mock reactions use wrong income bounds | LOW | Mock mode unrealistic but graceful |

---

## PART 3: ML MODEL QUALITY

### Feature Engineering
**Quality: ✅ GOOD**

6D feature vector is reasonable:
- Age (demographic trend)
- Income (economic status)
- Risk tolerance, openness, political leaning (behavioral)
- Policy domain (context)

Missing:
- Interaction terms (e.g., age × income, location × caste)
- Non-linear transformations (e.g., log(income))
- Time-based features for cumulative effects

### Normalization
**Quality: ✅ EXCELLENT**

- Proper Z-score normalization
- Saved mean/std reused correctly
- `apply_normalization()` prevents recomputation bug
- eps=1e-8 prevents division by zero

### Model Architecture
**Quality: ✅ APPROPRIATE**

```
Input (6) → Linear(64) → BatchNorm → ReLU → Dropout(0.2)
         → Linear(32)  → BatchNorm → ReLU → Dropout(0.2)
         → Linear(16)  → ReLU
         → Linear(3)   → Output
```

- Reasonable for small dataset
- Regularization (BatchNorm, Dropout) is good
- Output: [happiness_delta, support_delta, income_delta]

### Training Quality
**Quality: ❌ POOR**

| Aspect | Current | Needed |
|--------|---------|--------|
| Training samples | 50 | 500+ |
| Validation split | None | 20% |
| Test split | None | 20% |
| Cross-validation | None | 5-fold |
| Loss tracking | Each 40 epochs | Per batch |
| Convergence check | Fixed epochs | Early stopping |
| Hyperparameter tuning | None | Grid/random search |
| Generalization test | None | Required |

### Output Scaling
**Quality: ✅ FIXED (RECENTLY)**

- ~~Was multiplying income by 10,000 (BUG)~~ → Fixed to 1.0
- Clamping happiness/support to [-1, 1] is correct
- Income left unclamped for realism

### Overfitting Risk
**Quality: ❌ VERY HIGH**

With 50 samples and 6D input:
- 50 samples << number of model parameters (~1,000+ weights)
- Model can memorize training set
- No way to detect overfitting without test set
- **Prediction confidence should be very low**

**Recommendation:**
Add validation metrics:
```python
def evaluate_model(model, X_test, y_test, mean, std):
    # Calculate R² score per output
    # Calculate MAE per output
    # Compare train vs test loss
    return train_loss, test_loss, r2_scores
```

---

## PART 4: CODE QUALITY

### Strengths
✅ Clear section headers (great for navigation)  
✅ Defensive `.get()` calls with defaults  
✅ Logging throughout modules  
✅ Consistent naming conventions  
✅ Good function docstrings  
✅ Separation of concerns (policy → population → LLM → training → simulation)  

### Weaknesses
❌ No type hints (makes refactoring risky)  
❌ No docstrings for complex logic  
❌ Hardcoded constants scattered throughout  
❌ Silently ignoring errors (unknown attributes, unmapped domains)  
❌ No validation of inputs/outputs  
❌ Code duplication (e.g., dict key access patterns)  
❌ No abstract base classes or protocols  

### Duplication
```python
# Appears in multiple places:
result.get("happiness_change", 0.0)
result.get("support_change", 0.0)
result.get("income_change", 0.0)
```

Should extract into helper or use dataclass.

### Modularity
**Rating: 7/10**

Good:
- Modules have single responsibility
- Imports are logical
- Circular dependencies avoided

Bad:
- Hard-coded assumptions (e.g., 6D feature vector assumed in predictor and formatter)
- policy_mapper is tightly coupled to population_generator
- No abstraction for "policy domain" concept

---

## PART 5: PERFORMANCE ANALYSIS

### Bottlenecks (Ranked by Impact)

| Bottleneck | Time | Severity | Fix |
|---|---|---|---|
| LLM API calls (50 citizens × ~1-2 sec) | 50-100 sec | CRITICAL | Batch API, caching, lower sample |
| Neural training (50 samples × 100 epochs) | 10-20 sec | MEDIUM | Early stopping, smaller network |
| Population generation (10,000 citizens) | 5-10 sec | LOW | Pre-computation, caching |
| Simulation loop (10-50 steps × 10k preds) | 5-15 sec | LOW | Batch ops (already done) |

### LLM Cost Analysis
- 50 citizens per policy × $0.075/MCT (Gemini 2.0-Flash) ≈ $0.15-0.30 per policy
- Unrealistic for production (need lower sample or batch API)

### Scalability Issues
- Population of 10,000: ✅ Fine
- Population of 100,000: ❌ Memory pressure, slow simulation
- Training set of 50: ❌ Unreliable ML
- Training set of 5,000: ❌ LLM cost becomes prohibitive

**Recommendation:** Switch to smaller sample (10-20) or use synthetic LLM data augmentation.

---

## PART 6: INFRASTRUCTURE & MISSING FEATURES

### Error Handling
**Status: ❌ MINIMAL**

Missing:
- Try-catch around policy parsing
- Validation of LLM response format
- Handling of empty populations
- Division-by-zero in metrics (if population empty)
- Handle None returns from `_get_client()`

### Logging
**Status: ✅ GOOD**

Implemented in:
- llm_interface.py
- population_generator.py
- training_model.py
- reaction_predictor.py

Missing:
- app.py (no pipeline logging)
- simulation_engine.py
- policy_parser.py (only warnings)

### Configuration Management
**Status: ❌ NONE**

All constants hardcoded:
```python
# Should be configurable:
POPULATION_SIZE = 10000
SAMPLE_SIZE = 50
EPOCHS = 100
LEARNING_RATE = 0.001
TIMESTEPS = 10-50
```

**Recommendation:** Create `config/config.py`:
```python
@dataclass
class SimulationConfig:
    population_size: int = 10000
    sample_size: int = 50
    epochs: int = 100
    learning_rate: float = 0.001
    max_timesteps: int = 50
```

### Data Persistence
**Status: ❌ NONE**

Missing:
- Save simulation results (JSON/CSV)
- Load previous simulations
- Compare results between policies
- Export citizen-level data

### Model Persistence
**Status: ❌ NONE**

Missing:
- Save trained models
- Load pre-trained models
- Model versioning

### Testing
**Status: ❌ NONE**

No test suite exists. Should have:
```python
tests/
  test_citizen.py
  test_population.py
  test_policy_parser.py
  test_llm_interface.py
  test_training_model.py
  test_simulation.py
  test_pipeline_integration.py
```

### API Abstraction
**Status: ❌ MISSING**

Hard-coded assumptions about:
- Feature dimensions (6D)
- Output dimensions (3D)
- Policy domains (education/tax/agriculture/health)

Should use enums, protocols, or classes.

---

## PART 7: BUGS & CRITICAL ISSUES

### 🔴 CRITICAL

1. **Health domain mapped but not handled**
   - Parser extracts `"health"` domain
   - Mapper doesn't recognize it → falls to generic
   - **Fix:** Add health case to mapper
   
2. **Training set too small (50 samples)**
   - Model will overfit severely
   - Predictions unreliable, not generalizable
   - **Fix:** Increase to 500+ or use transfer learning

3. **No validation of attribute mismatch**
   - Mapper returns attributes mapper population can't generate
   - Silently ignored
   - **Fix:** Validate attribute compatibility

### 🟡 HIGH

4. **No error recovery in app.py**
   - If LLM fails mid-way, shows partial results
   - If training fails, shows garbage output
   - **Fix:** Wrap pipeline in try-catch

5. **Hardcoded constants**
   - Population size, sample size, epochs hardcoded
   - Can't tune without code changes
   - **Fix:** Move to config

6. **No progress indication**
   - 50-100 second LLM phase has no feedback
   - Users think app hung
   - **Fix:** Add progress bar or status updates

### 🟠 MEDIUM

7. **No test set for model evaluation**
   - Can't measure generalization
   - Can't detect overfitting
   - **Fix:** Create train/val/test split

8. **Mock reaction income factor incorrect**
   - Assumes max income ~200k (unrealistic for India)
   - **Fix:** Use actual distribution stats

9. **No input validation**
   - Empty policy string allowed (handled)
   - Very long policies might break prompt tokenization
   - **Fix:** Add max length validation

### 🟢 LOW

10. **Type hints missing**
    - Makes refactoring risky
    - IDE autocomplete limited
    - **Fix:** Add type hints throughout

11. **`to_dict()` incomplete**
    - Doesn't serialize all citizen fields
    - **Fix:** Make it comprehensive

12. **No __repr__ on classes**
    - Debugging harder
    - **Fix:** Add for Citizen, Policy objects

---

## PART 8: DASHBOARD EVALUATION

### Strengths
✅ Clear layout with dividers  
✅ Good KPI formatting (₹ symbols, thousands separators)  
✅ Multiple visualization types (pie, bar, histogram, line)  
✅ Citizen drill-down view  
✅ Diary entries for qualitative insight  
✅ Population analytics are comprehensive  

### Weaknesses
❌ Visualizations hardcoded in app.py (not reusable)  
❌ No save/export functionality  
❌ No policy comparison view  
❌ No error messages for failed runs  
❌ No configuration UI for tweaking parameters  
❌ No historical runs display  

### Missing Features for Production
- **Save results** → JSON/CSV export
- **Compare policies** → Side-by-side analysis
- **Run history** → Replay previous simulations
- **Parameter tuning** → UI sliders for population size, epochs, etc.
- **Sensitivity analysis** → What-if scenarios
- **Fairness metrics** → Show impact on different demographics separately
- **Warnings** → Alert if model confidence is low

### UX Issues
- No feedback during 50-second LLM phase
- No indication of what's running
- Error messages for failed LLM calls not shown
- No way to see logs/debug info

---

## PART 9: ARCHITECTURE & DESIGN

### Strengths
✅ **Modular separation:** Policy → Population → LLM → Training → Simulation → Viz  
✅ **Dual-path LLM:** Gemini + keyword fallback (excellent resilience)  
✅ **Lazy initialization:** LLM client only loaded when needed  
✅ **Data flow is logical:** Clear path from input to output  

### Weaknesses
❌ **No abstraction layers:** Hard-coded assumptions everywhere  
❌ **Tightly coupled:** policy_mapper assumptions built into population_generator  
❌ **Global state:** `_gemini_client` uses global variable  
❌ **No factory pattern:** No way to swap implementations  
❌ **No dependency injection:** Everything imported directly  

### Recommended Refactoring
```python
# Add abstraction layer
class PolicyDomain:
    EDUCATION = "education"
    TAX = "tax"
    AGRICULTURE = "agriculture"
    HEALTH = "health"

class PolicyManager:
    """Encapsulates policy parsing and mapping"""
    def parse(self, text) -> Policy
    def map_to_attributes(self, policy) -> List[str]

class PopulationManager:
    """Encapsulates population generation"""
    def generate(self, size, attributes) -> List[Citizen]

class ReactionGenerator:
    """Encapsulates LLM + mock reactions"""
    def generate(self, citizen, policy) -> Dict

# Use dependency injection in app.py
app = CivisimApp(
    policy_manager=PolicyManager(),
    population_manager=PopulationManager(),
    reaction_generator=ReactionGenerator(),
    model_trainer=ModelTrainer()
)
```

---

## PART 10: IMPROVEMENT ROADMAP

### P0 (Critical) — Do First
1. **Add health domain map** (5 min fix)
2. **Add validation for attribute compatibility** (30 min)
3. **Add error handling in app.py pipeline** (1 hour)
4. **Add try-catch around LLM calls** (30 min)

### P1 (High) — Do Soon
5. **Increase training data** (from 50 to 500 samples) (Requires rearchitecting LLM sampling)
6. **Add train/val/test split** (1 hour)
7. **Add model evaluation metrics** (1 hour)
8. **Add progress bar to app** (30 min)
9. **Extract dashboard viz to separate module** (1 hour)

### P2 (Medium) — Do This Sprint
10. **Add configuration system** (2 hours)
11. **Add type hints throughout** (3 hours)
12. **Add test suite** (4 hours)
13. **Add model saving/loading** (2 hours)
14. **Add result persistence** (2 hours)

### P3 (Nice to Have) — Future
15. **Add policy comparison view** (3 hours)
16. **Add fairness metrics per demographic** (2 hours)
17. **Add sensitivity analysis** (3 hours)
18. **Add API endpoint** (4 hours)
19. **Migrate to google.genai properly** (done ✅)

---

## FINAL VERDICT

### Scores

| Category | Score | Notes |
|----------|-------|-------|
| **Completeness** | 6/10 | Core pipeline works, but 20% features missing |
| **Code Quality** | 6.5/10 | Good structure, missing type hints and tests |
| **ML Quality** | 4/10 | Training set too small, no evaluation |
| **Architecture** | 7/10 | Good separation, but tightly coupled in places |
| **Error Handling** | 3/10 | Minimal, mostly silent failures |
| **Testing** | 0/10 | No test suite |
| **Documentation** | 4/10 | Some docstrings, no guides |
| **UX/Dashboard** | 7/10 | Good layout, missing saving/comparison |

### Overall Project Score: **5.3/10**

---

### Is This Ready for Demo/Portfolio?

#### ✅ **YES, BUT WITH CAVEATS**

**What works today:**
- Full pipeline runs end-to-end
- Produces believable outputs
- Dashboard looks polished
- LLM integration is robust
- Good for a proof-of-concept demo

**What to mention in demo:**
- "This is an early prototype"
- "Model trained on small sample for speed"
- "Full production version would use 500+ training samples"
- Show the policy parsing working with specific policy
- Highlight the fallback mock mode for offline demo

**What NOT to say:**
- "This model is production-ready" ❌
- "Predictions are statistically reliable" ❌
- "This outperforms existing policy tools" ❌

**For investors/advisors:**
- Position as **proof-of-concept** ✅
- Emphasize **dual-path LLM architecture** ✅
- Show **scalability path** (can grow to 50k citizens, 5k training samples) ✅
- Demo the **dashboard interactivity** ✅

---

### Recommended Next Steps (Ranked)

1. **Fix P0 bugs** (health domain, error handling) — 2 hours
2. **Increase training sample** to 500 (requires infrastructure change) — 4 hours
3. **Add test suite** (unit + integration) — 6 hours
4. **Add config management** — 2 hours
5. **Add result persistence** — 3 hours

**With these changes, project would be 7.5/10 and ready for alpha testing.**

---

## DETAILED RECOMMENDATIONS

### Short-term (Next Week)
- Fix health domain bug
- Add 5-10 validation checks
- Add progress indicator
- Write 10 unit tests

### Medium-term (Next Month)
- Scale training to 500 samples
- Add model evaluation metrics
- Implement result saving
- Build API endpoint

### Long-term (Q2+)
- Add fairness analysis
- Integrate real data sources
- Build admin dashboard
- Scale to 50k+ citizens
- Multi-policy comparison

---

**End of Audit Report**

---

## APPENDIX: Quick Wins (Highest ROI Fixes)

### Fix #1: Health Domain (5 minutes)
```python
# policy_mapper.py
elif domain == "health":
    return ["health_status", "insurance", "income"]
```

### Fix #2: Error Wrapping (20 minutes)
```python
# app.py
try:
    parsed_policy = parse_policy(policy)
    # ... rest of pipeline
except Exception as e:
    st.error(f"Pipeline failed: {str(e)}")
    st.stop()
```

### Fix #3: Progress Bar (15 minutes)
```python
# app.py
progress_bar = st.progress(0)
for i, citizen in enumerate(sample_population):
    progress_bar.progress((i+1) / len(sample_population))
    reaction = simulate_citizen_reaction(citizen, policy)
```

### Fix #4: Validation Check (10 minutes)
```python
# app.py after mapping
required_attrs = set(attributes)
generated_attrs = set(CROPS + EDUCATIONS + ... )
if not required_attrs.issubset(generated_attrs):
    st.warning(f"Cannot generate: {required_attrs - generated_attrs}")
```

---

## Summary for Stakeholders

**CIVISIM is a WORKING PROTOTYPE suitable for:**
- Internal demos
- Investor pitches (as proof-of-concept)
- Research papers
- Portfolio showcase

**CIVISIM is NOT ready for:**
- Production use
- Real policy decisions (model unreliable)
- Enterprise customers
- Public release

**Key strengths to emphasize:**
1. Robust dual-path LLM (Gemini + fallback)
2. Clean data pipeline
3. Scalable architecture
4. Polished dashboard

**Key improvements needed:**
1. Larger training set (50 → 500 samples)
2. Proper ML validation (train/val/test)
3. Error handling throughout
4. Test coverage
5. Production hardening (6 months of work)
