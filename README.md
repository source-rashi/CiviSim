# CiviSim

CiviSim is an AI-assisted synthetic society simulator for policy experimentation.
It lets you describe a policy in plain language, generates a large virtual population,
estimates citizen-level reactions, and visualizes system-wide outcomes over time.

## What It Does

- Parses free-text policy input into a structured policy representation.
- Maps policy intent to citizen attributes likely to be affected.
- Generates a synthetic population (demographics, occupation, income, traits).
- Uses Gemini to simulate reactions for a sample of citizens.
- Trains a neural predictor to scale reactions across the full population.
- Runs multi-step simulation and tracks happiness, support, and income trajectories.
- Displays interactive dashboard analytics and citizen-level views.

## Tech Stack

- Python
- Streamlit
- PyTorch
- Plotly
- Pandas / NumPy
- NetworkX
- Google Gemini API (`google-generativeai`)

## Repository Structure

```text
civisim/
	app.py
	ai_models/
	policy_engine/
	population/
	simulation/
	dashboard/
	utils/
	data/
	docs/
	test_*.py
```

## Quick Start

### 1) Install dependencies

```bash
pip install -r requirements.txt
```

### 2) Configure environment variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_actual_api_key
```

Without a valid key, LLM reaction generation returns a configuration error message.

### 3) Run the app

```bash
streamlit run app.py
```

Then open the local Streamlit URL shown in your terminal.

## Testing

Run the included tests with:

```bash
pytest -q
```

Targeted runs:

```bash
pytest -q test_policy_engine.py
pytest -q test_phase45.py
pytest -q test_phase5.py
pytest -q test_dashboard_integration.py
```

## Current Status

Core pipeline and dashboard are implemented and integrated.
Roadmap notes are available in `docs/roadmap.md`.
