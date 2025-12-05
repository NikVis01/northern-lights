# Cloud Run Deployment

## Quick Deploy

```bash
# Build and deploy
gcloud builds submit --config deploy/cloudbuild.yaml

# Or deploy directly
gcloud run deploy northern-lights-api \
  --source . \
  --region europe-north1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2
```

## Environment Variables

Set via Cloud Run console or CLI:

```bash
gcloud run services update northern-lights-api \
  --update-env-vars NEO4J_URI=neo4j+s://...,NEO4J_USERNAME=...,NEO4J_PASSWORD=...
```

## Local Testing

```bash
# Build
docker build -t northern-lights-api .

# Run
docker run -p 8080:8080 \
  -e PORT=8080 \
  -e NEO4J_URI=neo4j+s://... \
  northern-lights-api
```


