# 🚀 Northern Lights: Structured API Endpoint Specification (v1.1)

## 0. Mission:
Your mission with Northern Lights is to establish the definitive, API-accessible transparency platform for Nordic corporate and fund ownership. By leveraging Graph Database (Neo4j) and Vectorization technologies, you aim to transform fragmented public data into an intelligent registry that provides clients—funds and companies—with powerful, actionable insights into ownership, investment flows, and competitive relationships, moving beyond simple data lookup to deliver AI-driven investment and sales leads via Leiden Clustering. This platform is central to empowering your clients to make strategic decisions in the Nordic financial landscape.

## 1. Project Overview & Goals

| Field | Description |
| :--- | :--- |
| **Product Name** | Northern Lights (Nordic Fund & Company Transparency Platform) |
| **Core Mission** | To provide API-accessible, precise, and current insights into company ownership, investment flow, and competitive relationships within the Nordic region, centralized in a powerful graph registry. |
| **Initial Scope** | **Sweden (SE) only.** |
| **Target Volume** | **Tier 2 Focus:** 50,000 – 100,000 active entities (Companies and Funds). |
| **Stack** | Python, Tavely (Scraping), Sentence Transformers (Vectorization), Neo4j Aura DB (Graph/Vector Store), Google Cloud Run (REST API), Cloud Endpoints (API Security). |

---

## 2. Data Model & Entity Vectorization

### 2.1 Core Entity Nodes (`:Company`/`:Fund`)

| Field | Type | Description | Rationale/Refinement |
| :--- | :--- | :--- | :--- |
| **company\_id** | `str` (Org. No.) | **Primary Key.** Unique Legal Identifier. | **Mandatory index** for deduplication and traversal. |
| **name** | `str` | Full legal name. | Bolagsverket / User-input. |
| **country\_code** | `str` | Hardcoded to `SE` initially. | |
| **description** | `str` | Short executive summary. | Input for Vectorization. |
| **mission** | `str` | Company's core mission statement. | Input for Vectorization. |
| **sectors** | `List[str]` | Industry sectors. | Input for Vectorization. |
| **cluster\_id** | `int` | **Pre-calculated ID** from Leiden Clustering. | Critical for fast `/leads` endpoint filtering. |
| **vector** | `List[float]` | The generated embedding. | Stored directly on the node for similarity search. |

## 3. Architecture & Data Flow Summary

| Component | Technology / Service | Performance & Security Refinements |
| :--- | :--- | :--- |
| **Security Layer** | **Google Cloud Endpoints** | Manages the **API Key Registry**, enforces authentication, and applies Rate Limiting. |
| **API Backend** | **Google Cloud Run** | **Initial Target:** Scale to handle **5 RPS** with auto-scaling capacity up to **25 RPS**. |
| **Database** | **Neo4j Aura DB** | Must be sized for **100,000+ nodes**; requires Professional Tier or higher for vector indexing and GDS. |
| **Clustering** | **Neo4j Graph Data Science (GDS)** | GDS job execution must be scheduled externally (e.g., Cloud Run Job) based on the defined frequency. |
| **Ingestion** | **Pub/Sub Queue** | Decouples the `/ingest` endpoint, ensuring it returns immediately. |

---

## 4. Structured API Endpoint Specification

### 4.1. Entity Ingestion & Search

| Endpoint | Method | Use Case | Description | Performance Note |
| :--- | :--- | :--- | :--- | :--- |
| `/v1/companies/ingest` | **POST** | **Ingestion Trigger** | Initiates the **asynchronous** pipeline for a new entity. Takes `{"name": "Entity Name"}` in the body. | Returns