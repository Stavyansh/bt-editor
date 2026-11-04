"""
FastAPI routes for Behavior Tree Editor.
"""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from bt_lib.nodes import NodeStatus
from bt_lib.parser import node_to_dict, parse_auto, parse_xml
from bt_lib.tree import BehaviorTree

router = APIRouter()

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


class RunTreeRequest(BaseModel):
    xml: str
    max_ticks: int = 1000
    initial_blackboard: dict[str, Any] | None = None


class RunTreeResponse(BaseModel):
    final_status: str
    ticks: int
    history: list[dict[str, Any]]


class ExampleInfo(BaseModel):
    name: str
    filename: str
    description: str


@router.get("/examples", response_model=list[ExampleInfo])
async def list_examples():
    """List available example trees."""
    examples = []
    for file in EXAMPLES_DIR.glob("*.xml"):
        # Parse to get root name
        try:
            root = parse_auto(file)
            examples.append(ExampleInfo(
                name=root.name,
                filename=file.name,
                description=f"Behavior tree: {root.name}"
            ))
        except Exception:
            examples.append(ExampleInfo(
                name=file.stem,
                filename=file.name,
                description="Behavior tree example"
            ))
    return examples


@router.get("/examples/{filename}")
async def get_example(filename: str):
    """Get example tree XML content."""
    file = EXAMPLES_DIR / filename
    if not file.exists():
        raise HTTPException(status_code=404, detail="Example not found")

    content = file.read_text()
    return {"filename": filename, "xml": content}


@router.post("/run-tree", response_model=RunTreeResponse)
async def run_tree(request: RunTreeRequest):
    """Execute a behavior tree from XML string."""
    try:
        root = parse_xml(request.xml)
        tree = BehaviorTree(root, name="api_tree")

        if request.initial_blackboard:
            for key, value in request.initial_blackboard.items():
                tree.set_blackboard(key, value)

        history = []
        final_status = None

        for tick_num in range(1, request.max_ticks + 1):
            status = tree.tick_once()
            final_status = status

            history.append({
                "tick": tick_num,
                "status": status.value,
                "blackboard": tree.blackboard.to_dict()
            })

            if status != NodeStatus.RUNNING:
                break

        return RunTreeResponse(
            final_status=final_status.value if final_status else NodeStatus.RUNNING.value,
            ticks=len(history),
            history=history
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/run-tree-file/{filename}")
async def run_tree_file(filename: str, request: Request):
    """Execute a behavior tree from example file with optional blackboard."""
    file = EXAMPLES_DIR / filename
    if not file.exists():
        raise HTTPException(status_code=404, detail="Example not found")

    try:
        body = await request.json()
        max_ticks = body.get("max_ticks", 1000)
        initial_blackboard = body.get("initial_blackboard", None)

        root = parse_auto(file)
        tree = BehaviorTree(root, name=file.stem)

        if initial_blackboard:
            for key, value in initial_blackboard.items():
                tree.set_blackboard(key, value)

        history = []
        final_status = None

        for tick_num in range(1, max_ticks + 1):
            status = tree.tick_once()
            final_status = status

            history.append({
                "tick": tick_num,
                "status": status.value,
                "blackboard": tree.blackboard.to_dict()
            })

            if status != NodeStatus.RUNNING:
                break

        return {
            "filename": filename,
            "tree_name": tree.name,
            "final_status": final_status.value if final_status else NodeStatus.RUNNING.value,
            "ticks": len(history),
            "history": history
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tree-structure/{filename}")
async def get_tree_structure(filename: str):
    """Get tree structure as nested dict for visualization."""
    file = EXAMPLES_DIR / filename
    if not file.exists():
        raise HTTPException(status_code=404, detail="Example not found")

    try:
        root = parse_auto(file)
        return node_to_dict(root)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "behavior-tree-editor"}
