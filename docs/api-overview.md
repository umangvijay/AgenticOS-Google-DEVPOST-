# API overview

Base URL: `/api/v1` (health at `/health`). JWT Bearer + CSRF cookie on cookie-authenticated browsers.

## Auth
`POST /auth/signup` `POST /auth/login` `POST /auth/guest` `POST /auth/refresh` `GET /auth/me`

## Workspace
`POST /workflows` or `POST /intent` — goal → live plan → run  
`GET /workflows` `GET /workflows/{run_id}` `GET /workflows/{run_id}/events` (SSE)

## Integrations
`POST /integrations/build` `POST /integrations/build-from-url` `POST /integrations/build-from-prompt`  
`GET /integrations/builds/{id}` `POST /integrations/{id}/test|enable|disable` `POST /integrations/{id}/credentials`

## Vault & studio
`POST/GET/DELETE /credentials`  
`POST /capabilities/site-health` `POST /capabilities/debug` `POST /capabilities/generate`  
`GET /artifacts` `GET /artifacts/{id}/files/{path}`

## Resume & memory
`POST /resume/scan` `POST /resume/create` `POST /resume/analyze` `POST /resume/tailor`  
`POST /memory` `POST /memory/search`

## Usage
`GET /usage/context` — live context-window breakdown for the signed-in user
