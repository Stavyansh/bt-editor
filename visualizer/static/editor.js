/**
 * Behavior Tree Editor - Main Application
 * Canvas-based visual editor for behavior trees
 */

// ============================================
// STATE MANAGEMENT
// ============================================

const State = {
    nodes: new Map(),           // id -> node data
    connections: [],            // [{from: {nodeId, port}, to: {nodeId, port}}]
    selectedNodeId: null,
    draggedNodeType: null,
    connectionPreview: null,    // {fromNode, fromPort, toX, toY}
    pan: { x: 0, y: 0 },
    zoom: 1,
    history: [],                // execution history
    isRunning: false,
    currentTick: 0,
    animationFrame: null,
    examples: [],
    nextNodeId: 1,
};

const NODE_TYPES = {
    composites: [
        { type: 'Sequence', icon: '↘', desc: 'Run children in order, stop on failure' },
        { type: 'Selector', icon: '↗', desc: 'Try children in order, stop on success' },
        { type: 'Parallel', icon: '⇉', desc: 'Run all children simultaneously' },
    ],
    decorators: [
        { type: 'Inverter', icon: '↔', desc: 'Invert child result (S↔F)' },
        { type: 'Repeater', icon: '↻', desc: 'Repeat child N times' },
        { type: 'UntilSuccess', icon: '↺', desc: 'Repeat until child succeeds' },
        { type: 'Timeout', icon: '⏱', desc: 'Fail if child exceeds max ticks' },
    ],
    leaves: [
        { type: 'Action', icon: '▶', desc: 'Perform a task (returns S/F/R)' },
        { type: 'Condition', icon: '?', desc: 'Check a condition (returns S/F)' },
    ],
};

const NODE_DEFAULTS = {
    Sequence: { name: 'Sequence', properties: {} },
    Selector: { name: 'Selector', properties: {} },
    Parallel: { name: 'Parallel', properties: { success_threshold: 1, failure_threshold: 1 } },
    Inverter: { name: 'Inverter', properties: {} },
    Repeater: { name: 'Repeater', properties: { count: 3 } },
    UntilSuccess: { name: 'UntilSuccess', properties: {} },
    Timeout: { name: 'Timeout', properties: { max_ticks: 100 } },
    Action: { name: 'Action', properties: {} },
    Condition: { name: 'Condition', properties: {} },
};

// ============================================
// DOM ELEMENTS
// ============================================

const els = {
    canvas: document.getElementById('canvas'),
    ctx: null,
    wrapper: document.getElementById('canvas-wrapper'),
    previewSvg: document.getElementById('connection-preview'),
    paletteCategories: document.getElementById('palette-categories'),
    paletteSearch: document.getElementById('palette-search'),
    propertiesContent: document.getElementById('properties-content'),
    historyContent: document.getElementById('history-content'),
    exampleSelect: document.getElementById('example-select'),
    exampleList: document.getElementById('example-list'),
    zoomLevel: document.getElementById('zoom-level'),
    nodeCount: document.getElementById('node-count'),
    tickInfo: document.getElementById('tick-info'),
    currentTick: document.getElementById('current-tick'),
    statusBadge: document.getElementById('status-badge'),
    loadModal: document.getElementById('load-modal'),
    saveModal: document.getElementById('save-modal'),
    modalOverlay: document.getElementById('modal-overlay'),
    saveFilename: document.getElementById('save-filename'),
};

els.ctx = els.canvas.getContext('2d');

// ============================================
// INITIALIZATION
// ============================================

function init() {
    setupCanvas();
    buildPalette();
    loadExamples();
    setupEventListeners();
    setupCanvasEvents();
    resizeCanvas();
    render();
    updateNodeCount();
}

function setupCanvas() {
    els.canvas.width = els.wrapper.clientWidth;
    els.canvas.height = els.wrapper.clientHeight;
    els.previewSvg.style.width = '100%';
    els.previewSvg.style.height = '100%';
    els.previewSvg.setAttribute('viewBox', `0 0 ${els.canvas.width} ${els.canvas.height}`);
}

function resizeCanvas() {
    const rect = els.wrapper.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;

    els.canvas.width = rect.width * dpr;
    els.canvas.height = rect.height * dpr;
    els.canvas.style.width = rect.width + 'px';
    els.canvas.style.height = rect.height + 'px';

    els.ctx.scale(dpr, dpr);

    els.previewSvg.setAttribute('viewBox', `0 0 ${rect.width} ${rect.height}`);
    els.previewSvg.style.width = rect.width + 'px';
    els.previewSvg.style.height = rect.height + 'px';

    render();
}

window.addEventListener('resize', resizeCanvas);

// ============================================
// PALETTE
// ============================================

function buildPalette() {
    els.paletteCategories.innerHTML = '';

    for (const [category, types] of Object.entries(NODE_TYPES)) {
        const catDiv = document.createElement('div');
        catDiv.className = 'palette-category';
        catDiv.innerHTML = `<div class="palette-category-title">${category}</div>`;

        const nodesDiv = document.createElement('div');
        for (const nodeType of types) {
            const nodeEl = document.createElement('div');
            nodeEl.className = 'palette-node';
            nodeEl.draggable = true;
            nodeEl.dataset.type = nodeType.type;
            nodeEl.title = nodeType.desc;
            nodeEl.innerHTML = `
                <span class="palette-node-icon">${nodeType.icon}</span>
                <span>${nodeType.type}</span>
                <span class="palette-node-type">${category.slice(0, -1)}</span>
            `;
            nodesDiv.appendChild(nodeEl);
        }
        catDiv.appendChild(nodesDiv);
        els.paletteCategories.appendChild(catDiv);
    }

    // Palette drag events
    els.paletteCategories.addEventListener('dragstart', (e) => {
        const nodeEl = e.target.closest('.palette-node');
        if (!nodeEl) return;
        State.draggedNodeType = nodeEl.dataset.type;
        nodeEl.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'copy';
        e.dataTransfer.setData('text/plain', nodeEl.dataset.type);
    });

    els.paletteCategories.addEventListener('dragend', (e) => {
        const nodeEl = e.target.closest('.palette-node');
        if (nodeEl) nodeEl.classList.remove('dragging');
        State.draggedNodeType = null;
    });

    // Search filter
    els.paletteSearch.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        document.querySelectorAll('.palette-node').forEach(el => {
            const type = el.dataset.type.toLowerCase();
            el.style.display = type.includes(query) ? 'flex' : 'none';
        });
        document.querySelectorAll('.palette-category').forEach(cat => {
            const visible = cat.querySelector('.palette-node:not([style*="none"])');
            cat.style.display = visible ? 'block' : 'none';
        });
    });
}

// ============================================
// EXAMPLES
// ============================================

async function loadExamples() {
    try {
        const res = await fetch('/api/examples');
        State.examples = await res.json();

        // Populate dropdown
        els.exampleSelect.innerHTML = '<option value="">-- Examples --</option>';
        State.examples.forEach(ex => {
            const opt = document.createElement('option');
            opt.value = ex.filename;
            opt.textContent = ex.name;
            els.exampleSelect.appendChild(opt);
        });

        // Populate modal
        els.exampleList.innerHTML = '';
        State.examples.forEach(ex => {
            const item = document.createElement('div');
            item.className = 'example-item';
            item.dataset.filename = ex.filename;
            item.innerHTML = `
                <div class="example-item-info">
                    <div class="example-item-name">${ex.name}</div>
                    <div class="example-item-desc">${ex.filename}</div>
                </div>
            `;
            item.addEventListener('click', () => selectExample(item, ex.filename));
            els.exampleList.appendChild(item);
        });
    } catch (err) {
        console.error('Failed to load examples:', err);
    }
}

function selectExample(item, filename) {
    document.querySelectorAll('.example-item').forEach(el => el.classList.remove('selected'));
    item.classList.add('selected');
    State.selectedExampleFile = filename;
}

async function loadExample(filename) {
    try {
        const res = await fetch(`/api/tree-structure/${filename}`);
        const treeData = await res.json();
        clearCanvas();
        deserializeTree(treeData);
        centerView();
        closeModal();
    } catch (err) {
        console.error('Failed to load example:', err);
        alert('Failed to load example: ' + err.message);
    }
}

// ============================================
// NODE CREATION & MANAGEMENT
// ============================================

function createNode(type, x, y) {
    const defaults = NODE_DEFAULTS[type] || { name: type, properties: {} };
    const id = `node_${State.nextNodeId++}`;

    const node = {
        id,
        type,
        name: defaults.name,
        properties: { ...defaults.properties },
        x,
        y,
        width: 160,
        height: 60,
        status: 'idle', // idle, running, success, failure
        ports: {
            input: { x: 0, y: 30, connected: false },
            output: { x: 160, y: 30, connected: false },
        },
    };

    // Adjust ports for decorators (single child)
    if (['Inverter', 'Repeater', 'UntilSuccess', 'Timeout'].includes(type)) {
        node.ports.input = { x: 0, y: 30, connected: false };
        node.ports.output = { x: 160, y: 30, connected: false };
    }

    State.nodes.set(id, node);
    return node;
}

function deleteNode(nodeId) {
    // Remove connections
    State.connections = State.connections.filter(c =>
        c.from.nodeId !== nodeId && c.to.nodeId !== nodeId
    );
    State.nodes.delete(nodeId);
    if (State.selectedNodeId === nodeId) {
        State.selectedNodeId = null;
        showEmptyProperties();
    }
    render();
    updateNodeCount();
}

function clearCanvas() {
    State.nodes.clear();
    State.connections = [];
    State.selectedNodeId = null;
    State.nextNodeId = 1;
    showEmptyProperties();
    render();
    updateNodeCount();
}

// ============================================
// CANVAS RENDERING
// ============================================

function render() {
    const ctx = els.ctx;
    const width = els.canvas.width / (window.devicePixelRatio || 1);
    const height = els.canvas.height / (window.devicePixelRatio || 1);

    // Clear
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, width, height);
    ctx.restore();

    // Apply transform
    ctx.save();
    ctx.translate(State.pan.x, State.pan.y);
    ctx.scale(State.zoom, State.zoom);

    // Draw grid
    drawGrid(ctx, width, height);

    // Draw connections
    drawConnections(ctx);

    // Draw nodes
    drawNodes(ctx);

    // Draw connection preview
    if (State.connectionPreview) {
        drawConnectionPreview(ctx);
    }

    ctx.restore();
}

function drawGrid(ctx, width, height) {
    if (!document.getElementById('btn-grid').classList.contains('active')) return;

    const gridSize = 20;
    const startX = -State.pan.x / State.zoom;
    const startY = -State.pan.y / State.zoom;
    const endX = startX + width / State.zoom;
    const endY = startY + height / State.zoom;

    ctx.strokeStyle = '#2a2a3a';
    ctx.lineWidth = 0.5 / State.zoom;
    ctx.beginPath();

    for (let x = Math.floor(startX / gridSize) * gridSize; x <= endX; x += gridSize) {
        ctx.moveTo(x, startY);
        ctx.lineTo(x, endY);
    }
    for (let y = Math.floor(startY / gridSize) * gridSize; y <= endY; y += gridSize) {
        ctx.moveTo(startX, y);
        ctx.lineTo(endX, y);
    }
    ctx.stroke();
}

function drawNodes(ctx) {
    const nodeOrder = Array.from(State.nodes.values()).sort((a, b) => a.y - b.y);

    for (const node of nodeOrder) {
        drawNode(ctx, node);
    }
}

function drawNode(ctx, node) {
    const { x, y, width, height, type, name, status, selected } = node;
    const isSelected = State.selectedNodeId === node.id;
    const radius = 8;

    // Shadow for selected
    if (isSelected) {
        ctx.shadowColor = '#89b4fa';
        ctx.shadowBlur = 15 / State.zoom;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 0;
    }

    // Node background
    let fillColor = '#313244';
    let strokeColor = '#45475a';
    let lineWidth = 2 / State.zoom;

    if (status === 'running') {
        strokeColor = '#f9e2af';
        lineWidth = 3 / State.zoom;
    } else if (status === 'success') {
        strokeColor = '#a6e3a1';
        lineWidth = 3 / State.zoom;
    } else if (status === 'failure') {
        strokeColor = '#f38ba8';
        lineWidth = 3 / State.zoom;
    } else if (isSelected) {
        strokeColor = '#89b4fa';
        lineWidth = 3 / State.zoom;
    }

    // Rounded rect
    ctx.beginPath();
    ctx.roundRect(x, y, width, height, radius);
    ctx.fillStyle = fillColor;
    ctx.fill();
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = lineWidth;
    ctx.stroke();

    ctx.shadowColor = 'transparent';
    ctx.shadowBlur = 0;

    // Type indicator bar at top
    const typeColors = {
        Sequence: '#89b4fa', Selector: '#74a0e8', Parallel: '#b4befe',
        Inverter: '#fab387', Repeater: '#fab387', UntilSuccess: '#fab387', Timeout: '#fab387',
        Action: '#a6e3a1', Condition: '#f9e2af',
    };
    const typeColor = typeColors[type] || '#89b4fa';

    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + width - radius, y);
    ctx.arcTo(x + width, y, x + width, y + radius, radius);
    ctx.lineTo(x + width, y + 6);
    ctx.lineTo(x, y + 6);
    ctx.lineTo(x, y + radius);
    ctx.arcTo(x, y, x + radius, y, radius);
    ctx.closePath();
    ctx.fillStyle = typeColor + '33';
    ctx.fill();

    // Type icon
    const icons = {
        Sequence: '↘', Selector: '↗', Parallel: '⇉',
        Inverter: '↔', Repeater: '↻', UntilSuccess: '↺', Timeout: '⏱',
        Action: '▶', Condition: '?',
    };
    ctx.font = '14px sans-serif';
    ctx.fillStyle = typeColor;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(icons[type] || '●', x + 18, y + 15);

    // Node name
    ctx.font = 'bold 12px monospace';
    ctx.fillStyle = '#cdd6f4';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    const maxNameWidth = width - 50;
    let displayName = name;
    while (ctx.measureText(displayName).width > maxNameWidth && displayName.length > 3) {
        displayName = displayName.slice(0, -1) + '…';
    }
    ctx.fillText(displayName, x + 36, y + height / 2);

    // Ports
    drawPort(ctx, node, 'input');
    drawPort(ctx, node, 'output');

    // Selection handles
    if (isSelected) {
        drawSelectionHandles(ctx, node);
    }
}

function drawPort(ctx, node, portName) {
    const port = node.ports[portName];
    const isInput = portName === 'input';
    const x = node.x + (isInput ? 0 : node.width);
    const y = node.y + port.y;

    ctx.beginPath();
    ctx.arc(x, y, 8 / State.zoom, 0, Math.PI * 2);
    ctx.fillStyle = port.connected ? '#89b4fa' : '#45475a';
    ctx.fill();
    ctx.strokeStyle = '#1e1e2e';
    ctx.lineWidth = 2 / State.zoom;
    ctx.stroke();

    // Port label
    ctx.font = '9px monospace';
    ctx.fillStyle = '#6c7086';
    ctx.textAlign = isInput ? 'right' : 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText(isInput ? 'in' : 'out', x + (isInput ? -14 : 14), y);
}

function drawSelectionHandles(ctx, node) {
    const handleSize = 8 / State.zoom;
    const { x, y, width, height } = node;

    ctx.fillStyle = '#89b4fa';
    ctx.strokeStyle = '#1e1e2e';
    ctx.lineWidth = 1 / State.zoom;

    // 8 handles
    const handles = [
        { x: x, y: y },                           // top-left
        { x: x + width / 2, y: y },               // top-mid
        { x: x + width, y: y },                   // top-right
        { x: x + width, y: y + height / 2 },      // mid-right
        { x: x + width, y: y + height },          // bottom-right
        { x: x + width / 2, y: y + height },      // bottom-mid
        { x: x, y: y + height },                  // bottom-left
        { x: x, y: y + height / 2 },              // mid-left
    ];

    for (const h of handles) {
        ctx.beginPath();
        ctx.rect(h.x - handleSize / 2, h.y - handleSize / 2, handleSize, handleSize);
        ctx.fill();
        ctx.stroke();
    }
}

function drawConnections(ctx) {
    for (const conn of State.connections) {
        const fromNode = State.nodes.get(conn.from.nodeId);
        const toNode = State.nodes.get(conn.to.nodeId);
        if (!fromNode || !toNode) continue;

        const fromX = fromNode.x + fromNode.ports.output.x - fromNode.x;
        const fromY = fromNode.y + fromNode.ports.output.y - fromNode.y;
        const toX = toNode.x + toNode.ports.input.x - toNode.x;
        const toY = toNode.y + toNode.ports.input.y - toNode.y;

        drawBezierCurve(ctx, fromX, fromY, toX, toY, conn.active);
    }
}

function drawBezierCurve(ctx, x1, y1, x2, y2, active = false) {
    const cpOffset = Math.max(50, Math.abs(x2 - x1) * 0.5);
    const cpx1 = x1 + cpOffset;
    const cpy1 = y1;
    const cpx2 = x2 - cpOffset;
    const cpy2 = y2;

    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.bezierCurveTo(cpx1, cpy1, cpx2, cpy2, x2, y2);

    ctx.strokeStyle = active ? '#89b4fa' : '#45475a';
    ctx.lineWidth = active ? 3 / State.zoom : 2 / State.zoom;
    ctx.stroke();

    // Arrow head
    const angle = Math.atan2(y2 - cpy2, x2 - cpx2);
    const arrowSize = 10 / State.zoom;
    ctx.beginPath();
    ctx.moveTo(x2, y2);
    ctx.lineTo(
        x2 - arrowSize * Math.cos(angle - Math.PI / 6),
        y2 - arrowSize * Math.sin(angle - Math.PI / 6)
    );
    ctx.lineTo(
        x2 - arrowSize * Math.cos(angle + Math.PI / 6),
        y2 - arrowSize * Math.sin(angle + Math.PI / 6)
    );
    ctx.closePath();
    ctx.fillStyle = active ? '#89b4fa' : '#45475a';
    ctx.fill();
}

function drawConnectionPreview(ctx) {
    const { fromNode, fromPort, toX, toY } = State.connectionPreview;
    const fromX = fromNode.x + fromNode.ports[fromPort].x;
    const fromY = fromNode.y + fromNode.ports[fromPort].y;

    drawBezierCurve(ctx, fromX, fromY, toX, toY, false);
}

// ============================================
// CANVAS INTERACTION
// ============================================

function setupCanvasEvents() {
    const canvas = els.canvas;
    let isPanning = false;
    let panStart = { x: 0, y: 0 };
    let isDraggingNode = false;
    let dragStart = { x: 0, y: 0 };
    let dragNodeId = null;
    let isConnecting = false;
    let connectStart = { nodeId: null, port: null };

    // Mouse down
    canvas.addEventListener('mousedown', (e) => {
        const pos = getCanvasPos(e);
        const nodeId = getNodeAt(pos.x, pos.y);
        const port = getPortAt(nodeId, pos.x, pos.y);

        if (e.button === 1 || (e.button === 0 && e.altKey)) {
            // Middle click or Alt+click = pan
            isPanning = true;
            panStart = { x: e.clientX - State.pan.x, y: e.clientY - State.pan.y };
            canvas.style.cursor = 'grabbing';
            return;
        }

        if (port && e.button === 0) {
            // Start connection
            isConnecting = true;
            connectStart = { nodeId, port };
            State.connectionPreview = {
                fromNode: State.nodes.get(nodeId),
                fromPort: port,
                toX: pos.x,
                toY: pos.y,
            };
            els.previewSvg.classList.remove('hidden');
            canvas.style.cursor = 'crosshair';
            return;
        }

        if (nodeId && e.button === 0) {
            // Select/drag node
            selectNode(nodeId);
            if (!isNodeOnPort(nodeId, pos.x, pos.y)) {
                isDraggingNode = true;
                dragNodeId = nodeId;
                dragStart = { x: pos.x - State.nodes.get(nodeId).x, y: pos.y - State.nodes.get(nodeId).y };
                canvas.style.cursor = 'grabbing';
            }
            return;
        }

        // Click empty space = deselect
        if (e.button === 0) {
            selectNode(null);
        }
    });

    // Mouse move
    canvas.addEventListener('mousemove', (e) => {
        const pos = getCanvasPos(e);

        if (isPanning) {
            State.pan.x = e.clientX - panStart.x;
            State.pan.y = e.clientY - panStart.y;
            render();
            return;
        }

        if (isDraggingNode && dragNodeId) {
            const node = State.nodes.get(dragNodeId);
            if (node) {
                node.x = pos.x - dragStart.x;
                node.y = pos.y - dragStart.y;
                render();
            }
            return;
        }

        if (isConnecting) {
            State.connectionPreview.toX = pos.x;
            State.connectionPreview.toY = pos.y;
            render();
            return;
        }

        // Hover effects
        const nodeId = getNodeAt(pos.x, pos.y);
        const port = nodeId ? getPortAt(nodeId, pos.x, pos.y) : null;
        canvas.style.cursor = port ? 'crosshair' : (nodeId ? 'grab' : 'default');
    });

    // Mouse up
    window.addEventListener('mouseup', (e) => {
        if (isPanning) {
            isPanning = false;
            canvas.style.cursor = 'default';
            return;
        }

        if (isDraggingNode) {
            isDraggingNode = false;
            dragNodeId = null;
            canvas.style.cursor = 'default';
            return;
        }

        if (isConnecting) {
            const pos = getCanvasPos(e);
            const targetNodeId = getNodeAt(pos.x, pos.y);
            const targetPort = targetNodeId ? getPortAt(targetNodeId, pos.x, pos.y) : null;

            if (targetNodeId && targetPort && targetNodeId !== connectStart.nodeId) {
                // Validate connection (output -> input)
                const fromIsOutput = connectStart.port === 'output';
                const toIsInput = targetPort === 'input';

                if (fromIsOutput && toIsInput) {
                    // Check for existing connection on target port
                    const existing = State.connections.find(c =>
                        c.to.nodeId === targetNodeId && c.to.port === 'input'
                    );
                    if (!existing) {
                        addConnection(connectStart.nodeId, 'output', targetNodeId, 'input');
                    }
                }
            }

            isConnecting = false;
            State.connectionPreview = null;
            els.previewSvg.classList.add('hidden');
            canvas.style.cursor = 'default';
            render();
            return;
        }
    });

    // Wheel zoom
    canvas.addEventListener('wheel', (e) => {
        e.preventDefault();
        const pos = getCanvasPos(e);
        const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
        const newZoom = Math.max(0.1, Math.min(3, State.zoom * zoomFactor));

        // Zoom towards mouse position
        State.pan.x = pos.x - (pos.x - State.pan.x) * (newZoom / State.zoom);
        State.pan.y = pos.y - (pos.y - State.pan.y) * (newZoom / State.zoom);
        State.zoom = newZoom;

        updateZoomDisplay();
        render();
    }, { passive: false });

    // Double click to edit name
    canvas.addEventListener('dblclick', (e) => {
        const pos = getCanvasPos(e);
        const nodeId = getNodeAt(pos.x, pos.y);
        if (nodeId) {
            selectNode(nodeId);
            editNodeName(nodeId);
        }
    });

    // Context menu
    canvas.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        const pos = getCanvasPos(e);
        const nodeId = getNodeAt(pos.x, pos.y);
        if (nodeId) {
            selectNode(nodeId);
            showContextMenu(e.clientX, e.clientY, nodeId);
        }
    });
}

function getCanvasPos(e) {
    const rect = els.canvas.getBoundingClientRect();
    return {
        x: (e.clientX - rect.left - State.pan.x) / State.zoom,
        y: (e.clientY - rect.top - State.pan.y) / State.zoom,
    };
}

function getNodeAt(x, y) {
    for (const node of State.nodes.values()) {
        if (x >= node.x && x <= node.x + node.width &&
            y >= node.y && y <= node.y + node.height) {
            return node.id;
        }
    }
    return null;
}

function getPortAt(nodeId, x, y) {
    const node = State.nodes.get(nodeId);
    if (!node) return null;

    for (const [portName, port] of Object.entries(node.ports)) {
        const px = node.x + port.x;
        const py = node.y + port.y;
        const dist = Math.hypot(x - px, y - py);
        if (dist < 12 / State.zoom) return portName;
    }
    return null;
}

function isNodeOnPort(nodeId, x, y) {
    return getPortAt(nodeId, x, y) !== null;
}

function selectNode(nodeId) {
    State.selectedNodeId = nodeId;
    showProperties(nodeId);
    render();
}

function addConnection(fromNodeId, fromPort, toNodeId, toPort) {
    // Check if connection already exists
    const exists = State.connections.some(c =>
        c.from.nodeId === fromNodeId && c.from.port === fromPort &&
        c.to.nodeId === toNodeId && c.to.port === toPort
    );
    if (exists) return;

    State.connections.push({
        from: { nodeId: fromNodeId, port: fromPort },
        to: { nodeId: toNodeId, port: toPort },
        active: false,
    });

    // Update port connected status
    const fromNode = State.nodes.get(fromNodeId);
    const toNode = State.nodes.get(toNodeId);
    if (fromNode) fromNode.ports[fromPort].connected = true;
    if (toNode) toNode.ports[toPort].connected = true;

    render();
}

function removeConnection(connIndex) {
    const conn = State.connections[connIndex];
    const fromNode = State.nodes.get(conn.from.nodeId);
    const toNode = State.nodes.get(conn.to.nodeId);
    if (fromNode) fromNode.ports[conn.from.port].connected = false;
    if (toNode) toNode.ports[conn.to.port].connected = false;
    State.connections.splice(connIndex, 1);
    render();
}

// Context menu
function showContextMenu(x, y, nodeId) {
    removeContextMenu();

    const menu = document.createElement('div');
    menu.id = 'context-menu';
    menu.style.cssText = `
        position: fixed; left: ${x}px; top: ${y}px; z-index: 1000;
        background: var(--bg-panel); border: 1px solid var(--border);
        border-radius: var(--radius); padding: 0.5rem; min-width: 160px;
        box-shadow: 0 10px 30px var(--shadow);
    `;
    menu.innerHTML = `
        <button class="ctx-item" data-action="delete">🗑 Delete</button>
        <button class="ctx-item" data-action="duplicate">📋 Duplicate</button>
        <hr style="border-color: var(--border); margin: 0.5rem 0;">
        <button class="ctx-item" data-action="rename">✏ Rename</button>
    `;
    document.body.appendChild(menu);

    menu.querySelectorAll('.ctx-item').forEach(btn => {
        btn.style.cssText = `
            display: block; width: 100%; padding: 0.5rem 0.75rem;
            background: none; border: none; color: var(--fg-primary);
            font: inherit; text-align: left; cursor: pointer;
            border-radius: var(--radius-sm);
        `;
        btn.addEventListener('mouseenter', () => btn.style.background = 'var(--bg-tertiary)');
        btn.addEventListener('mouseleave', () => btn.style.background = 'none');
        btn.addEventListener('click', () => {
            const action = btn.dataset.action;
            removeContextMenu();
            if (action === 'delete') deleteNode(nodeId);
            else if (action === 'duplicate') duplicateNode(nodeId);
            else if (action === 'rename') editNodeName(nodeId);
        });
    });

    document.addEventListener('click', removeContextMenu, { once: true });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') removeContextMenu(); }, { once: true });
}

function removeContextMenu() {
    const menu = document.getElementById('context-menu');
    if (menu) menu.remove();
}

function duplicateNode(nodeId) {
    const node = State.nodes.get(nodeId);
    if (!node) return;
    const newNode = createNode(node.type, node.x + 40, node.y + 40);
    newNode.name = node.name + ' (copy)';
    newNode.properties = { ...node.properties };
    selectNode(newNode.id);
}

function editNodeName(nodeId) {
    const node = State.nodes.get(nodeId);
    if (!node) return;

    const newName = prompt('Enter node name:', node.name);
    if (newName && newName.trim()) {
        node.name = newName.trim();
        render();
        showProperties(nodeId);
    }
}

// ============================================
// PROPERTIES PANEL
// ============================================

function showEmptyProperties() {
    els.propertiesContent.innerHTML = `
        <div class="empty-state">
            <p>Select a node to edit properties</p>
        </div>
    `;
}

function showProperties(nodeId) {
    if (!nodeId) {
        showEmptyProperties();
        return;
    }

    const node = State.nodes.get(nodeId);
    if (!node) {
        showEmptyProperties();
        return;
    }

    let html = `
        <div class="property-group">
            <label>Node Type</label>
            <input type="text" class="property-input" value="${node.type}" readonly style="background: var(--bg-secondary);">
        </div>
        <div class="property-group">
            <label>Name</label>
            <input type="text" class="property-input" id="prop-name" value="${escapeHtml(node.name)}" placeholder="Node name">
        </div>
    `;

    // Type-specific properties
    if (node.type === 'Parallel') {
        html += `
            <div class="property-group">
                <label>Success Threshold</label>
                <input type="number" class="property-input" id="prop-success-threshold" value="${node.properties.success_threshold || 1}" min="1">
            </div>
            <div class="property-group">
                <label>Failure Threshold</label>
                <input type="number" class="property-input" id="prop-failure-threshold" value="${node.properties.failure_threshold || 1}" min="1">
            </div>
        `;
    } else if (node.type === 'Repeater') {
        html += `
            <div class="property-group">
                <label>Repeat Count (-1 = infinite)</label>
                <input type="number" class="property-input" id="prop-count" value="${node.properties.count || 3}" min="-1">
            </div>
        `;
    } else if (node.type === 'Timeout') {
        html += `
            <div class="property-group">
                <label>Max Ticks</label>
                <input type="number" class="property-input" id="prop-max-ticks" value="${node.properties.max_ticks || 100}" min="1">
            </div>
        `;
    }

    // Custom properties
    if (Object.keys(node.properties).length > 0) {
        const customProps = Object.entries(node.properties).filter(([k]) =>
            !['success_threshold', 'failure_threshold', 'count', 'max_ticks'].includes(k)
        );
        if (customProps.length > 0) {
            html += `<div class="property-group"><label>Custom Properties</label>`;
            for (const [key, value] of customProps) {
                html += `
                    <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
                        <input type="text" class="property-input" value="${escapeHtml(key)}" readonly style="width: 40%; background: var(--bg-secondary);">
                        <input type="text" class="property-input prop-custom-value" data-key="${escapeHtml(key)}" value="${escapeHtml(String(value))}">
                    </div>
                `;
            }
            html += `</div>`;
        }
    }

    els.propertiesContent.innerHTML = html;

    // Event listeners
    const nameInput = document.getElementById('prop-name');
    if (nameInput) {
        nameInput.addEventListener('change', () => {
            node.name = nameInput.value;
            render();
        });
    }

    const thresholdInputs = ['prop-success-threshold', 'prop-failure-threshold', 'prop-count', 'prop-max-ticks'];
    for (const id of thresholdInputs) {
        const input = document.getElementById(id);
        if (input) {
            const propKey = id.replace('prop-', '').replace('-', '_');
            input.addEventListener('change', () => {
                node.properties[propKey] = parseInt(input.value) || 0;
            });
        }
    }

    document.querySelectorAll('.prop-custom-value').forEach(input => {
        input.addEventListener('change', () => {
            node.properties[input.dataset.key] = input.value;
        });
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// CANVAS CONTROLS
// ============================================

function updateZoomDisplay() {
    els.zoomLevel.textContent = Math.round(State.zoom * 100) + '%';
}

function updateNodeCount() {
    els.nodeCount.textContent = State.nodes.size + ' node' + (State.nodes.size !== 1 ? 's' : '');
}

function zoomIn() { State.zoom = Math.min(3, State.zoom * 1.2); updateZoomDisplay(); render(); }
function zoomOut() { State.zoom = Math.max(0.1, State.zoom / 1.2); updateZoomDisplay(); render(); }
function zoomReset() { State.zoom = 1; State.pan = { x: 0, y: 0 }; updateZoomDisplay(); render(); }
function centerView() {
    if (State.nodes.size === 0) {
        State.pan = { x: els.wrapper.clientWidth / 2, y: els.wrapper.clientHeight / 2 };
    } else {
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        let validNodes = 0;
        for (const node of State.nodes.values()) {
            if (isFinite(node.x) && isFinite(node.y) && isFinite(node.width) && isFinite(node.height)) {
                minX = Math.min(minX, node.x);
                minY = Math.min(minY, node.y);
                maxX = Math.max(maxX, node.x + node.width);
                maxY = Math.max(maxY, node.y + node.height);
                validNodes++;
            }
        }
        if (validNodes === 0) {
            State.pan = { x: els.wrapper.clientWidth / 2, y: els.wrapper.clientHeight / 2 };
        } else {
            const cx = (minX + maxX) / 2;
            const cy = (minY + maxY) / 2;
            State.pan.x = els.wrapper.clientWidth / 2 - cx * State.zoom;
            State.pan.y = els.wrapper.clientHeight / 2 - cy * State.zoom;
        }
    }
    render();
}

function toggleGrid() {
    const btn = document.getElementById('btn-grid');
    btn.classList.toggle('active');
    render();
}

// ============================================
// EXECUTION / RUNNING
// ============================================

async function runTree() {
    if (State.isRunning) return;

    const xml = serializeToXML();
    if (!xml.trim()) {
        alert('No tree to run!');
        return;
    }

    State.isRunning = true;
    State.currentTick = 0;
    State.history = [];
    updateRunUI(true);

    try {
        const res = await fetch('/api/run-tree', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ xml, max_ticks: 1000 })
        });
        const data = await res.json();

        // Animate history
        await animateHistory(data.history);
        State.history = data.history;
        renderHistory();
    } catch (err) {
        console.error('Run failed:', err);
        alert('Failed to run tree: ' + err.message);
    } finally {
        State.isRunning = false;
        updateRunUI(false);
        resetNodeStatuses();
        render();
    }
}

async function animateHistory(history) {
    for (let i = 0; i < history.length; i++) {
        if (!State.isRunning) break;
        State.currentTick = i + 1;
        updateTickDisplay();

        // Update node statuses for this tick
        applyTickStatuses(history[i]);
        render();

        // Wait a bit for visualization
        await new Promise(r => setTimeout(r, 300));
    }
}

function applyTickStatuses(tickData) {
    // We don't have per-node status from API, so we'll simulate
    // In a real implementation, the API would return per-node status
    // For now, just mark the path taken
    const { status, blackboard } = tickData;

    // Reset all
    for (const node of State.nodes.values()) {
        node.status = 'idle';
    }

    // Simple heuristic: mark nodes that could be active
    // This is a simplification - real impl would need per-node status from backend
    const visited = new Set();
    function markPath(nodeId) {
        if (visited.has(nodeId)) return;
        visited.add(nodeId);
        const node = State.nodes.get(nodeId);
        if (!node) return;

        if (status === 'RUNNING') node.status = 'running';
        else if (status === 'SUCCESS') node.status = 'success';
        else if (status === 'FAILURE') node.status = 'failure';

        // Find children
        for (const conn of State.connections) {
            if (conn.from.nodeId === nodeId) {
                markPath(conn.to.nodeId);
            }
        }
    }

    // Start from root (nodes with no incoming connections)
    const hasIncoming = new Set();
    for (const conn of State.connections) hasIncoming.add(conn.to.nodeId);
    for (const node of State.nodes.values()) {
        if (!hasIncoming.has(node.id)) {
            markPath(node.id);
            break;
        }
    }
}

function resetNodeStatuses() {
    for (const node of State.nodes.values()) {
        node.status = 'idle';
    }
}

function updateRunUI(running) {
    State.isRunning = running;
    document.getElementById('btn-run').disabled = running;
    document.getElementById('btn-step').disabled = running;
    document.getElementById('btn-stop').disabled = !running;
    document.getElementById('btn-reset').disabled = running;

    const badge = els.statusBadge;
    badge.className = 'badge ' + (running ? 'badge-running' : 'badge-idle');
    badge.textContent = running ? 'Running' : 'Idle';

    els.tickInfo.classList.toggle('hidden', !running);
}

function updateTickDisplay() {
    els.currentTick.textContent = State.currentTick;
}

function stepTree() {
    // Single step - would need backend support for step-by-step
    runTree(); // For now just run full tree
}

function stopTree() {
    State.isRunning = false;
    updateRunUI(false);
}

function resetTree() {
    stopTree();
    resetNodeStatuses();
    State.history = [];
    State.currentTick = 0;
    renderHistory();
    render();
}

// ============================================
// HISTORY PANEL
// ============================================

function renderHistory() {
    if (State.history.length === 0) {
        els.historyContent.innerHTML = '<div class="empty-state">Run a tree to see execution history</div>';
        return;
    }

    let html = '';
    for (let i = State.history.length - 1; i >= 0; i--) {
        const tick = State.history[i];
        const bbEntries = Object.entries(tick.blackboard || {});
        const bbStr = bbEntries.length > 0
            ? bbEntries.map(([k, v]) => `${k}=${v}`).join(', ')
            : 'empty';

        html += `
            <div class="history-entry">
                <span class="history-tick">Tick ${tick.tick}</span>
                <span class="history-status ${tick.status}">${tick.status}</span>
                <span class="history-blackboard">{${bbStr}}</span>
            </div>
        `;
    }
    els.historyContent.innerHTML = html;
}

function clearHistory() {
    State.history = [];
    renderHistory();
}

// ============================================
// SERIALIZATION
// ============================================

function serializeToXML() {
    // Find root (no incoming connections)
    const hasIncoming = new Set();
    for (const conn of State.connections) hasIncoming.add(conn.to.nodeId);

    let rootId = null;
    for (const node of State.nodes.values()) {
        if (!hasIncoming.has(node.id)) {
            rootId = node.id;
            break;
        }
    }

    if (!rootId && State.nodes.size > 0) {
        rootId = State.nodes.values().next().value.id;
    }

    if (!rootId) return '';

    const visited = new Set();
    function serializeNode(nodeId) {
        if (visited.has(nodeId)) return '';
        visited.add(nodeId);

        const node = State.nodes.get(nodeId);
        if (!node) return '';

        const props = Object.entries(node.properties)
            .map(([k, v]) => ` ${k}="${escapeXml(v)}"`)
            .join('');

        const nameAttr = node.name !== node.type ? ` name="${escapeXml(node.name)}"` : '';

        // Find children
        const children = State.connections
            .filter(c => c.from.nodeId === nodeId)
            .map(c => serializeNode(c.to.nodeId))
            .join('\n');

        if (children) {
            return `<${node.type}${nameAttr}${props}>\n${children}\n</${node.type}>`;
        } else {
            return `<${node.type}${nameAttr}${props} />`;
        }
    }

    return `<?xml version="1.0" encoding="UTF-8"?>\n${serializeNode(rootId)}`;
}

function escapeXml(text) {
    return String(text)
        .replace(/&/g, '&')
        .replace(/</g, '<')
        .replace(/>/g, '>')
        .replace(/"/g, '"')
        .replace(/'/g, '&apos;');
}

function deserializeTree(data) {
    clearCanvas();
    const nodeMap = new Map(); // original id -> new id
    const MAX_DEPTH = 20;
    const MAX_NODES = 100;
    let nodeCount = 0;

    function buildNode(nodeData, x = 100, y = 100, depth = 0) {
        if (depth > MAX_DEPTH || nodeCount >= MAX_NODES) {
            console.warn('Max depth/nodes reached, stopping');
            return null;
        }

        if (!NODE_DEFAULTS[nodeData.type]) {
            console.warn('Unknown node type:', nodeData.type);
            return null;
        }

        const node = createNode(nodeData.type, x, y);
        node.name = nodeData.name || nodeData.type;
        node.properties = { ...nodeData.properties };
        nodeCount++;

        if (nodeData.children && nodeData.children.length > 0) {
            let childY = y;
            const spacing = 100;
            for (let i = 0; i < nodeData.children.length; i++) {
                const childData = nodeData.children[i];
                const childX = x + 220;
                const child = buildNode(childData, childX, childY, depth + 1);
                if (child) {
                    addConnection(node.id, 'output', child.id, 'input');
                    childY += child.height + spacing;
                }
            }
        }

        return node;
    }

    // Start from root
    try {
        buildNode(data, 100, 100);
        centerView();
    } catch (e) {
        console.error('Deserialize error:', e);
        clearCanvas();
    }
}

function saveXML() {
    const xml = serializeToXML();
    const filename = els.saveFilename.value || 'tree.xml';
    const blob = new Blob([xml], { type: 'application/xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    closeModal();
}

function exportXML() {
    const xml = serializeToXML();
    navigator.clipboard.writeText(xml).then(() => {
        showToast('XML copied to clipboard!');
    }).catch(() => {
        // Fallback
        const textarea = document.createElement('textarea');
        textarea.value = xml;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showToast('XML copied to clipboard!');
    });
}

function showToast(msg) {
    const toast = document.createElement('div');
    toast.textContent = msg;
    toast.style.cssText = `
        position: fixed; bottom: 2rem; left: 50%; transform: translateX(-50%);
        background: var(--bg-panel); border: 1px solid var(--accent);
        padding: 0.75rem 1.5rem; border-radius: var(--radius);
        z-index: 1000; animation: slideUp 0.3s ease;
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2000);
}

// ============================================
// MODALS
// ============================================

function openLoadModal() {
    els.modalOverlay.classList.remove('hidden');
    els.loadModal.classList.remove('hidden');
}

function openSaveModal() {
    els.modalOverlay.classList.remove('hidden');
    els.saveModal.classList.remove('hidden');
    els.saveFilename.focus();
    els.saveFilename.select();
}

function closeModal() {
    els.modalOverlay.classList.add('hidden');
    els.loadModal.classList.add('hidden');
    els.saveModal.classList.add('hidden');
    State.selectedExampleFile = null;
    document.querySelectorAll('.example-item').forEach(el => el.classList.remove('selected'));
}

function confirmLoad() {
    if (State.selectedExampleFile) {
        loadExample(State.selectedExampleFile);
    }
}

function confirmSave() {
    saveXML();
}

// ============================================
// EVENT LISTENERS
// ============================================

function setupEventListeners() {
    // Toolbar buttons
    document.getElementById('btn-load').addEventListener('click', openLoadModal);
    document.getElementById('btn-save').addEventListener('click', openSaveModal);
    document.getElementById('btn-export').addEventListener('click', exportXML);
    document.getElementById('btn-run').addEventListener('click', runTree);
    document.getElementById('btn-step').addEventListener('click', stepTree);
    document.getElementById('btn-stop').addEventListener('click', stopTree);
    document.getElementById('btn-reset').addEventListener('click', resetTree);
    document.getElementById('btn-zoom-in').addEventListener('click', zoomIn);
    document.getElementById('btn-zoom-out').addEventListener('click', zoomOut);
    document.getElementById('btn-zoom-reset').addEventListener('click', zoomReset);
    document.getElementById('btn-center').addEventListener('click', centerView);
    document.getElementById('btn-grid').addEventListener('click', toggleGrid);
    document.getElementById('btn-clear-history').addEventListener('click', clearHistory);

    // Example select
    els.exampleSelect.addEventListener('change', (e) => {
        if (e.target.value) loadExample(e.target.value);
    });

    // Modals
    document.getElementById('modal-cancel').addEventListener('click', closeModal);
    document.getElementById('modal-load').addEventListener('click', confirmLoad);
    document.getElementById('save-cancel').addEventListener('click', closeModal);
    document.getElementById('save-confirm').addEventListener('click', confirmSave);
    els.modalOverlay.addEventListener('click', closeModal);

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        switch (e.key) {
            case 'r':
            case 'R': if (!State.isRunning) runTree(); break;
            case ' ': e.preventDefault(); if (State.isRunning) stepTree(); break;
            case 'Escape': stopTree(); closeModal(); removeContextMenu(); break;
            case 'Backspace': resetTree(); break;
            case 's':
            case 'S': if (e.ctrlKey || e.metaKey) { e.preventDefault(); openSaveModal(); } break;
            case 'e':
            case 'E': if (e.ctrlKey || e.metaKey) { e.preventDefault(); exportXML(); } break;
            case 'l':
            case 'L': if (e.ctrlKey || e.metaKey) { e.preventDefault(); openLoadModal(); } break;
            case '+':
            case '=': zoomIn(); break;
            case '-': zoomOut(); break;
            case '0': zoomReset(); break;
            case 'c':
            case 'C': centerView(); break;
            case 'g':
            case 'G': toggleGrid(); break;
            case 'Delete':
            case 'Backspace': if (State.selectedNodeId) deleteNode(State.selectedNodeId); break;
        }
    });

    // Prevent context menu on canvas (we handle our own)
    els.canvas.addEventListener('contextmenu', e => e.preventDefault());

    // Drop on canvas (from palette)
    els.canvas.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
    });

    els.canvas.addEventListener('drop', (e) => {
        e.preventDefault();
        const type = e.dataTransfer.getData('text/plain');
        if (type && NODE_DEFAULTS[type]) {
            const pos = getCanvasPos(e);
            const node = createNode(type, pos.x, pos.y);
            selectNode(node.id);
        }
    });
}

// ============================================
// START
// ============================================

// Add slideUp animation
const style = document.createElement('style');
style.textContent = `
@keyframes slideUp {
    from { opacity: 0; transform: translateX(-50%) translateY(20px); }
    to { opacity: 1; transform: translateX(-50%) translateY(0); }
}
`;
document.head.appendChild(style);

// Initialize when DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}