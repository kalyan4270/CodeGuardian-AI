import re
from graph.neo4j_client import neo4j_client

def extract_changed_files(pr_diff: str) -> list:
    """
    Extracts list of changed file paths from PR diff.
    Looks for lines starting with 'diff --git'
    """
    files = []
    for line in pr_diff.split("\n"):
        if line.startswith("diff --git"):
            # Format: diff --git a/path/to/file.py b/path/to/file.py
            parts = line.split(" ")
            if len(parts) >= 4:
                # Take the b/ version (new file path)
                file_path = parts[3].replace("b/", "", 1)
                files.append(file_path)
    return files

def extract_imports(pr_diff: str, file_path: str) -> list:
    """
    Extracts import statements from diff to build
    dependency relationships in Neo4j.
    Handles Python imports for now.
    Phase 3+ can extend to Java, JS, etc.
    """
    imports = []
    in_target_file = False

    for line in pr_diff.split("\n"):
        # Track which file we're in
        if file_path in line and line.startswith("diff --git"):
            in_target_file = True
            continue
        if line.startswith("diff --git") and file_path not in line:
            in_target_file = False

        if in_target_file and line.startswith("+"):
            # Python imports
            if line.startswith("+import ") or line.startswith("+from "):
                clean = line[1:].strip()
                imports.append(clean)

    return imports

def import_to_file_path(import_str: str) -> str:
    """
    Convert import statement to file path.
    e.g. 'from agents.security_agent import ...' 
      -> 'agents/security_agent.py'
    """
    # Extract module name
    if import_str.startswith("from "):
        module = import_str.split(" ")[1]
    elif import_str.startswith("import "):
        module = import_str.split(" ")[1].split(" as ")[0]
    else:
        return None

    # Skip standard library and third party
    skip_prefixes = [
        "os", "sys", "re", "json", "typing",
        "fastapi", "groq", "neo4j", "langchain",
        "langgraph", "pydantic", "dotenv", "httpx",
        "concurrent", "asyncio", "datetime"
    ]

    root_module = module.split(".")[0]
    if root_module in skip_prefixes:
        return None

    # Convert module path to file path
    return module.replace(".", "/") + ".py"

def build_knowledge_graph(repo_name: str, 
                           pr_number: int,
                           pr_title: str,
                           pr_diff: str,
                           pr_summary: str = ""):
    """
    Main function to build/update Neo4j knowledge graph
    from PR data.

    Creates:
    - Repository node
    - File nodes for changed files
    - Dependency edges from import analysis
    - PR node linked to changed files
    """
    # Step 1: Create repository node
    neo4j_client.create_repository(repo_name)

    # Step 2: Extract changed files from diff
    changed_files = extract_changed_files(pr_diff)

    if not changed_files:
        return {
            "changed_files": [],
            "dependencies_mapped": 0,
            "message": "No file changes detected in diff"
        }

    # Step 3: Create file nodes and dependency edges
    dependencies_mapped = 0
    for file_path in changed_files:

        # Create file node
        neo4j_client.create_file_node(repo_name, file_path)

        # Extract and map imports as dependencies
        imports = extract_imports(pr_diff, file_path)
        for import_str in imports:
            dep_path = import_to_file_path(import_str)
            if dep_path:
                neo4j_client.create_file_node(repo_name, dep_path)
                neo4j_client.create_dependency(
                    repo_name=repo_name,
                    source_file=file_path,
                    target_file=dep_path,
                    dependency_type="IMPORTS"
                )
                dependencies_mapped += 1

    # Step 4: Store PR review history
    neo4j_client.store_pr_review(
        repo_name=repo_name,
        pr_number=pr_number,
        pr_title=pr_title,
        changed_files=changed_files,
        summary=pr_summary
    )

    return {
        "changed_files": changed_files,
        "dependencies_mapped": dependencies_mapped,
        "message": f"Graph updated with {len(changed_files)} files"
    }