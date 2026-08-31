# Kinara AI — Deployment

## Target

Google Cloud Run.

## Container

Application listens on:

0.0.0.0:$PORT

Default:

8080

## Build

Docker builds application.

## Runtime Configuration

Required environment variables (`src/config.py` — the app fails fast at
startup with a clear error if any are missing):

GEMINI_API_KEY (secret — via Secret Manager, not `--set-env-vars`)
GEMINI_MODEL
GOOGLE_CLOUD_PROJECT
FIREBASE_PROJECT_ID
FIREBASE_WEB_API_KEY

Optional — Multi-Provider AI Architecture (`src/config.py`, all default
to Gemini-only behavior if unset, so an existing Gemini-only deployment
never needs these):

AI_PRIMARY_PROVIDER (default: gemini)
AI_FALLBACK_PROVIDER (default: none — set to `openai` to enable the
Gemini → OpenAI fallback documented in ARCHITECTURE.md / AI_SPEC.md)
OPENAI_API_KEY (secret — via Secret Manager, only required if
AI_FALLBACK_PROVIDER=openai or AI_PRIMARY_PROVIDER=openai)
OPENAI_MODEL (only required under the same condition)

Firebase configuration must use a secure server-side mechanism —
Application Default Credentials via the Cloud Run service's attached
service account. No `GOOGLE_APPLICATION_CREDENTIALS` env var, no key
file, on Cloud Run.

Do not commit Firebase service account credentials.

## Session affinity (required — Streamlit-specific)

`st.session_state` lives in the process handling the request, not in
Firestore. On Cloud Run's default autoscaling, a user's next request can
land on a different instance and lose their login/session mid-flow.
Deploy with `--session-affinity --min-instances=1` to prevent this for
demo-scale traffic. See ACCEPTANCE_TESTS.md DEPLOY-001.

## Deployment Checklist

1. Enable required Google Cloud APIs (Cloud Run, Cloud Build, Artifact
   Registry, Secret Manager).
2. Configure Firebase project (Blaze plan required).
3. Configure Firebase Authentication (Email/Password provider).
4. Create Firestore database.
5. Configure Gemini access (API key from Google AI Studio).
6. Grant the Cloud Run runtime service account `roles/datastore.user` and
   `roles/secretmanager.secretAccessor`.
7. Build container. Confirm `.dockerignore` is present before building —
   without it, `COPY . .` bakes any local `.env`/`.venv` into the image.
8. Deploy to Cloud Run with `--session-affinity --min-instances=1`.
9. Configure environment/secrets (`--set-env-vars` for non-secrets,
   `--set-secrets` for GEMINI_API_KEY — and OPENAI_API_KEY the same way
   if the OpenAI fallback is enabled for this deployment).
10. Test authentication.
11. Test Firestore persistence.
12. Test Gemini generation.
13. If AI_FALLBACK_PROVIDER=openai, test the fallback path (see
    ACCEPTANCE_TESTS.md) — do not skip this if fallback is enabled.
14. Run acceptance tests (ACCEPTANCE_TESTS.md), including DEMO-001.