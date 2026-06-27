import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

class Neo4jClient:
    """
    Handles all Neo4j connections and queries.
    Single instance shared across the app.
    """

    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(
                os.getenv("NEO4J_USERNAME"),
                os.getenv("NEO4J_PASSWORD")
            )
        )

    def close(self):
        self.driver.close()

    def verify_connection(self):
        """Test Neo4j connection on startup."""
        with self.driver.session() as session:
            result = session.run("RETURN 'Connected to Neo4j' AS message")
            return result.single()["message"]

    # ─── Write Operations ───────────────────────────────

    def create_repository(self, repo_name: str):
        """Create or update a repository node."""
        with self.driver.session() as session:
            session.run("""
                MERGE (r:Repository {name: $repo_name})
                ON CREATE SET r.created_at = datetime()
                ON MATCH SET r.last_seen = datetime()
            """, repo_name=repo_name)

    def create_file_node(self, repo_name: str, file_path: str):
        """Create a file node and link it to its repository."""
        with self.driver.session() as session:
            session.run("""
                MERGE (r:Repository {name: $repo_name})
                MERGE (f:File {path: $file_path, repo: $repo_name})
                ON CREATE SET f.created_at = datetime()
                MERGE (r)-[:CONTAINS]->(f)
            """, repo_name=repo_name, file_path=file_path)

    def create_dependency(self, 
                          repo_name: str,
                          source_file: str, 
                          target_file: str,
                          dependency_type: str = "IMPORTS"):
        """
        Create dependency relationship between two files.
        dependency_type: IMPORTS, CALLS, EXTENDS, IMPLEMENTS
        """
        with self.driver.session() as session:
            session.run(f"""
                MERGE (s:File {{path: $source, repo: $repo_name}})
                MERGE (t:File {{path: $target, repo: $repo_name}})
                MERGE (s)-[:{dependency_type}]->(t)
            """, source=source_file, 
                target=target_file,
                repo_name=repo_name)

    def store_pr_review(self, 
                        repo_name: str, 
                        pr_number: int,
                        pr_title: str,
                        changed_files: list,
                        summary: str):
        """
        Store PR review history in graph.
        Used for context in future reviews of same files.
        """
        with self.driver.session() as session:
            session.run("""
                MERGE (r:Repository {name: $repo_name})
                CREATE (pr:PullRequest {
                    number: $pr_number,
                    title: $pr_title,
                    reviewed_at: datetime(),
                    summary: $summary
                })
                MERGE (r)-[:HAS_PR]->(pr)
            """, repo_name=repo_name,
                pr_number=pr_number,
                pr_title=pr_title,
                summary=summary)

            # Link PR to files it changed
            for file_path in changed_files:
                session.run("""
                    MATCH (pr:PullRequest {number: $pr_number})
                    MERGE (f:File {path: $file_path, repo: $repo_name})
                    MERGE (pr)-[:CHANGED]->(f)
                """, pr_number=pr_number,
                    file_path=file_path,
                    repo_name=repo_name)

    # ─── Read Operations ────────────────────────────────

    def get_file_dependencies(self, 
                               repo_name: str,
                               file_path: str) -> list:
        """
        Get all files that depend on the given file.
        These are files that could be IMPACTED by changes.
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (f:File {path: $file_path, repo: $repo_name})
                      <-[:IMPORTS|CALLS|EXTENDS|IMPLEMENTS]-(dependent:File)
                RETURN dependent.path AS path
            """, file_path=file_path, repo_name=repo_name)
            return [record["path"] for record in result]

    def get_downstream_impact(self, 
                               repo_name: str,
                               changed_files: list) -> dict:
        """
        For each changed file, find all downstream dependents.
        Returns impact map: {changed_file: [impacted_files]}
        """
        impact_map = {}
        for file_path in changed_files:
            dependents = self.get_file_dependencies(repo_name, file_path)
            if dependents:
                impact_map[file_path] = dependents

        return impact_map

    def get_pr_history(self, 
                        repo_name: str,
                        file_path: str,
                        limit: int = 5) -> list:
        """
        Get recent PR history for a file.
        Gives context about how often this file changes.
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (pr:PullRequest)-[:CHANGED]->(f:File {
                    path: $file_path, 
                    repo: $repo_name
                })
                RETURN pr.number AS pr_number,
                       pr.title AS title,
                       pr.reviewed_at AS reviewed_at
                ORDER BY pr.reviewed_at DESC
                LIMIT $limit
            """, file_path=file_path, 
                repo_name=repo_name,
                limit=limit)
            return [dict(record) for record in result]

    def get_most_changed_files(self, 
                                repo_name: str,
                                limit: int = 10) -> list:
        """
        Find files changed most frequently — hotspots.
        Useful for risk assessment.
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (pr:PullRequest)-[:CHANGED]->(f:File {repo: $repo_name})
                RETURN f.path AS file, COUNT(pr) AS change_count
                ORDER BY change_count DESC
                LIMIT $limit
            """, repo_name=repo_name, limit=limit)
            return [dict(record) for record in result]

# Single shared instance
neo4j_client = Neo4jClient()