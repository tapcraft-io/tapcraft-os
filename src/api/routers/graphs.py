"""API routes for Graphs."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_db
from src.models.schemas import (
    GraphResponse,
    GraphUpdate,
    NodeCreate,
    NodeUpdate,
    NodeResponse,
    EdgeCreate,
    EdgeResponse,
)
from src.services import crud

router = APIRouter(prefix="/graphs", tags=["graphs"])


@router.get("/{graph_id}", response_model=GraphResponse)
async def get_graph(
    graph_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a graph by ID."""
    graph = await crud.get_graph(db=db, graph_id=graph_id, load_nodes_edges=True)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    return graph


@router.patch("/{graph_id}", response_model=GraphResponse)
async def update_graph(
    graph_id: int,
    graph_data: GraphUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a graph."""
    graph = await crud.update_graph(
        db=db,
        graph_id=graph_id,
        entry_node_id=graph_data.entry_node_id,
        layout_metadata=graph_data.layout_metadata,
    )
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    return await crud.get_graph(db=db, graph_id=graph_id, load_nodes_edges=True)


@router.post("/{graph_id}/nodes", response_model=NodeResponse, status_code=201)
async def create_node(
    graph_id: int,
    node_data: NodeCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new node in a graph."""
    node = await crud.create_node(
        db=db,
        graph_id=graph_id,
        kind=node_data.kind,
        label=node_data.label,
        config=node_data.config,
        config_schema=node_data.config_schema,
        ui_position=node_data.ui_position,
        activity_operation_id=node_data.activity_operation_id,
        primitive_type=node_data.primitive_type,
    )
    return node


@router.patch("/nodes/{node_id}", response_model=NodeResponse)
async def update_node(
    node_id: int,
    node_data: NodeUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a node."""
    node = await crud.update_node(
        db=db,
        node_id=node_id,
        label=node_data.label,
        config=node_data.config,
        ui_position=node_data.ui_position,
    )
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@router.delete("/nodes/{node_id}", status_code=204)
async def delete_node(
    node_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a node."""
    success = await crud.delete_node(db=db, node_id=node_id)
    if not success:
        raise HTTPException(status_code=404, detail="Node not found")


@router.post("/{graph_id}/edges", response_model=EdgeResponse, status_code=201)
async def create_edge(
    graph_id: int,
    edge_data: EdgeCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new edge in a graph."""
    edge = await crud.create_edge(
        db=db,
        graph_id=graph_id,
        from_node_id=edge_data.from_node_id,
        to_node_id=edge_data.to_node_id,
        path=edge_data.path,
        label=edge_data.label,
    )
    return edge


@router.delete("/edges/{edge_id}", status_code=204)
async def delete_edge(
    edge_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete an edge."""
    success = await crud.delete_edge(db=db, edge_id=edge_id)
    if not success:
        raise HTTPException(status_code=404, detail="Edge not found")
