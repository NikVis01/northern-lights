from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
from graphdatascience.session import GdsSessions, AuraAPICredentials, DbmsConnectionInfo, SessionMemory

load_dotenv()

# URI examples: "neo4j://localhost", "neo4j+s://xxx.databases.neo4j.io"
URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
CLIENT_SECRET = os.getenv("AURA_CLIENT_SECRET")
CLIENT_ID = os.getenv("AURA_CLIENT_ID")

_driver = None
_gds_session = None
_gds_sessions_manager = None


def get_gds_session():
    """
    Returns a GDS session for AuraDS operations using the Sessions API.
    """
    global _gds_session, _gds_sessions_manager

    if _gds_session is None:
        client_id = os.getenv("AURA_CLIENT_ID")
        client_secret = os.getenv("AURA_CLIENT_SECRET")
        project_id = os.getenv("AURA_PROJECT_ID")  # Optional, can be None
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD")

        if not client_id or not client_secret:
            raise ValueError(
                "GDS credentials not configured. Set AURA_CLIENT_ID and AURA_CLIENT_SECRET environment variables."
            )

        if not neo4j_uri or not neo4j_password:
            raise ValueError(
                "Neo4j credentials not configured. Set NEO4J_URI and NEO4J_PASSWORD environment variables."
            )

        # Create GdsSessions manager
        _gds_sessions_manager = GdsSessions(api_credentials=AuraAPICredentials(client_id, client_secret, project_id))

        # Create database connection info
        db_connection = DbmsConnectionInfo(uri=neo4j_uri, username=neo4j_username, password=neo4j_password)

        # Get or create a session
        _gds_session = _gds_sessions_manager.get_or_create(
            session_name="northern-lights-gds-session",
            memory=SessionMemory.m_4GB,
            db_connection=db_connection,
        )

    return _gds_session


def close_gds_session():
    """
    Close and delete the GDS session when the app is closed.
    """
    global _gds_session
    if _gds_session is not None:
        try:
            _gds_session.delete()
            print("GDS session deleted successfully.")
        except Exception as e:
            print(f"Error deleting GDS session: {e}")
        finally:
            _gds_session = None


def get_driver():
    global _driver
    if _driver is None:
        if not URI or not AUTH[0] or not AUTH[1]:
            raise ValueError(
                "Neo4j credentials not configured. Set NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD environment variables."
            )
        _driver = GraphDatabase.driver(URI, auth=AUTH)
    return _driver


def close_driver():
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def verify_connectivity():
    driver = get_driver()
    driver.verify_connectivity()
