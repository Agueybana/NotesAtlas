const canvas = document.getElementById("graphCanvas");
const ctx = canvas.getContext("2d");

const els = {
  search: document.getElementById("graphSearch"),
  typeFilter: document.getElementById("typeFilter"),
  fitButton: document.getElementById("fitButton"),
  labelsButton: document.getElementById("labelsButton"),
  pauseButton: document.getElementById("pauseButton"),
  detailsTitle: document.getElementById("detailsTitle"),
  detailsCopy: document.getElementById("detailsCopy"),
  statNodes: document.getElementById("statNodes"),
  statLinks: document.getElementById("statLinks"),
  statNotes: document.getElementById("statNotes"),
  statConcepts: document.getElementById("statConcepts"),
  loadingOverlay: document.getElementById("loadingOverlay"),
  loadingPhase: document.getElementById("loadingPhase"),
  loadingMessage: document.getElementById("loadingMessage"),
  loadingProgress: document.getElementById("loadingProgress"),
  toast: document.getElementById("mapToast"),
};

const graph = {
  nodes: [],
  links: [],
  visibleNodes: [],
  visibleLinks: [],
  byId: new Map(),
  neighbors: new Map(),
  hover: null,
  selected: null,
  query: "",
  type: "all",
  labels: true,
  paused: false,
  dragging: false,
  dragStart: null,
  transform: { x: 0, y: 0, k: 1 },
  categoryAnchors: new Map(),
  lastPointer: { x: 0, y: 0 },
};

const nodePriority = {
  root: 5,
  category: 4,
  subcategory: 3,
  concept: 2,
  note: 1,
};

function setLoading(phase, message, percent) {
  els.loadingPhase.textContent = phase;
  els.loadingMessage.textContent = message;
  els.loadingProgress.style.width = `${percent}%`;
}

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("is-visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => els.toast.classList.remove("is-visible"), 3000);
}

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "Request failed");
  return payload;
}

function resizeCanvas() {
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.floor(window.innerWidth * dpr);
  canvas.height = Math.floor(window.innerHeight * dpr);
  canvas.style.width = `${window.innerWidth}px`;
  canvas.style.height = `${window.innerHeight}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function hashString(value) {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash += (hash << 1) + (hash << 4) + (hash << 7) + (hash << 8) + (hash << 24);
  }
  return Math.abs(hash >>> 0);
}

function polar(angle, radius) {
  return {
    x: Math.cos(angle) * radius,
    y: Math.sin(angle) * radius,
  };
}

function graphPoint(event) {
  return {
    x: (event.clientX - graph.transform.x) / graph.transform.k,
    y: (event.clientY - graph.transform.y) / graph.transform.k,
  };
}

function initializeGraph(payload) {
  const categories = payload.nodes.filter((node) => node.type === "category");
  const angleStep = (Math.PI * 2) / Math.max(categories.length, 1);
  categories.forEach((node, index) => {
    const anchor = polar(index * angleStep - Math.PI / 2, 520);
    graph.categoryAnchors.set(node.id, anchor);
    graph.categoryAnchors.set(node.label, anchor);
  });

  graph.nodes = payload.nodes.map((node) => {
    const hash = hashString(node.id);
    const jitter = polar((hash % 6283) / 1000, 40 + (hash % 170));
    let base = { x: 0, y: 0 };
    if (node.type === "category") base = graph.categoryAnchors.get(node.id) || base;
    if (node.type === "subcategory") base = graph.categoryAnchors.get(`category:${node.category}`) || base;
    if (node.type === "note") base = graph.categoryAnchors.get(`category:${node.category}`) || base;
    if (node.type === "concept") base = polar((hash % 6283) / 1000, 300 + (hash % 260));
    return {
      ...node,
      x: base.x + jitter.x,
      y: base.y + jitter.y,
      vx: 0,
      vy: 0,
      visible: true,
      matches: true,
    };
  });

  graph.byId = new Map(graph.nodes.map((node) => [node.id, node]));
  graph.links = payload.links
    .map((link) => ({
      ...link,
      sourceNode: graph.byId.get(link.source),
      targetNode: graph.byId.get(link.target),
    }))
    .filter((link) => link.sourceNode && link.targetNode);

  graph.neighbors = new Map(graph.nodes.map((node) => [node.id, new Set()]));
  graph.links.forEach((link) => {
    graph.neighbors.get(link.source).add(link.target);
    graph.neighbors.get(link.target).add(link.source);
  });

  els.statNodes.textContent = payload.counts.nodes.toLocaleString();
  els.statLinks.textContent = payload.counts.links.toLocaleString();
  els.statNotes.textContent = payload.counts.notes.toLocaleString();
  els.statConcepts.textContent = payload.counts.concepts.toLocaleString();
  els.detailsTitle.textContent = "Interactive knowledge graph";
  els.detailsCopy.textContent =
    "Hover nodes to isolate nearby connections. Click note nodes to open the source note in Apple Notes.";
  applyFilters();
  fitGraph();
}

function applyFilters() {
  const query = graph.query.trim().toLowerCase();
  graph.nodes.forEach((node) => {
    const haystack = `${node.label} ${node.category || ""} ${node.subcategory || ""} ${node.folder || ""}`.toLowerCase();
    const typeMatches = graph.type === "all" || node.type === graph.type || node.type === "root";
    const queryMatches = !query || haystack.includes(query);
    node.matches = typeMatches && queryMatches;
  });

  if (!query && graph.type === "all") {
    graph.nodes.forEach((node) => {
      node.visible = true;
    });
  } else {
    const expanded = new Set();
    graph.nodes.forEach((node) => {
      if (!node.matches) return;
      expanded.add(node.id);
      const neighbors = graph.neighbors.get(node.id) || new Set();
      neighbors.forEach((neighbor) => expanded.add(neighbor));
    });
    graph.nodes.forEach((node) => {
      node.visible = expanded.has(node.id);
    });
  }
  graph.visibleNodes = graph.nodes.filter((node) => node.visible);
  graph.visibleLinks = graph.links.filter((link) => link.sourceNode.visible && link.targetNode.visible);
}

function fitGraph() {
  if (!graph.visibleNodes.length) return;
  const xs = graph.visibleNodes.map((node) => node.x);
  const ys = graph.visibleNodes.map((node) => node.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const width = Math.max(1, maxX - minX);
  const height = Math.max(1, maxY - minY);
  const scale = Math.min(window.innerWidth / (width + 360), window.innerHeight / (height + 280), 1.25);
  graph.transform.k = Math.max(0.18, scale);
  graph.transform.x = window.innerWidth / 2 - ((minX + maxX) / 2) * graph.transform.k;
  graph.transform.y = window.innerHeight / 2 - ((minY + maxY) / 2) * graph.transform.k;
}

function preferredDistance(link) {
  if (link.type === "category") return 220;
  if (link.type === "subcategory") return 120;
  if (link.type === "concept") return 170;
  return 44;
}

function simulate() {
  const centerForce = 0.002;
  graph.visibleLinks.forEach((link) => {
    const source = link.sourceNode;
    const target = link.targetNode;
    const dx = target.x - source.x;
    const dy = target.y - source.y;
    const distance = Math.hypot(dx, dy) || 1;
    const targetDistance = preferredDistance(link);
    const force = (distance - targetDistance) * 0.0009 * Number(link.weight || 1);
    const fx = (dx / distance) * force;
    const fy = (dy / distance) * force;
    source.vx += fx;
    source.vy += fy;
    target.vx -= fx;
    target.vy -= fy;
  });

  graph.visibleNodes.forEach((node) => {
    let anchor = { x: 0, y: 0 };
    if (node.type === "category") anchor = graph.categoryAnchors.get(node.id) || anchor;
    if (node.type === "subcategory" || node.type === "note") {
      anchor = graph.categoryAnchors.get(`category:${node.category}`) || anchor;
    }
    if (node.type === "concept") {
      const hash = hashString(node.id);
      anchor = polar((hash % 6283) / 1000, 360 + (hash % 320));
    }
    node.vx += (anchor.x - node.x) * centerForce * nodePriority[node.type];
    node.vy += (anchor.y - node.y) * centerForce * nodePriority[node.type];
    node.vx *= 0.88;
    node.vy *= 0.88;
    node.x += node.vx;
    node.y += node.vy;
  });
}

function activeNeighborhood() {
  const active = graph.hover || graph.selected;
  if (!active) return null;
  const set = new Set([active.id]);
  const neighbors = graph.neighbors.get(active.id) || new Set();
  neighbors.forEach((id) => set.add(id));
  return set;
}

function drawText(text, x, y, color, size = 12) {
  ctx.font = `700 ${size}px Avenir Next, Helvetica Neue, sans-serif`;
  ctx.fillStyle = color;
  ctx.shadowColor = "rgba(0,0,0,0.72)";
  ctx.shadowBlur = 8;
  ctx.fillText(text, x, y);
  ctx.shadowBlur = 0;
}

function render() {
  ctx.save();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#070a0f";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.restore();

  ctx.save();
  ctx.translate(graph.transform.x, graph.transform.y);
  ctx.scale(graph.transform.k, graph.transform.k);

  const neighborhood = activeNeighborhood();
  graph.visibleLinks.forEach((link) => {
    const source = link.sourceNode;
    const target = link.targetNode;
    const active = !neighborhood || (neighborhood.has(source.id) && neighborhood.has(target.id));
    ctx.beginPath();
    ctx.moveTo(source.x, source.y);
    ctx.lineTo(target.x, target.y);
    ctx.strokeStyle = active ? "rgba(132, 220, 255, 0.36)" : "rgba(120, 150, 190, 0.055)";
    ctx.lineWidth = active ? Math.max(0.55, Number(link.weight || 1) * 0.58) : 0.35;
    ctx.stroke();
  });

  graph.visibleNodes
    .slice()
    .sort((a, b) => nodePriority[a.type] - nodePriority[b.type])
    .forEach((node) => {
      const active = !neighborhood || neighborhood.has(node.id);
      const radius = (node.size || 4) * (node.type === "note" ? Math.max(0.7, graph.transform.k ** -0.12) : 1);
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = active ? node.color : "rgba(90, 105, 125, 0.2)";
      ctx.globalAlpha = active ? 0.92 : 0.22;
      ctx.shadowColor = active ? node.color : "transparent";
      ctx.shadowBlur = active && node.type !== "note" ? 18 : 0;
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.globalAlpha = 1;
    });

  if (graph.labels) {
    graph.visibleNodes.forEach((node) => {
      if (node.type === "note" && node !== graph.hover && node !== graph.selected) return;
      if (node.type === "subcategory" && graph.transform.k < 0.42 && node !== graph.hover) return;
      if (node.type === "concept" && graph.transform.k < 0.58 && node !== graph.hover) return;
      const active = !neighborhood || neighborhood.has(node.id);
      if (!active && node.type !== "category") return;
      const label = node.label.length > 34 ? `${node.label.slice(0, 33)}...` : node.label;
      const color = node.type === "note" ? "#edf7ff" : node.color;
      const size = node.type === "category" ? 18 : node.type === "subcategory" ? 12 : 10;
      drawText(label, node.x + (node.size || 4) + 4, node.y + 3, color, size);
    });
  }

  ctx.restore();
}

function nearestNode(event) {
  const point = graphPoint(event);
  let best = null;
  let bestDistance = Infinity;
  graph.visibleNodes.forEach((node) => {
    const radius = Math.max(8, (node.size || 4) + 5 / graph.transform.k);
    const distance = Math.hypot(node.x - point.x, node.y - point.y);
    if (distance < radius && distance < bestDistance) {
      best = node;
      bestDistance = distance;
    }
  });
  return best;
}

function updateDetails(node) {
  if (!node) {
    els.detailsTitle.textContent = "Interactive knowledge graph";
    els.detailsCopy.textContent =
      "Hover nodes to isolate nearby connections. Click note nodes to open the source note in Apple Notes.";
    return;
  }
  els.detailsTitle.textContent = node.label;
  if (node.type === "note") {
    els.detailsCopy.textContent = `${node.category} / ${node.subcategory} - ${node.snippet || "No snippet available."}`;
    return;
  }
  if (node.type === "concept") {
    els.detailsCopy.textContent = `Concept hub connected to ${node.count.toLocaleString()} notes.`;
    return;
  }
  els.detailsCopy.textContent = `${node.type} node containing ${Number(node.count || 0).toLocaleString()} notes.`;
}

async function openNote(node) {
  if (!node?.note_id) return;
  showToast("Opening note in Apple Notes...");
  await fetchJSON("/api/open", {
    method: "POST",
    body: JSON.stringify({ note_id: node.note_id }),
  });
}

function animate() {
  if (!graph.paused) simulate();
  render();
  window.requestAnimationFrame(animate);
}

function wireEvents() {
  window.addEventListener("resize", () => {
    resizeCanvas();
    fitGraph();
  });

  canvas.addEventListener("pointerdown", (event) => {
    graph.dragging = true;
    graph.dragStart = {
      x: event.clientX,
      y: event.clientY,
      ox: graph.transform.x,
      oy: graph.transform.y,
    };
    canvas.classList.add("is-dragging");
  });

  canvas.addEventListener("pointermove", (event) => {
    graph.lastPointer = { x: event.clientX, y: event.clientY };
    if (graph.dragging && graph.dragStart) {
      graph.transform.x = graph.dragStart.ox + event.clientX - graph.dragStart.x;
      graph.transform.y = graph.dragStart.oy + event.clientY - graph.dragStart.y;
      return;
    }
    graph.hover = nearestNode(event);
    updateDetails(graph.hover || graph.selected);
  });

  window.addEventListener("pointerup", () => {
    graph.dragging = false;
    graph.dragStart = null;
    canvas.classList.remove("is-dragging");
  });

  canvas.addEventListener("click", async (event) => {
    const node = nearestNode(event);
    graph.selected = node;
    updateDetails(node);
    if (node?.type === "note") {
      openNote(node).catch((error) => showToast(error.message));
    }
  });

  canvas.addEventListener("wheel", (event) => {
    event.preventDefault();
    const before = graphPoint(event);
    const scale = event.deltaY < 0 ? 1.08 : 0.92;
    graph.transform.k = Math.min(4, Math.max(0.08, graph.transform.k * scale));
    graph.transform.x = event.clientX - before.x * graph.transform.k;
    graph.transform.y = event.clientY - before.y * graph.transform.k;
  }, { passive: false });

  let searchTimer = null;
  els.search.addEventListener("input", (event) => {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(() => {
      graph.query = event.target.value;
      applyFilters();
    }, 160);
  });

  els.typeFilter.addEventListener("change", (event) => {
    graph.type = event.target.value;
    applyFilters();
  });

  els.fitButton.addEventListener("click", fitGraph);
  els.labelsButton.addEventListener("click", () => {
    graph.labels = !graph.labels;
    els.labelsButton.textContent = graph.labels ? "Labels On" : "Labels Off";
  });
  els.pauseButton.addEventListener("click", () => {
    graph.paused = !graph.paused;
    els.pauseButton.textContent = graph.paused ? "Resume" : "Pause";
  });
}

async function init() {
  resizeCanvas();
  wireEvents();
  setLoading("Loading graph", "Reading local catalog data.", 18);
  const payload = await fetchJSON("/api/mind-map");
  setLoading("Indexing nodes", "Connecting notes, categories, and concept hubs.", 58);
  initializeGraph(payload);
  setLoading("Starting physics", "Letting the graph settle into place.", 92);
  window.setTimeout(() => els.loadingOverlay.classList.add("is-hidden"), 450);
  animate();
}

init().catch((error) => {
  setLoading("Error", error.message, 0);
});
