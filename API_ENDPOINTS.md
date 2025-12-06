# Northern Lights API Endpoints

## Companies (`/v1/companies/`)
- `POST /ingest` - Trigger async ingestion
- `GET /{organization_id}` - Get company
- `POST /search` - Vector similarity search
- `GET /{organization_id}/leads` - Same-cluster leads

## Investors (`/v1/investors/`)
- `GET /{investor_id}` - Get investor
- `GET /{investor_id}/portfolio` - Get holdings
- `POST /` - Create investor

## Relationships (`/v1/relationships/`)
- `POST /` - Create relationship
- `GET /network/{entity_id}` - Ownership graph

## Search (`/v1/search/`)
- `POST /` - Unified vector search

All endpoints require API key via `X-API-Key` header.





