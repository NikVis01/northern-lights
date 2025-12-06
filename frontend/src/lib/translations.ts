
export type Language = "en" | "sv";

export const translations = {
  en: {
    // Header (Hub)
    network: "Network",
    data: "Data",
    agent: "Agent",
    live: "LIVE",
    account: "Account",
    settings: "Settings",
    language: "Language",
    logout: "Logout",
    english: "English",
    swedish: "Svenska",

    // Header (AI)
    "nav.network": "Network",
    "nav.features": "Features",
    "nav.architecture": "Architecture",
    "nav.requestAccess": "Request Access",

    // Index page (Hub)
    liveNetwork: "Live Network",
    ownershipGraph: "Ownership Graph",
    hoverToExplore: "Hover to explore connections",

    // Hero (AI)
    "hero.subtitle": "Nordic Corporate Intelligence",
    "hero.title1": "The Definitive Map of",
    "hero.title2": "Nordic Corporate Power",
    "hero.description": "AI-powered ownership intelligence. Trace beneficial owners through corporate layers in seconds. Know who controls what—before your competition does.",
    "hero.exploreGraph": "Explore the Graph",
    "hero.viewDocs": "View Documentation",

    // Graph section (AI)
    "graph.subtitle": "Live Network",
    "graph.title": "Ownership Graph Visualization",

    // Stats (AI)
    "stats.entities": "Entities Tracked",
    "stats.scope": "Initial Scope",
    "stats.response": "Query Response",
    "stats.updates": "Data Updates",
    "stats.realtime": "Real-time",

    // Features (AI)
    "features.subtitle": "Capabilities",
    "features.title": "Actionable Intelligence",
    "features.ownership.title": "Complete Ownership Chains",
    "features.ownership.desc": "Trace hidden beneficial owners through corporate layers instantly.",
    "features.mapping.title": "Intelligent Market Mapping",
    "features.mapping.desc": "Discover non-obvious competitors and acquisition targets using AI similarity clustering.",
    "features.leads.title": "Qualified Leads",
    "features.leads.desc": "Generate high-value prospects from real-time network patterns and ownership shifts.",
    "features.database.title": "Graph Database",
    "features.database.desc": "Neo4j-powered relationship analysis with vector embeddings for deep insights.",
    "features.api.title": "REST API",
    "features.api.desc": "Secure, high-performance endpoints via Google Cloud Run with sub-100ms latency.",
    "features.security.title": "Enterprise Security",
    "features.security.desc": "API key authentication, rate limiting, and encrypted data transmission.",

    // Architecture (AI)
    "arch.subtitle": "Infrastructure",
    "arch.title": "Built for Scale",
    "arch.data.label": "Data Layer",
    "arch.data.value": "Real-time aggregation from Swedish corporate registries",
    "arch.intelligence.label": "Intelligence",
    "arch.intelligence.value": "Neo4j graph database + vector embeddings",
    "arch.clustering.label": "Clustering",
    "arch.clustering.value": "Leiden algorithm for market segmentation",
    "arch.delivery.label": "Delivery",
    "arch.delivery.value": "Google Cloud Run + Cloud Endpoints",

    // CTA (AI)
    "cta.title": "Control the flow of information",
    "cta.description": "Join leading Nordic funds and enterprises using Northern Lights for strategic advantage.",
    "cta.button": "Request API Access",

    // Footer (AI)
    "footer.tagline": "Nordic Corporate Intelligence Platform",

    // Data Table (Hub)
    allEntities: "All Entities",
    companies: "Companies",
    company: "Company",
    investors: "Investors",
    fund: "Fund",
    results: "results",
    search: "Search...",
    type: "Type",
    name: "Name",
    orgNo: "Org No.",
    sector: "Sector",
    cluster: "Cluster",
    ownership: "Ownership",
    country: "Country",

    // Chat Panel (Hub)
    ingestionAgent: "Ingestion Agent",
    addCompany: "Add company...",
    readyToProcess: "Ready to process ingestion requests. Enter a company name or org number to add to the registry.",
    queuing: "Queuing \"{input}\" for ingestion. Processing will complete in ~5 minutes.",
    foundEntity: "Found entity matching query. Generating vector embeddings and assigning to Cluster #3.",
    ingestionComplete: "Ingestion complete. Entity added to graph with 4 ownership connections identified.",
  },
  sv: {
    // Header (Hub)
    network: "Nätverk",
    data: "Data",
    agent: "Agent",
    live: "LIVE",
    account: "Konto",
    settings: "Inställningar",
    language: "Språk",
    logout: "Logga ut",
    english: "English",
    swedish: "Svenska",

    // Header (AI)
    "nav.network": "Nätverk",
    "nav.features": "Funktioner",
    "nav.architecture": "Arkitektur",
    "nav.requestAccess": "Begär åtkomst",

    // Index page (Hub)
    liveNetwork: "Live-nätverk",
    ownershipGraph: "Ägarskapsgrafen",
    hoverToExplore: "Hovra för att utforska kopplingar",

    // Hero (AI)
    "hero.subtitle": "Nordisk Företagsintelligens",
    "hero.title1": "Den Definitiva Kartan över",
    "hero.title2": "Nordisk Företagsmakt",
    "hero.description": "AI-driven ägarintelligens. Spåra verkliga ägare genom företagslager på sekunder. Vet vem som kontrollerar vad—innan dina konkurrenter gör det.",
    "hero.exploreGraph": "Utforska Grafen",
    "hero.viewDocs": "Visa Dokumentation",

    // Graph section (AI)
    "graph.subtitle": "Live Nätverk",
    "graph.title": "Visualisering av Ägargraf",

    // Stats (AI)
    "stats.entities": "Spårade Enheter",
    "stats.scope": "Initialt Omfång",
    "stats.response": "Svarstid",
    "stats.updates": "Datauppdateringar",
    "stats.realtime": "Realtid",

    // Features (AI)
    "features.subtitle": "Kapaciteter",
    "features.title": "Handlingsbar Intelligens",
    "features.ownership.title": "Kompletta Ägarkedjor",
    "features.ownership.desc": "Spåra dolda verkliga ägare genom flera företagslager omedelbart.",
    "features.mapping.title": "Intelligent Marknadskartläggning",
    "features.mapping.desc": "Upptäck icke-uppenbara konkurrenter och förvärvsmål med AI-likhetskluster.",
    "features.leads.title": "Kvalificerade Leads",
    "features.leads.desc": "Generera högvärdiga prospekt från realtidsnätverksmönster och ägarförändringar.",
    "features.database.title": "Grafdatabas",
    "features.database.desc": "Neo4j-driven relationsanalys med vektorinbäddningar för djupa insikter.",
    "features.api.title": "REST API",
    "features.api.desc": "Säkra, högpresterande endpoints via Google Cloud Run med under 100ms latens.",
    "features.security.title": "Företagssäkerhet",
    "features.security.desc": "API-nyckelautentisering, hastighetsbegränsning och krypterad dataöverföring.",

    // Architecture (AI)
    "arch.subtitle": "Infrastruktur",
    "arch.title": "Byggd för Skala",
    "arch.data.label": "Datalager",
    "arch.data.value": "Realtidsaggregering från svenska företagsregister",
    "arch.intelligence.label": "Intelligens",
    "arch.intelligence.value": "Neo4j grafdatabas + vektorinbäddningar",
    "arch.clustering.label": "Klustring",
    "arch.clustering.value": "Leiden-algoritm för marknadssegmentering",
    "arch.delivery.label": "Leverans",
    "arch.delivery.value": "Google Cloud Run + Cloud Endpoints",

    // CTA (AI)
    "cta.title": "Kontrollera informationsflödet",
    "cta.description": "Gå med ledande nordiska fonder och företag som använder Northern Lights för strategisk fördel.",
    "cta.button": "Begär API-åtkomst",

    // Footer (AI)
    "footer.tagline": "Nordisk Företagsintelligensplattform",

    // Data Table (Hub)
    allEntities: "Alla enheter",
    companies: "Företag",
    company: "Företag",
    investors: "Investerare",
    fund: "Fond",
    results: "resultat",
    search: "Sök...",
    type: "Typ",
    name: "Namn",
    orgNo: "Org Nr.",
    sector: "Sektor",
    cluster: "Kluster",
    ownership: "Ägande",
    country: "Land",

    // Chat Panel (Hub)
    ingestionAgent: "Inmatningsagent",
    addCompany: "Lägg till företag...",
    readyToProcess: "Redo att behandla inmatningsförfrågningar. Ange ett företagsnamn eller org-nummer för att lägga till i registret.",
    queuing: "Köar \"{input}\" för inmatning. Bearbetningen slutförs om ~5 minuter.",
    foundEntity: "Hittade matchande enhet. Genererar vektorinbäddningar och tilldelar till Kluster #3.",
    ingestionComplete: "Inmatning klar. Enhet tillagd i grafen med 4 identifierade ägarkopplingar.",
  },
} as const;

export type TranslationKey = keyof typeof translations.en;
