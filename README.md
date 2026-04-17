# CiviSim

CiviSim is a simple AI-powered tool that lets you test how different policies might affect a society. Describe a policy in everyday words, and it creates a virtual population, predicts how people would react, and shows you the results over time with easy-to-read charts.

## Overview

Imagine you want to know what happens if the government changes taxes or education rules. CiviSim builds a fake society of thousands of people, uses AI to guess their reactions, and runs a simulation to see trends like happiness, support for the policy, and income changes. It's like a video game for policy makers, but based on real data and AI.

## Features

- **Easy Policy Input**: Type a policy in plain English, like "Increase education subsidies for rural students."
- **Smart Policy Understanding**: The AI breaks down your policy into key parts, like what area it affects (education, taxes) and how it works (subsidies, regulations).
- **Virtual People**: Creates a diverse group of citizens with realistic traits, like age, job, income, and personality.
- **AI Reactions**: Uses advanced AI to predict how a sample of people might feel about the policy, including happiness changes and personal stories.
- **Fast Predictions**: Trains a quick AI model to guess reactions for everyone in the population.
- **Time-Based Simulation**: Runs the policy over multiple steps (like months or years) to see long-term effects.
- **Visual Results**: Shows trends with line graphs and population breakdowns with pie charts.
- **Multiple Interfaces**: Choose from a modern web app, a simple dashboard, or a basic app.

## Architecture

CiviSim works in a step-by-step process. Here's a simple flowchart of how it all connects:

```
Policy Input (Your Text)
       ↓
Policy Parser (Breaks down the policy)
       ↓
Attribute Mapper (Finds which citizen traits are affected)
       ↓
Population Generator (Creates virtual citizens)
       ↓
LLM Sampler (AI predicts reactions for a few people)
       ↓
Model Trainer (Trains a predictor for the whole group)
       ↓
Simulation Engine (Runs the policy over time)
       ↓
Dashboard (Shows results with charts)
```

This keeps everything organized: AI handles the smart parts, the simulator runs the numbers, and the dashboard makes it easy to see.

## Tech Stack

- **Python**: Main programming language for all the logic.
- **PyTorch**: For training the AI prediction models.
- **FastAPI**: Builds the backend API for running simulations.
- **React**: Creates the modern web interface.
- **Dash/Streamlit**: Alternative dashboards for different needs.
- **Groq API**: Powers the AI reactions (with a backup mode if needed).
- **Chart.js/Plotly**: Makes the graphs and charts.
- **Pandas/NumPy**: Handles data and numbers.

## Repository Structure

```
CiviSim/
├── ai_models/              # AI components
│   ├── llm_interface.py    # Connects to Groq AI for reactions
│   ├── reaction_predictor.py # Predicts reactions for everyone
│   └── training_model.py   # Trains the prediction AI
├── backend/                # API server
│   ├── app.py              # FastAPI app with simulation endpoint
│   └── requirements.txt    # Backend dependencies
├── config/                 # Settings
│   └── settings.py         # App configurations
├── dashboard/              # Visualization helpers
│   └── visualizations.py   # Chart utilities
├── data/                   # Static data
│   └── distributions.json  # Population data (for future use)
├── docs/                   # Documentation
│   └── roadmap.md          # Development plans
├── frontend/               # React web app
│   ├── src/
│   │   ├── App.tsx         # Main app
│   │   └── components/
│   │       └── Dashboard.tsx # Main dashboard with charts
│   ├── package.json        # Frontend dependencies
│   └── vite.config.js      # Build config
├── policy_engine/          # Policy processing
│   ├── policy_parser.py    # Turns text into policy details
│   └── policy_mapper.py    # Links policies to citizen traits
├── population/             # Virtual people
│   ├── citizen.py          # Citizen class with traits
│   └── population_generator.py # Creates the population
├── simulation/             # Simulation logic
│   ├── simulation_engine.py # Runs the time steps
│   └── social_network.py   # Future: citizen interactions
├── utils/                  # Helpers
│   └── metrics.py          # Data calculations
├── README.md               # This file
├── requirements.txt        # Python dependencies
└── .env                    # Environment settings
```

## Quick Start

### 1. Install Python Dependencies

Make sure you have Python 3.8+ installed. Then:

```bash
pip install -r requirements.txt
```

For the backend:

```bash
cd backend
pip install -r requirements.txt
```

### 2. Set Up Environment

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_actual_api_key_here
MOCK_BATCH_DELAY_SECONDS=0.25
```

- Get a Groq API key from their website if you want real AI reactions.
- Without a key, it uses a simple backup mode.

### 3. Run the App

#### Option 1: React Frontend + FastAPI Backend (Recommended)

Start the backend:

```bash
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

In another terminal, start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

#### Option 2: Streamlit App (Simple)

If you have Streamlit installed:

```bash
streamlit run app.py
```

Open the link shown (usually http://localhost:8501).

## Usage Examples

1. **Enter a Policy**: Type something like "Provide free school meals to all children under 12."

2. **Adjust Settings**: Use sliders to change population size (e.g., 1000 people), simulation steps (e.g., 10 months), or AI sample size.

3. **Run Simulation**: Click "Simulate" and wait for results.

4. **View Results**: See policy breakdown, population stats, and charts.

Example Output:
- Policy Analysis: Domain - Education, Mechanism - Subsidy
- Population: 3000 citizens, mix of urban/rural, various jobs
- Trends: Happiness increases gradually, income stays stable

## Visualizations

CiviSim shows results with simple, clear charts:

- **Line Charts**: Track changes over time.
  - Happiness Trend: How average happiness changes each step.
  - Support Trend: How much people support the policy over time.
  - Income Trend: Average income changes.

- **Pie Charts**: Show population makeup.
  - Occupation Distribution: Percent of farmers, workers, students, etc.
  - Caste Distribution: Breakdown by general, OBC, SC, ST groups.

These charts help you see if the policy helps everyone or causes problems.

## API Reference

The backend provides a REST API for advanced users.

### Endpoints

- `GET /api/health`: Check if the server is running.
- `POST /api/simulate`: Run a full simulation.

#### Simulate Request

```json
{
  "policy_text": "Increase minimum wage by 20%",
  "population_size": 3000,
  "sample_size": 120,
  "steps": 12,
  "epochs": 50
}
```

#### Simulate Response

```json
{
  "policy_analysis": {...},
  "population_stats": {...},
  "simulation_results": {
    "happiness_trend": [0.5, 0.6, ...],
    "support_trend": [0.4, 0.5, ...],
    "income_trend": [50000, 51000, ...]
  },
  "diagnostics": {...},
  "recommendation": "Implement with conditions"
}
```

Use tools like Postman to test the API.

## Contributing

Want to help? Great!

1. Fork the repo.
2. Make changes.
3. Test with `pytest` (if tests exist).
4. Submit a pull request.

Ideas: Add more policy types, improve charts, or add social networks.

## Roadmap

- **Done**: Basic policy parsing, population generation, AI reactions, simulation, React dashboard.
- **Next**: Add social networks for citizen interactions.
- **Future**: More advanced visualizations, real data integration, mobile app.

Check `docs/roadmap.md` for details.

---

CiviSim makes policy testing fun and easy. Try it out and see how your ideas could change a society!
