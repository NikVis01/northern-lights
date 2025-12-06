"""
Python script to delete company nodes from Neo4j using Cypher queries.
"""
import sys
from app.db.neo4j_client import get_driver


def delete_company(company_id: str, dry_run: bool = True):
    """
    Delete a company node by organization_id.
    
    Args:
        company_id: Swedish organization number (e.g., "556043-4200")
        dry_run: If True, only show what would be deleted without actually deleting
    """
    driver = get_driver()
    
    with driver.session() as session:
        if dry_run:
            # Check what will be deleted
            query = """
            MATCH (c:Company {company_id: $company_id})
            OPTIONAL MATCH (c)-[r]-(connected)
            RETURN c, labels(c) as labels, count(r) as relationship_count, 
                   collect(DISTINCT type(r)) as relationship_types,
                   collect(DISTINCT labels(connected)) as connected_labels
            """
            result = session.run(query, company_id=company_id)
            record = result.single()
            
            if record and record["c"]:
                company = dict(record["c"])
                print(f"Would delete company: {company.get('name', 'Unknown')} ({company_id})")
                print(f"  Relationships: {record['relationship_count']}")
                print(f"  Relationship types: {record['relationship_types']}")
                print(f"  Connected nodes: {record['connected_labels']}")
                return False
            else:
                print(f"Company {company_id} not found")
                return False
        else:
            # Actually delete
            query = """
            MATCH (c:Company {company_id: $company_id})
            DETACH DELETE c
            RETURN count(c) as deleted_count
            """
            result = session.run(query, company_id=company_id)
            record = result.single()
            deleted = record["deleted_count"] if record else 0
            
            if deleted > 0:
                print(f"✅ Deleted company {company_id}")
            else:
                print(f"⚠️  Company {company_id} not found")
            return deleted > 0


def delete_multiple_companies(company_ids: list[str], dry_run: bool = True):
    """
    Delete multiple company nodes.
    
    Args:
        company_ids: List of organization numbers
        dry_run: If True, only show what would be deleted
    """
    driver = get_driver()
    
    with driver.session() as session:
        if dry_run:
            query = """
            MATCH (c:Company)
            WHERE c.company_id IN $company_ids
            OPTIONAL MATCH (c)-[r]-()
            RETURN c.company_id as id, c.name as name, count(r) as relationship_count
            """
            result = session.run(query, company_ids=company_ids)
            print(f"Would delete {len(company_ids)} companies:")
            for record in result:
                print(f"  - {record['name']} ({record['id']}): {record['relationship_count']} relationships")
        else:
            query = """
            MATCH (c:Company)
            WHERE c.company_id IN $company_ids
            DETACH DELETE c
            RETURN count(c) as deleted_count
            """
            result = session.run(query, company_ids=company_ids)
            record = result.single()
            deleted = record["deleted_count"] if record else 0
            print(f"✅ Deleted {deleted} companies")


def delete_placeholder_companies(dry_run: bool = True):
    """
    Delete companies with placeholder IDs (non-numeric, short IDs like "ERICSSON").
    
    Args:
        dry_run: If True, only show what would be deleted
    """
    driver = get_driver()
    
    with driver.session() as session:
        if dry_run:
            query = """
            MATCH (c:Company)
            WHERE NOT c.company_id =~ '^[0-9]{6}-[0-9]{4}$'  // Not valid org number format
               AND NOT c.company_id =~ '^[0-9]{10}$'          // Not 10 digits
            OPTIONAL MATCH (c)-[r]-()
            RETURN c.company_id as id, c.name as name, count(r) as relationship_count
            ORDER BY c.company_id
            """
            result = session.run(query)
            companies = list(result)
            print(f"Would delete {len(companies)} placeholder companies:")
            for record in companies:
                print(f"  - {record['name']} ({record['id']}): {record['relationship_count']} relationships")
        else:
            query = """
            MATCH (c:Company)
            WHERE NOT c.company_id =~ '^[0-9]{6}-[0-9]{4}$'
               AND NOT c.company_id =~ '^[0-9]{10}$'
            DETACH DELETE c
            RETURN count(c) as deleted_count
            """
            result = session.run(query)
            record = result.single()
            deleted = record["deleted_count"] if record else 0
            print(f"✅ Deleted {deleted} placeholder companies")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Delete company nodes from Neo4j")
    parser.add_argument("--id", help="Single company ID to delete")
    parser.add_argument("--ids", nargs="+", help="Multiple company IDs to delete")
    parser.add_argument("--placeholders", action="store_true", help="Delete placeholder companies")
    parser.add_argument("--execute", action="store_true", help="Actually delete (default is dry-run)")
    
    args = parser.parse_args()
    
    dry_run = not args.execute
    
    if args.id:
        delete_company(args.id, dry_run=dry_run)
    elif args.ids:
        delete_multiple_companies(args.ids, dry_run=dry_run)
    elif args.placeholders:
        delete_placeholder_companies(dry_run=dry_run)
    else:
        parser.print_help()


