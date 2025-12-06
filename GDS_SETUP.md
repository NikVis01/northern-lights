# AuraDS Graph Data Science Setup

## Required Environment Variables

Add these to your `.env` file:

```bash
# Aura API Credentials (for GDS Sessions)
AURA_CLIENT_ID=your-aura-api-client-id
AURA_CLIENT_SECRET=your-aura-api-client-secret
AURA_PROJECT_ID=your-project-id  # Optional

# Neo4j Database Connection
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-database-password
```

## How to Get Credentials

### 1. Aura API Credentials

1. Go to https://console.neo4j.io
2. Navigate to your account settings
3. Go to "API Keys" or "Credentials"
4. Create a new API key pair
5. Copy the `Client ID` and `Client Secret`

### 2. Neo4j Database Connection

1. In Neo4j Aura Console, select your database instance
2. Click "Connect"
3. Copy the connection URI (starts with `neo4j+s://`)
4. Use the password you set when creating the database

## How It Works

The application now uses the **AuraDS Sessions API**:

1. **On First GDS Call**: Creates a managed GDS session with 4GB memory
2. **Session Reuse**: Subsequent calls reuse the same session
3. **On App Shutdown**: Automatically deletes the session to avoid charges

## Session Management

- **Session Name**: `northern-lights-gds-session`
- **Memory**: 4GB (configurable in `neo4j_client.py`)
- **Auto-cleanup**: Session is deleted when FastAPI app shuts down

## Testing GDS

Run the graph service pipeline:

```bash
uv run python -m app.services.graph_service
```

This will:

1. Generate embeddings for all Company and Fund nodes
2. Create a GDS session
3. Run K-NN similarity to find similar entities
4. Apply Leiden clustering for community detection
5. Clean up the session when done

## Cost Considerations

AuraDS sessions are billed by usage time. The session is automatically deleted when:

- The FastAPI app shuts down
- The graph service pipeline completes
- You manually call `close_gds_session()`

## Troubleshooting

### "GDS credentials not configured"

- Make sure `AURA_CLIENT_ID` and `AURA_CLIENT_SECRET` are set in `.env`

### "Neo4j credentials not configured"

- Make sure `NEO4J_URI` and `NEO4J_PASSWORD` are set in `.env`

### Session not deleted

- Check FastAPI logs for shutdown messages
- Manually delete via Aura Console if needed
