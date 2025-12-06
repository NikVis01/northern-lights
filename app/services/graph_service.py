from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from app.db.neo4j_client import get_driver
from app.models.company import CompanyOut
from app.models.investor import InvestorOut


class GraphService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.driver = get_driver()

    def _generate_embedding_text(self, node: CompanyOut | InvestorOut) -> str:
        """
        Construct a single string representation of the node for embedding.
        """
        parts = [
            f"Name: {node.name}",
            f"Organization ID: {node.organization_id}",
            f"Aliases: {getattr(node, 'aliases', [])}",
            f"Description: {node.description}",
            f"Mission: {getattr(node, 'mission', '')}",
            f"Sectors: {', '.join(getattr(node, 'sectors', []))}",
            f"Country_code: {node.country_code}",
            f"Year_founded: {getattr(node, 'year_founded', '')}",
            f"Num_employees: {getattr(node, 'num_employees', '')}",
            f"Num_shares: {getattr(node, 'num_shares', '')}",
            f"Portfolio: {getattr(node, 'portfolio', [])}",
            f"Shareholders: {getattr(node, 'shareholders', [])}",
            f"Customers: {getattr(node, 'customers', [])}",
            f"Key_people: {getattr(node, 'key_people', [])}",
            f"Website: {getattr(node, 'website', '')}",
        ]
        return ". ".join(filter(None, parts))

    def generate_and_store_embeddings(self, batch_size: int = 100):
        """
        Fetch all Company and Fund nodes without embeddings (or update all),
        generate embeddings, and write them back to Neo4j.
        """
        # Fetch nodes that need embeddings (or just all valid nodes)
        # We fetch labels to determine which Pydantic model to use
        query_fetch = """
        MATCH (n)
        WHERE (n:Company OR n:Fund)
        RETURN labels(n) as labels,
               n.company_id as company_id, n.name as name, n.organization_id as organization_id, 
               n.description as description, 
               n.mission as mission, n.sectors as sectors, n.aliases as aliases,
               n.country_code as country_code, n.year_founded as year_founded,
               n.num_employees as num_employees, n.num_shares as num_shares,
               n.portfolio as portfolio, n.shareholders as shareholders,
               n.customers as customers, n.key_people as key_people,
               n.website as website
        """

        with self.driver.session() as session:
            result = session.run(query_fetch)
            nodes_data = [dict(record) for record in result]

        # Process in batches
        for i in range(0, len(nodes_data), batch_size):
            batch_data = nodes_data[i : i + batch_size]

            # Convert dicts to Pydantic models
            batch_models = []
            for d in batch_data:
                # Sanitize list fields that might be None from DB
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

                # Determine type
                labels = d.get("labels", [])
                if "Company" in labels:
                    # Depending on exact model definition, we might need to be careful with extra fields
                    # CompanyOut expects specific fields.
                    # 'investor_id' vs 'company_id' is a difference in the models?
                    # CompanyOut uses company_id. InvestorOut uses investor_id.
                    # The query returns 'company_id' as alias.
                    # In DB, both probably have 'company_id' property based on previous queries.
                    # But InvestorOut definition has 'investor_id'.
                    # We might need to map it.
                    try:
                        batch_models.append(CompanyOut(**d))
                    except Exception as e:
                        print(f"Skipping invalid company {d.get('company_id')}: {e}")
                        continue
                elif "Fund" in labels:
                    # Map company_id to investor_id for InvestorOut
                    d["investor_id"] = d.get("company_id")
                    try:
                        batch_models.append(InvestorOut(**d))
                    except Exception as e:
                        print(f"Skipping invalid investor {d.get('company_id')}: {e}")
                        continue

            if not batch_models:
                continue

            texts = [self._generate_embedding_text(model) for model in batch_models]
            embeddings = self.model.encode(texts)

            # Update back to Neo4j
            update_query = """
            UNWIND $updates as update
            MATCH (n {company_id: update.company_id})
            SET n._embedding = update.embedding, n.vector = update.embedding
            """

            updates = []
            for model, embedding in zip(batch_models, embeddings):
                # Both models might not have company_id attribute if InvestorOut uses investor_id
                # But we know they came from nodes with company_id.
                # Let's use the ID we know.
                cid = getattr(model, "company_id", None) or getattr(
                    model, "organization_id", None
                )
                invid = getattr(model, "investor_id", None)

                # Note: The MATCH query uses company_id, which is the unique ID in our graph.
                # Even for investors, we match on company_id in the DB.
                # So we should prefer sending the ID that matches the node property 'company_id'.
                # In InvestorOut, we mapped company_id -> investor_id.
                # So we should grab that back.

                target_id = cid if cid else invid

                if target_id:
                    updates.append(
                        {"company_id": target_id, "embedding": embedding.tolist()}
                    )

            with self.driver.session() as session:
                session.run(update_query, updates=updates)

    def run_knn_projection(
        self, projection_name: str = "graph_projection", k: int = 10
    ):
        """
        Project the graph using K-NN similarity on the `_embedding` property.
        """
        # Improved approach: Use gds.knn.write to write relationships directly
        # Or project into memory first. Let's do in-memory projection + write relationships

        # 1. Project nodes with embeddings
        # Note: We usually need a named graph for GDS

        # Ensure GDS is available
        check_gds = "RETURN gds.version()"
        # (Error handling omitted for brevity, assuming GDS exists per plan)

        # Drop projection if exists
        drop_query = f"""
        CALL gds.graph.drop('{projection_name}', false)
        """

        # Project graph
        project_query = f"""
        CALL gds.graph.project(
          '{projection_name}',
          ['Company', 'Fund'],
          {{}},
          {{
            nodeProperties: ['_embedding']
          }}
        )
        """

        # Run K-NN and write relationships (SIMILAR_TO)
        knn_query = f"""
        CALL gds.knn.write(
          '{projection_name}',
          {{
            nodeProperties: ['_embedding'],
            writeRelationshipType: 'SIMILAR_TO',
            writeProperty: 'score',
            topK: $k
          }}
        )
        YIELD nodesCompared, relationshipsWritten
        """

        with self.driver.session() as session:
            session.run(drop_query)
            session.run(project_query)
            session.run(knn_query, k=k)

    def run_leiden_clustering(self, projection_name: str = "graph_projection"):
        """
        Run Leiden clustering on the projected graph (which now implies similarity edges,
        BUT wait - gds.knn.write writes to DB, not necessarily to the in-memory projection
        unless we mutate.

        Better path:
        1. Project nodes.
        2. Mutate (add SIMILAR_TO to in-memory graph).
        3. Run Leiden on in-memory graph.
        4. Write cluster_id back to DB.
        """

        # Re-doing the flow for optimization in one go:

        drop_query = f"CALL gds.graph.drop('{projection_name}', false)"

        # Project nodes with embedding
        project_query = f"""
        CALL gds.graph.project(
            '{projection_name}',
            ['Company', 'Fund'],
            {{}},
            {{
                nodeProperties: ['_embedding']
            }}
        )
        """

        # Mutate K-NN (add relationships to in-memory graph)
        knn_mutate_query = f"""
        CALL gds.knn.mutate(
            '{projection_name}',
            {{
                nodeProperties: ['_embedding'],
                mutateRelationshipType: 'SIMILAR_TO',
                mutateProperty: 'score',
                topK: 10
            }}
        )
        """

        # Run Leiden and write back
        leiden_write_query = f"""
        CALL gds.leiden.write(
            '{projection_name}',
            {{
                relationshipTypes: ['SIMILAR_TO'],
                writeProperty: 'cluster_id'
            }}
        )
        YIELD nodeCount, communityCount
        """

        with self.driver.session() as session:
            session.run(drop_query)
            session.run(project_query)
            session.run(knn_mutate_query)
            result = session.run(leiden_write_query)

            # Cleanup
            session.run(drop_query)
            return result.single()


if __name__ == "__main__":
    print("Starting Northern Lights Graph Pipeline...")
    service = GraphService()

    print("Step 1: Generating and Storing Embeddings...")
    service.generate_and_store_embeddings()
    print("Embeddings generated.")

    print("Step 2: Running K-NN and Leiden Clustering...")
    try:
        result = service.run_leiden_clustering()
        print(f"Clustering complete. Stats: {result}")
    except Exception as e:
        print(
            f"Clustering failed. Ensure GDS is installed and enabled on your Neo4j instance. Error: {e}"
        )

    print("Pipeline finished.")
