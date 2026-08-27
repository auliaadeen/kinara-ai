# Kinara AI — Architecture

Version: 3.0

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

Gemini is NOT the system of record.

Firestore is the source of truth for:

- user
- child
- session
- learning memory
- learning path

Python is the source of truth for:

- score
- XP
- mastery calculation
- adaptive rules

Gemini is the source of generated learning content.

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