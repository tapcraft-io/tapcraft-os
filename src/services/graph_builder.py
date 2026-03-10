"""Build workflow graphs by parsing source code for activity references.

Scans workflow Python files using AST to find ``workflow.execute_activity()``
calls, extracts the activity code symbols, and creates corresponding Graph
nodes and edges in the database.  This connects workflows to their activities
so the UI can display usage relationships and workflow structure.

The builder is idempotent — re-running it skips workflows that already have
populated graphs (graphs with at least one node).
"""

from __future__ import annotations

import ast
import logging
from typing import Any, Dict, List, Optional

from src.db.base import AsyncSessionLocal
from src.services import crud

LOGGER = logging.getLogger(__name__)


def extract_activity_symbols(source_code: str) -> List[str]:
    """Parse Python source and extract activity code symbols from execute_activity calls.

    Looks for patterns like:
        workflow.execute_activity("pipeline.score_signals", ...)
        workflow.execute_activity("arxiv.search", input, ...)

    Returns a list of string symbols in call order (preserving duplicates removed).
    """
    symbols: list[str] = []
    seen: set[str] = set()

    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return symbols

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        # Match: workflow.execute_activity(...)
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "execute_activity"):
            continue

        # First argument should be a string literal (the activity name)
        if (
            node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            symbol = node.args[0].value
            if symbol not in seen:
                symbols.append(symbol)
                seen.add(symbol)

    return symbols


async def build_graphs_for_workspace(workspace_id: int) -> Dict[str, int]:
    """Scan all workflows in a workspace and build their graphs from source code.

    For each workflow:
    1. Read the workflow source file from the workspace directory.
    2. Parse it to find execute_activity() calls.
    3. Match activity symbols to ActivityOperation records.
    4. Create Graph nodes (one per activity call) and edges (call order).

    Returns counts of graphs built and nodes created.
    """
    stats = {"graphs_built": 0, "nodes_created": 0, "edges_created": 0, "skipped": 0}

    async with AsyncSessionLocal() as db:
        # Load all workflows
        workflows = await crud.list_workflows(db=db, workspace_id=workspace_id)
        if not workflows:
            return stats

        # Load all activity operations and index by code_symbol
        activities = await crud.list_activities(db=db, workspace_id=workspace_id)
        symbol_to_op: Dict[str, Any] = {}
        for act in activities:
            for op in act.operations:
                symbol_to_op[op.code_symbol] = op

        for wf in workflows:
            # Skip if graph already has nodes
            if wf.graph_id:
                graph = await crud.get_graph(db=db, graph_id=wf.graph_id, load_nodes_edges=True)
                if graph and graph.nodes:
                    stats["skipped"] += 1
                    continue

            # Find the workflow source file
            source = _find_workflow_source(wf.entrypoint_symbol)
            if not source:
                continue

            # Extract activity symbols from the source
            symbols = extract_activity_symbols(source)
            if not symbols:
                continue

            # Ensure workflow has a graph
            graph_id = wf.graph_id
            if not graph_id:
                graph = await crud.create_graph(
                    db=db,
                    workspace_id=workspace_id,
                    owner_type="workflow",
                    owner_id=wf.id,
                )
                wf.graph_id = graph.id
                graph_id = graph.id
                await db.commit()

            # Create nodes for each activity reference
            prev_node_id: Optional[int] = None
            first_node_id: Optional[int] = None

            for i, symbol in enumerate(symbols):
                op = symbol_to_op.get(symbol, None)
                activity_op_id: Optional[int] = op.id if op else None

                # Use the symbol as label, with human-friendly display
                label = symbol.rsplit(".", 1)[-1].replace("_", " ").title()

                node = await crud.create_node(
                    db=db,
                    graph_id=graph_id,
                    kind="activity_operation" if activity_op_id else "primitive",
                    label=label,
                    activity_operation_id=activity_op_id,
                    config=f'{{"code_symbol": "{symbol}"}}',
                    ui_position=f'{{"x": {150 * i}, "y": 100}}',
                )
                stats["nodes_created"] += 1

                if first_node_id is None:
                    first_node_id = node.id

                # Create edge from previous node
                if prev_node_id is not None:
                    await crud.create_edge(
                        db=db,
                        graph_id=graph_id,
                        from_node_id=prev_node_id,
                        to_node_id=node.id,
                    )
                    stats["edges_created"] += 1

                prev_node_id = node.id

            # Set entry node
            if first_node_id:
                await crud.update_graph(db=db, graph_id=graph_id, entry_node_id=first_node_id)

            stats["graphs_built"] += 1
            LOGGER.info(
                "Built graph for workflow '%s': %d nodes from %d activity calls",
                wf.name,
                len(symbols),
                len(symbols),
            )

    LOGGER.info(
        "Graph build complete: %d graphs built, %d nodes, %d edges, %d skipped",
        stats["graphs_built"],
        stats["nodes_created"],
        stats["edges_created"],
        stats["skipped"],
    )
    return stats


def _find_workflow_source(entrypoint_symbol: str) -> Optional[str]:
    """Find and read the source file for a workflow by its entrypoint symbol.

    The entrypoint_symbol is either a bare class name (for imported workflows)
    or a dotted module path like ``workspace.workspace_1.workflows.foo.MyClass``.
    """
    from src.worker.worker import WORKSPACE_ROOT

    # For imported workflows, search workspace directories
    if not WORKSPACE_ROOT.exists():
        return None

    # Search all workflow files for the class definition
    for workspace_dir in WORKSPACE_ROOT.glob("workspace_*"):
        from src.worker.worker import _collect_search_dirs

        for search_dir in _collect_search_dirs(workspace_dir, "workflows"):
            if not search_dir.exists():
                continue

            for py_file in search_dir.glob("*.py"):
                if py_file.name == "__init__.py":
                    continue

                try:
                    source = py_file.read_text()
                    # Check if this file contains the workflow class
                    if entrypoint_symbol in source:
                        return source
                except Exception:
                    continue

    return None
