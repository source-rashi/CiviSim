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
- **Dash** (Modern Web Dashboard) or Streamlit (Basic Dashboard)
- PyTorch
- Plotly
- Pandas / NumPy
- NetworkX
- Google Gemini API (`google-generativeai`)

## Repository Structure

```text
civisim/
	app.py                    # Original Streamlit app
	dashboard.py              # Modern Dash dashboard
	run_dashboard.py          # Dashboard launcher script
	DASHBOARD_README.md       # Dash dashboard documentation
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

### 3) Choose your dashboard

#### Option A: Modern Dash Dashboard (Recommended)
```bash
python run_dashboard.py
```
or
```bash
python dashboard.py
```

#### Option B: Original Streamlit Dashboard
```bash
streamlit run app.py
```

Then open the local URL shown in your terminal (Dash: http://localhost:8050, Streamlit: usually http://localhost:8501).

## Dashboard Comparison

| Feature | Streamlit | Dash |
|---------|-----------|------|
| 🎨 **UI Design** | Basic, functional | Modern, aesthetic with dark theme |
| 📱 **Responsiveness** | Basic | Bootstrap-based responsive layout |
| 🎯 **Interactivity** | Limited | Advanced callbacks and state management |
| ⚡ **Performance** | Good | Excellent for complex dashboards |
| 🚀 **Deployment** | Streamlit Cloud | Any WSGI server (Heroku, AWS, etc.) |
| 🎨 **Customization** | Limited | Extensive CSS and component control |
| 📊 **Charts** | Plotly integration | Native Plotly with custom styling |

**Recommendation**: Use the **Dash dashboard** for production deployments and the **Streamlit app** for quick prototyping.

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
