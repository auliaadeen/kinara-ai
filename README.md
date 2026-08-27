# Kinara AI

> AI remembers learning behavior and adapts the next learning experience.

Kinara AI is an adaptive learning companion powered by:

- Google Cloud Run
- Firebase Authentication
- Cloud Firestore
- Gemini API
- Python + Streamlit

## Core Loop

Learn
→ Assess
→ Remember
→ Adapt
→ Next Experience

## Local Development

Create environment:

cp .env.example .env

Install:

pip install -r requirements.txt

Run:

streamlit run src/app.py

## Documentation

See:

docs/PRD.md
docs/FSD.md
docs/ARCHITECTURE.md
docs/DATA_MODEL.md
docs/AI_SPEC.md
docs/UI_SPEC.md
docs/SECURITY.md
docs/DEPLOYMENT.md
docs/ACCEPTANCE_TESTS.md
docs/AI_RULES.md

## Development Philosophy

Kinara is intentionally designed as a focused MVP.

The most important feature is not AI content generation.

The most important feature is the learning memory loop:

Learn → Assess → Remember → Adapt → Learn Again.

Kinara AI
Copyright (c) 2026 Diana Aulia

Licensed under the MIT License.

The MIT License applies to the source code of this repository.
Product name, branding, visual identity, original product concept,
documentation, and other non-code intellectual property are not
granted additional rights beyond what is explicitly stated.