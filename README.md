# Behavior Tree Editor

A visual behavior tree editor with Python backend and web-based canvas editor. Build, test, and execute behavior trees for robotics, game AI, and autonomous systems.

## Features

- **Visual Editor** — Drag-and-drop canvas to design behavior trees
- **Python Library** — Core BT implementation with Sequence, Selector, Parallel, Decorators
- **Multiple Formats** — XML, JSON, YAML parsing and serialization
- **REST API** — FastAPI backend for programmatic execution
- **CLI Runner** — Execute trees from command line with verbose output
- **Web Visualizer** — Real-time tick animation in browser
- **75 Tests** — Comprehensive test coverage (86%)

## Quick Start

```bash
# Clone and setup
git clone <repo>
cd bt-editor
python3 -m venv venv
source venv/bin/activate
pip install -e .[api]

# Run CLI examples
python -m bt_lib.runner examples/simple.xml --verbose
python -m bt_lib.runner examples/patrol.xml --blackboard BatteryLow=true

# Start web editor
uvicorn visualizer.app:app --port 8000
# Open http://localhost:8000
```

## Project Structure

```
bt-editor/
├── bt_lib/                 # Core behavior tree library
│   ├── nodes.py           # Node types (Sequence, Selector, Action, Condition, Decorators)
│   ├── blackboard.py      # Hierarchical shared state
│   ├── tree.py            # BehaviorTree container
│   ├── parser.py          # XML/JSON/YAML parser
│   ├── runner.py          # CLI runner
│   └── tests/             # 75 unit/integration tests
├── examples/              # Example behavior trees
│   ├── simple.xml         # Basic sequence
│   ├── patrol.xml         # Robot patrol (Selector priority)
│   └── pickup.xml         # Pick & place with Repeater
├── visualizer/            # Web editor
│   ├── app.py             # FastAPI app
│   ├── api.py             # REST endpoints
│   └── static/            # HTML/CSS/JS editor
├── .github/workflows/ci.yml
├── pyproject.toml
└── requirements.txt
```

## Node Types

### Composites
| Node | Behavior |
|------|----------|
| **Sequence** | Run children in order; stop on first FAILURE |
| **Selector** | Try children in order; stop on first SUCCESS |
| **Parallel** | Run all children; configurable success/failure thresholds |

### Decorators
| Node | Behavior |
|------|----------|
| **Inverter** | Flip SUCCESS ↔ FAILURE |
| **Repeater** | Repeat child N times (or infinite) |
| **UntilSuccess** | Repeat until child returns SUCCESS |
| **Timeout** | Fail if child exceeds max ticks |

### Leaves
| Node | Behavior |
|------|----------|
| **Action** | Perform task; returns SUCCESS/FAILURE/RUNNING |
| **Condition** | Check condition; returns SUCCESS/FAILURE |

## Usage

### Python API

```python
from bt_lib import Sequence, Selector, Action, Condition, BehaviorTree, Blackboard

# Build tree programmatically
tree = BehaviorTree(
    Selector("Root", children=[
        Sequence("LowBattery", children=[
            Condition("BatteryLow", lambda bb: bb.get("battery", 100) < 20),
            Action("GoHome", lambda bb: print("Going home!") or True),
        ]),
        Action("Patrol", lambda bb: print("Patrolling...") or True),
    ])
)

# Run with blackboard
bb = Blackboard()
bb.set("battery", 15)
tree.tick(max_ticks=10)  # Executes GoHome
```

### From XML

```python
from bt_lib import parse_xml_file, BehaviorTree

root = parse_xml_file("examples/patrol.xml")
tree = BehaviorTree(root)
tree.set_blackboard("BatteryLow", True)
tree.tick(max_ticks=10)
```

### CLI

```bash
# Run with verbose output
python -m bt_lib.runner examples/simple.xml --verbose

# Pass initial blackboard values
python -m bt_lib.runner examples/patrol.xml --blackboard BatteryLow=true --blackboard DirtDetected=false

# Show tree structure
python -m bt_lib.runner examples/pickup.xml --show-tree
```

### REST API

```bash
# Start server
uvicorn visualizer.app:app --port 8000

# Execute tree
curl -X POST http://localhost:8000/api/run-tree \
  -H "Content-Type: application/json" \
  -d '{"xml": "<Sequence><Action name=\"A1\"/></Sequence>"}'

# List examples
curl http://localhost:8000/api/examples

# Get tree structure for visualization
curl http://localhost:8000/api/tree-structure/simple.xml
```

## Web Editor

Open `http://localhost:8000` after starting the server:

- **Left Panel** — Palette (Composites, Decorators, Leaves)
- **Center** — Canvas (drag nodes, click ports to connect)
- **Right Panel** — Properties (edit name, type-specific params)
- **Bottom** — Execution History (tick-by-tick animation)
- **Toolbar** — Load/Save/Export, Run/Step/Stop/Reset

### Keyboard Shortcuts
| Key | Action |
|-----|--------|
| `R` | Run tree |
| `Space` | Step one tick |
| `Esc` | Stop |
| `Backspace` | Reset |
| `+/-` | Zoom in/out |
| `0` | Reset zoom |
| `C` | Center view |
| `G` | Toggle grid |
| `Del` | Delete selected node |
| `Ctrl+S` | Save |
| `Ctrl+E` | Export XML |
| `Ctrl+L` | Load example |

## Examples

### Simple Sequence
```xml
<Sequence name="SimpleSequence">
    <Action name="Action1" />
    <Action name="Action2" />
    <Action name="Action3" />
</Sequence>
```

### Robot Patrol (Priority-based Selector)
```xml
<Selector name="RobotPatrol">
    <Sequence name="LowBattery">
        <Condition name="BatteryLow" />
        <Action name="GoHomeAndCharge" />
    </Sequence>
    <Sequence name="DirtDetected">
        <Condition name="DirtDetected" />
        <Action name="CleanSpot" />
    </Sequence>
    <Sequence name="PatrolRooms">
        <Action name="MoveToNextRoom" />
        <Action name="ScanRoom" />
        <Condition name="RoomClear" />
    </Sequence>
</Selector>
```

### Pick & Place with Retry
```xml
<Sequence name="PickAndPlace">
    <Selector name="FindObject">
        <Sequence name="ObjectInGripper">
            <Condition name="HasObject" />
            <Action name="SkipToPlace" />
        </Sequence>
        <Sequence name="LocateAndGrasp">
            <Action name="ScanForObject" />
            <Condition name="ObjectFound" />
            <Action name="MoveToObject" />
            <Action name="GraspObject" />
        </Sequence>
    </Selector>
    <Repeater name="RetryPlace" count="3">
        <Sequence name="PlaceAttempt">
            <Action name="AlignGripper" />
            <Action name="ReleaseObject" />
            <Condition name="ObjectReleased" />
        </Sequence>
    </Repeater>
</Sequence>
```

## Testing

```bash
# Run all tests
pytest bt_lib/tests/ -v

# With coverage
pytest bt_lib/tests/ --cov=bt_lib --cov-report=term-missing

# Run specific test file
pytest bt_lib/tests/test_nodes.py -v
```

## CI/CD

GitHub Actions workflow (`.github/workflows/ci.yml`):
- Tests on Python 3.10, 3.11, 3.12
- Ruff linting + formatting
- Mypy type checking
- Build verification
- Coverage reporting

## Requirements

- Python 3.10+
- Dependencies: `pyyaml` (core), `fastapi`, `uvicorn`, `pydantic` (API)

## License

MIT License - see [LICENSE](LICENSE)