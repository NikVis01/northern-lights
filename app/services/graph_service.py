from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from app.db.neo4j_client import get_driver


class GraphService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._driver = None

    @property
    def model(self):
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def driver(self):
        if self._driver is None:
            self._driver = get_driver()
        return self._driver

    def _generate_embedding_text(self, node_data: Dict[str, Any]) -> str:
        """
        Construct a single string representation of the node for embedding.
        """

        # Helper to safely get list or string and format
        def safe_get(key: str) -> str:
            val = node_data.get(key)
            if val is None:
                return ""
            if isinstance(val, list):
                # Handle list of complex objects (dicts) or strings
                if val and isinstance(val[0], dict):
                    # If it's a list of EntityRefs or similar dicts, maybe just extract names?
                    # For now, let's just stringify.
                    # Better: extract names if available.
                    return ", ".join([str(v.get("name", v)) for v in val])
                return ", ".join([str(v) for v in val])
            return str(val)

        parts = [
            f"Name: {node_data.get('name', '')}",
            f"ID: {node_data.get('company_id', '')}",
            f"Aliases: {safe_get('aliases')}",
            f"Description: {node_data.get('description', '')}",
            f"Mission: {node_data.get('mission', '')}",
            f"Sectors: {safe_get('sectors')}",
            f"Country: {node_data.get('country_code', '')}",
            f"Year Founded: {node_data.get('year_founded', '')}",
            f"Employees: {node_data.get('num_employees', '')}",
            f"Key People: {safe_get('key_people')}",
            f"Investment Thesis: {node_data.get('investment_thesis', '')}",
            f"Website: {node_data.get('website', '')}",
            # Include portfolio names if available
            f"Portfolio: {safe_get('portfolio')}",
        ]
        return ". ".join(filter(lambda x: len(x.split(": ", 1)[1]) > 0, parts))

    def generate_and_store_embeddings(self, batch_size: int = 100):
        """
        Fetch all Company and Fund nodes, generate embeddings, and write them back to Neo4j.
        """
        query_fetch = """
        MATCH (n)
        WHERE (n:Company OR n:Fund)
        RETURN labels(n) as labels,
               n.company_id as company_id, 
               n.name as name, 
               n.description as description, 
               n.mission as mission, 
               n.sectors as sectors, 
               n.aliases as aliases,
               n.country_code as country_code, 
               n.year_founded as year_founded,
               n.num_employees as num_employees, 
               n.num_shares as num_shares,
               n.portfolio as portfolio, 
               n.shareholders as shareholders,
               n.customers as customers, 
               n.key_people as key_people,
               n.website as website,
               n.investment_thesis as investment_thesis
        """

        with self.driver.session() as session:
            result = session.run(query_fetch)
            nodes_data = [dict(record) for record in result]

        if not nodes_data:
            print("No nodes found for embedding generation.")
            return

        # Process in batches
        for i in range(0, len(nodes_data), batch_size):
            batch_data = nodes_data[i : i + batch_size]

            # Clean data (ensure lists are lists)
            processed_batch = []
            for d in batch_data:
                # Sanitize list fields
                for field in [
                    "sectors",
                    "aliases",
                    "portfolio",
                    "shareholders",
                    "customers",
                    "key_people",
                ]:
                    if d.get(field) is None:
                        d[field] = []
                processed_batch.append(d)

            texts = [self._generate_embedding_text(node) for node in processed_batch]
            embeddings = self.model.encode(texts)

            # Update back to Neo4j
            update_query = """
            UNWIND $updates as update
            MATCH (n {company_id: update.company_id})
            SET n._embedding = update.embedding, n.vector = update.embedding
            """

            updates = []
            for node_data, embedding in zip(processed_batch, embeddings):
                if node_data.get("company_id"):
                    updates.append({"company_id": node_data["company_id"], "embedding": embedding.tolist()})

            if updates:
                with self.driver.session() as session:
                    session.run(update_query, updates=updates)
                print(f"Processed batch {i // batch_size + 1}: {len(updates)} nodes updated.")

    def run_knn_projection(self, projection_name: str = "graph_projection", k: int = 10):
        """
        Project the graph using K-NN similarity on the `_embedding` property.
        """
        from app.db.neo4j_client import get_gds_session

        gds = get_gds_session()

        # Ensure GDS is available
        try:
            gds.version()
        except Exception:
            print("GDS not available (checked via library).")
            return

        # Use unique graph name to avoid conflicts (can't drop remotely)
        import time

        unique_projection_name = f"{projection_name}_{int(time.time())}"
        print(f"Creating graph projection: {unique_projection_name}")

        # 2. Project graph using Cypher queries (required for AuraDS Sessions)
        node_query = """
        MATCH (n)
        WHERE n:Company OR n:Fund
        RETURN id(n) AS id, labels(n) AS labels, n._embedding AS _embedding
        """

        relationship_query = """
        MATCH (s)-[r]->(t)
        WHERE (s:Company OR s:Fund) AND (t:Company OR t:Fund)
        RETURN id(s) AS source, id(t) AS target, type(r) AS type
        """

        G, _ = gds.graph.project(projection_name, node_query, relationship_query)
        # 3. Run K-NN and write relationships
        gds.knn.write(
            G, nodeProperties=["_embedding"], writeRelationshipType="SIMILAR_TO", writeProperty="score", topK=k
        )

    def run_leiden_clustering(self, projection_name: str = "graph_projection"):
        """
        Run Leiden clustering on the projected graph.
        """
        from app.db.neo4j_client import get_gds_session

        gds = get_gds_session()

        # Ensure GDS is available
        try:
            gds.version()
        except Exception:
            print("GDS not available.")
            return

        # Use unique graph name to avoid conflicts
        import time

        unique_projection_name = f"{projection_name}_{int(time.time())}"
        print(f"Creating graph projection: {unique_projection_name}")

        # 1. Project nodes with embedding using Cypher queries
        node_query = """
        MATCH (n)
        WHERE n:Company OR n:Fund
        RETURN id(n) AS id, labels(n) AS labels, n._embedding AS _embedding
        """

        relationship_query = """
        MATCH (s)-[r]->(t)
        WHERE (s:Company OR s:Fund) AND (t:Company OR t:Fund)
        RETURN id(s) AS source, id(t) AS target, type(r) AS type
        """

        G, _ = gds.graph.project(projection_name, node_query, relationship_query)
        # 2. Mutate K-NN
        gds.knn.mutate(
            G, nodeProperties=["_embedding"], mutateRelationshipType="SIMILAR_TO", mutateProperty="score", topK=10
        )

        # 3. Run Leiden and write back
        result = gds.leiden.write(G, relationshipTypes=["SIMILAR_TO"], writeProperty="cluster_id")
        gds.graph.drop(G)

        return result


if __name__ == "__main__":
    print("Starting Northern Lights Graph Pipeline...")
    service = GraphService()

    # Make sure gds is installed and enabled
    gds_available = False
    try:
        from app.db.neo4j_client import get_gds_session

        gds = get_gds_session()
        # Check via GDS client
        gds.version()
        gds_available = True
    except Exception as e:
        print(f"Warning: Graph Data Science (GDS) library not found or not connected: {e}")
        print("Clustering steps will be skipped.")

    print("Step 1: Generating and Storing Embeddings...")
    service.generate_and_store_embeddings()
    print("Embeddings generated.")

    if gds_available:
        print("Step 2: Running K-NN and Leiden Clustering...")
        try:
            result = service.run_leiden_clustering()
            print(f"Clustering complete. Stats: {result}")
        except Exception as e:
            print(f"Clustering failed. Ensure GDS is installed and enabled on your Neo4j instance. Error: {e}")
    else:
        print("Skipping Step 2 (Clustering) - GDS not available.")

    print("Pipeline finished.")
