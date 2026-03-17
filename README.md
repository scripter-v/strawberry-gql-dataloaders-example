# Simple FastAPI + Strawberry server

This repository contains a minimal Python HTTP server built with FastAPI and Strawberry GraphQL.

## Endpoints

- `POST /graphql` exposes the Strawberry GraphQL API.
- `GET /graphql` opens the Strawberry GraphQL IDE in the browser.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The server will start on `http://127.0.0.1:8000`.

## Example GraphQL query

```graphql
{
  books {
    id
    title
    author {
      id
      name
    }
  }
}
```

## Run tests

```bash
pytest
```
