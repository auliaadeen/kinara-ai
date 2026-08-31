# Kinara AI — Architecture

Version: 3.1

## 1. Architecture Principle

Keep the MVP simple.

One application:

Streamlit → Cloud Run

External services:

Firebase Auth
Cloud Firestore
Gemini API

## 2. Architecture

Browser
   |
   v
Cloud Run
   |
   +-- Streamlit UI
   |
   +-- Application Services
          |
          +-- Auth Service
          +-- Learning Memory
          +-- Adaptive Engine
          +-- AI Engine
          +-- Gamification
          |
          +----> Firebase Auth
          |
          +----> Firestore
          |
          +----> Gemini API

## 3. Important Boundary

Gemini is NOT the system of record, and NOT the decision-maker for
anything adaptive. It generates worksheet content only. This is an
explicit, deliberate boundary, not an accident of the current
implementation — see AI_SPEC.md §0 for the full statement and rationale.

Firestore is the source of truth for:

- user
- child
- session
- learning memory (including conceptHistory — DATA_MODEL.md)
- learning path (Self-Learner — deferred, unused in this MVP)

Python is the source of truth for:

- score
- Grade (derived from score, not stored — FIRESTORE_SCHEMA.md)
- XP
- Kinara Level (derived from XP, not stored — FIRESTORE_SCHEMA.md)
- streak / Strike Status (derived from streak + lastSessionAt, not stored)
- mastery calculation (recency-weighted over conceptHistory)
- adaptive rules — including the "Recommended Next" decision itself,
  not just the inputs to it

Gemini is the source of generated learning content only.

## 4. Adaptive Flow

User starts session
       ↓
Load profile
       ↓
Load Learning Memory
       ↓
Adaptive Engine
       ↓
Create context
       ↓
Gemini
       ↓
Structured response
       ↓
Pydantic validation
       ↓
User completes activity
       ↓
Python calculates score
       ↓
Learning Memory updated
       ↓
Firestore persistence
       ↓
Next recommendation

## 5. Design Constraint

Do not introduce unnecessary infrastructure.

No:

- Kubernetes
- Redis
- Cloud SQL
- message queues
- microservices
- vector database

unless explicitly required by a future version.