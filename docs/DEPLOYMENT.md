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

Required:

GEMINI_API_KEY
GEMINI_MODEL

Firebase configuration must use a secure server-side mechanism.

Do not commit Firebase service account credentials.

## Deployment Checklist

1. Enable required Google Cloud APIs.
2. Configure Firebase project.
3. Configure Firebase Authentication.
4. Create Firestore database.
5. Configure Gemini access.
6. Build container.
7. Deploy to Cloud Run.
8. Configure environment/secrets.
9. Test authentication.
10. Test Firestore persistence.
11. Test Gemini generation.
12. Run acceptance tests.