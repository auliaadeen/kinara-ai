# Kinara AI — Security Specification

## Authentication

Firebase Authentication is mandatory.

No fake authentication in production.

## Authorization

Every Firestore operation must be scoped to authenticated UID.

Users can only access their own:

- profile
- children
- sessions
- learning paths
- learning memory

## Secrets

Never commit:

.env
Firebase service account JSON
API keys
credentials

## Cloud Run

Secrets must be provided through:

- environment variables
- Google Secret Manager where appropriate

Do not bake secrets into Docker image.

## Child Data

Collect only information necessary for the learning experience.

Do not store:

- home address
- phone number
- unnecessary personal identifiers
- sensitive personal information