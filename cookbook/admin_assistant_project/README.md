# Admin Assistant Prototype

This repository contains a small Python prototype for an admin-facing assistant that helps with product descriptions, customer replies, recommendations, and morning briefings.

## Purpose

The admin assistant is designed to support operations teams by:

- Generating product descriptions from catalog metadata
- Suggesting related and upsell products
- Drafting customer-facing replies
- Recommending the next admin action
- Assembling a simple morning briefing

## Project structure

- `main.py` - entry point that builds a sample catalog, runs the assistant, and prints outputs
- `agent.py` - core assistant logic, AI interaction, session handling, and JSON validation
- `tools.py` - product catalog and customer message helper utilities
- `workflow.py` - example workflow for a morning briefing
- `models/schemas.py` - Pydantic schemas used for input validation and structured output
- `requirements.txt` - Python dependencies

## Requirements

- Python 3.11+
- `pip` or another package manager
- Optional: `OPENAI_API_KEY` environment variable to use the OpenAI API

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the prototype

### With OpenAI

Set your OpenAI API key and run:

```bash
export OPENAI_API_KEY="your_api_key_here"
python main.py
```

### Without OpenAI (mock mode)

If `OPENAI_API_KEY` is not set, the assistant falls back to mock responses for demo purposes.

```bash
python main.py
```

## Running the backend API

Install the backend dependencies, then start the FastAPI server:

```bash
pip install -r requirements.txt
uvicorn api:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

## React UI integration

A minimal React frontend is included in `ui/`.

Install and run it separately:

```bash
cd ui
npm install
npm run dev
```

The UI is configured to call the backend at `http://localhost:8000` and can perform:

- product listing
- product description generation
- related and upsell recommendations
- drafted customer replies
- next action suggestions
- morning briefing generation

## Features

- `generate_product_description()` produces a headline, body copy, and benefits list
- `suggest_product_recommendations()` identifies related and upsell products
- `draft_customer_reply()` returns a polite response and tone recommendation
- `recommend_next_action()` chooses one of five admin actions based on product and customer context
- `MorningBriefingWorkflow` creates a briefing with product and customer summaries

## Customization

- Add products in `main.py` by editing `build_catalog()`
- Change the AI model in `main.py` via the `model` parameter
- Extend tools and workflows for additional admin tasks

## Notes

- The prototype uses JSON-based prompts and validation to keep the assistant output structured
- The mock mode is useful for local development when API access is not available

Feel free to adapt this prototype into a more complete admin assistant or integrate it with a UI layer.