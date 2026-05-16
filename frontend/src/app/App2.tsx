import { useState, useRef, useCallback, useMemo } from "react";
import { ChevronRight, ChevronDown, Search, Loader2, ImageOff } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { Toaster, toast } from "sonner";

// ─── Types ───────────────────────────────────────────────────────────────────

type NodeType = "root" | "service" | "module" | "component" | "resource";

interface TreeNode {
  id: string;
  label: string;
  type: NodeType;
  meta?: string;
  imageUrl?: string;
  children?: TreeNode[];
}

// ─── Layout engine ────────────────────────────────────────────────────────────
// Nodes have variable height: base height + optional image panel.
// The subtree height algorithm works in pixels so mixed card sizes compose cleanly.


function cardH(id: string, cardExpanded: Set<string>): number {
  return cardExpanded.has(id) ? NODE_H_BASE + NODE_H_IMAGE : NODE_H_BASE;
}

interface LayoutNode extends TreeNode {
  x: number;
  y: number;
  height: number;
}
let uidCounter = 0;

// function assignUniqueIds(node: TreeNode): TreeNode {
//   const uid = `node_${uidCounter++}`;
//   return {
//     ...node,
//     id: uid,
//     children: node.children?.map(child => assignUniqueIds(child)),
//   };
// }

function assignUniqueIds(node: TreeNode): TreeNode {
  uidCounter = 0;  // reset at the top level call only
  return assignUniqueIdsInner(node);
}

function assignUniqueIdsInner(node: TreeNode): TreeNode {
  const uid = `node_${uidCounter++}`;
  return {
    ...node,
    id: uid,
    children: node.children?.map(child => assignUniqueIdsInner(child)),
  };
}

function subtreeH(
  node: TreeNode,
  treeEx: Set<string>,
  cardEx: Set<string>
): number {
  const myH = cardH(node.id, cardEx);
  if (!node.children?.length || !treeEx.has(node.id)) return myH;
  const ch = node.children;
  const childTotal =
    ch.reduce((s, c) => s + subtreeH(c, treeEx, cardEx), 0) +
    (ch.length - 1) * ROW_GAP;
  return Math.max(myH, childTotal);
}

function buildLayout(
  node: TreeNode,
  depth: number,
  yTop: number,
  treeEx: Set<string>,
  cardEx: Set<string>,
  out: LayoutNode[] = []
): LayoutNode[] {
  const myH = cardH(node.id, cardEx);
  const totalH = subtreeH(node, treeEx, cardEx);
  const x = depth * (NODE_W + COL_GAP);
  const y = yTop + (totalH - myH) / 2;
  out.push({ ...node, x, y, height: myH });

  if (node.children && treeEx.has(node.id)) {
    let cy = yTop;
    for (const child of node.children) {
      buildLayout(child, depth + 1, cy, treeEx, cardEx, out);
      cy += subtreeH(child, treeEx, cardEx) + ROW_GAP;
    }
  }
  return out;
}

// ─── Visual tokens ────────────────────────────────────────────────────────────

const TYPE_CONFIG: Record<
  NodeType,
  { dot: string; badge: string; text: string; label: string }
> = {
  root:      { dot: "#22d3ee", badge: "rgba(34,211,238,0.12)",  text: "#22d3ee", label: "root" },
  //service:   { dot: "#a78bfa", badge: "rgba(167,139,250,0.12)", text: "#a78bfa", label: "service" },
  module:    { dot: "#34d399", badge: "rgba(52,211,153,0.12)",  text: "#34d399", label: "Crafting?" },
  component: { dot: "#fb923c", badge: "rgba(251,146,60,0.12)",  text: "#fb923c", label: "N/A (raw leaf)" },
  resource:  { dot: "#94a3b8", badge: "rgba(148,163,184,0.09)", text: "#94a3b8", label: "Raw Resource" },
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function collectAllIds(node: TreeNode, out = new Set<string>()): Set<string> {
  if (node.children?.length) {
    out.add(node.id);
    node.children.forEach((c) => collectAllIds(c, out));
  }
  return out;
}

function countAll(node: TreeNode): number {
  return 1 + (node.children?.reduce((s, c) => s + countAll(c), 0) ?? 0);
}

// ─── API ─────────────────────────────────────────────────────────────────────

async function fetchTreeRoot(query: string): Promise<TreeNode> {
  const res = await fetch(`http://localhost:5000/tree?item=${encodeURIComponent(query)}`);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(body || `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<TreeNode>;
}

// ─── Component ───────────────────────────────────────────────────────────────

const INIT_EXPANDED = new Set<string>([
  "root", "frontend", "gateway", "services", "data",
]);

export default function App() {
  const [treeRoot, setTreeRoot] = useState<TreeNode>(() => assignUniqueIds(DEMO_TREE));
  const [treeExpanded, setTreeExpanded] = useState<Set<string>>(INIT_EXPANDED);
  const [cardExpanded, setCardExpanded] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<string | null>(null);
  const [pan, setPan] = useState({ x: 48, y: 56 });
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const isPanning = useRef(false);
  const dragOrigin = useRef({ mx: 0, my: 0, px: 0, py: 0 });
  const [panActive, setPanActive] = useState(false);

  const nodes = useMemo(
    () => buildLayout(treeRoot, 0, 0, treeExpanded, cardExpanded),
    [treeRoot, treeExpanded, cardExpanded]
  );
  const byId = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);

  const edges = useMemo(() => {
    const result: { fid: string; tid: string }[] = [];
    for (const n of nodes) {
      if (n.children && treeExpanded.has(n.id)) {
        for (const c of n.children) {
          if (byId.has(c.id)) result.push({ fid: n.id, tid: c.id });
        }
      }
    }
    return result;
  }, [nodes, byId, treeExpanded]);

  const canvasW = nodes.reduce((m, n) => Math.max(m, n.x + NODE_W + 120), 600);
  const canvasH = nodes.reduce((m, n) => Math.max(m, n.y + n.height + 120), 400);

  const toggleTree = useCallback((id: string) => {
    setTreeExpanded((p) => {
      const s = new Set(p);
      s.has(id) ? s.delete(id) : s.add(id);
      return s;
    });
  }, []);

  const toggleCard = useCallback((id: string) => {
    setCardExpanded((p) => {
      const s = new Set(p);
      s.has(id) ? s.delete(id) : s.add(id);
      return s;
    });
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = searchQuery.trim();
    if (!q || isLoading) return;
    setIsLoading(true);
    try {
      const data = await fetchTreeRoot(q);
      const uniqueTree = assignUniqueIds(data);
      setTreeRoot(uniqueTree);
      setTreeExpanded(new Set([uniqueTree.id]));
      setCardExpanded(new Set());
      setSelected(null);
      setPan({ x: 48, y: 56 });
      toast.success(`Loaded: ${data.label}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load tree");
    } finally {
      setIsLoading(false);
    }
  };

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if ((e.target as HTMLElement).closest("[data-node]")) return;
      isPanning.current = true;
      setPanActive(true);
      dragOrigin.current = { mx: e.clientX, my: e.clientY, px: pan.x, py: pan.y };
    },
    [pan]
  );

  const onMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isPanning.current) return;
    setPan({
      x: dragOrigin.current.px + e.clientX - dragOrigin.current.mx,
      y: dragOrigin.current.py + e.clientY - dragOrigin.current.my,
    });
  }, []);

  const onMouseUp = useCallback(() => {
    isPanning.current = false;
    setPanActive(false);
  }, []);

  const totalNodes = useMemo(() => countAll(treeRoot), [treeRoot]);

  return (
    <>
      <Toaster
        theme="dark"
        toastOptions={{
          style: {
            background: "#111120",
            border: "1px solid rgba(255,255,255,0.09)",
            color: "#dde2ea",
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 12,
          },
        }}
      />

      <div
        className="size-full flex flex-col bg-background text-foreground overflow-hidden"
        style={{ fontFamily: "'Inter', sans-serif" }}
      >
        {/* ── Toolbar ── */}
        <header className="shrink-0 flex items-center gap-3 border-b border-border px-4 h-12">
          {/* Brand */}
          <div className="flex items-center gap-2 shrink-0">
            <span
              className="w-2 h-2 rounded-full"
              style={{ background: "#22d3ee", boxShadow: "0 0 8px rgba(34,211,238,0.7)" }}
            />
            <span className="text-sm font-semibold tracking-tight whitespace-nowrap">Tree Explorer</span>
          </div>

          {/* Divider */}
          <div className="w-px h-5 bg-border shrink-0" />

          {/* Search */}
          <form onSubmit={handleSearch} className="flex items-center gap-2 flex-1 min-w-0">
            <div className="relative flex-1 min-w-0 max-w-md">
              <Search
                size={13}
                className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none"
              />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search or enter an ID to load as root…"
                disabled={isLoading}
                className="w-full h-7 pl-8 pr-3 text-xs rounded border border-border bg-transparent text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-[rgba(34,211,238,0.4)] focus:ring-1 focus:ring-[rgba(34,211,238,0.15)] transition-colors disabled:opacity-50"
                style={{ fontFamily: "'JetBrains Mono', monospace" }}
              />
            </div>
            <button
              type="submit"
              disabled={isLoading || !searchQuery.trim()}
              className="shrink-0 h-7 px-3 text-xs rounded border border-border text-muted-foreground hover:text-foreground hover:border-white/20 transition-colors disabled:opacity-40 disabled:pointer-events-none flex items-center gap-1.5"
            >
              {isLoading ? (
                <>
                  <Loader2 size={11} className="animate-spin" />
                  Loading
                </>
              ) : (
                "Load"
              )}
            </button>
          </form>

          {/* Controls */}
          <div className="flex items-center gap-2 shrink-0 ml-auto">
            <span
              className="text-xs text-muted-foreground tabular-nums mr-1"
              style={{ fontFamily: "'JetBrains Mono', monospace" }}
            >
              {nodes.length}&thinsp;/&thinsp;{totalNodes}
            </span>
            {(
              [
                { label: "Expand all", fn: () => setTreeExpanded(collectAllIds(treeRoot)) },
                { label: "Collapse all", fn: () => setTreeExpanded(new Set([treeRoot.id])) },
                { label: "Reset view", fn: () => setPan({ x: 48, y: 56 }) },
              ] as const
            ).map(({ label, fn }) => (
              <button
                key={label}
                onClick={fn}
                className="text-xs px-2.5 py-1 rounded border border-border text-muted-foreground hover:text-foreground hover:border-white/20 transition-colors"
              >
                {label}
              </button>
            ))}
          </div>
        </header>

        {/* ── Legend ── */}
        <div className="shrink-0 flex items-center gap-5 px-4 h-8 border-b border-border">
          {(Object.entries(TYPE_CONFIG) as [NodeType, (typeof TYPE_CONFIG)[NodeType]][]).map(
            ([type, { dot, label }]) => (
              <div key={type} className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: dot }} />
                <span
                  className="text-[11px] text-muted-foreground"
                  style={{ fontFamily: "'JetBrains Mono', monospace" }}
                >
                  {label}
                </span>
              </div>
            )
          )}
        </div>

        {/* ── Canvas ── */}
        <div
          className="flex-1 relative overflow-hidden select-none"
          style={{ cursor: panActive ? "grabbing" : "grab" }}
          onMouseDown={onMouseDown}
          onMouseMove={onMouseMove}
          onMouseUp={onMouseUp}
          onMouseLeave={onMouseUp}
        >
          {/* Dot grid */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none" aria-hidden>
            <defs>
              <pattern
                id="dotgrid"
                width={28}
                height={28}
                x={pan.x % 28}
                y={pan.y % 28}
                patternUnits="userSpaceOnUse"
              >
                <circle cx={1} cy={1} r={1} fill="rgba(255,255,255,0.045)" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#dotgrid)" />
          </svg>

          {/* Pan layer */}
          <div
            style={{
              position: "absolute",
              transform: `translate(${pan.x}px, ${pan.y}px)`,
              width: canvasW,
              height: canvasH,
            }}
          >
            {/* SVG edges — uses node.height for correct midpoint */}
            <svg
              style={{
                position: "absolute",
                inset: 0,
                width: canvasW,
                height: canvasH,
                overflow: "visible",
                pointerEvents: "none",
              }}
              aria-hidden
            >
              {edges.map(({ fid, tid }) => {
                const f = byId.get(fid);
                const t = byId.get(tid);
                if (!f || !t) return null;
                const x1 = f.x + NODE_W;
                const y1 = f.y + f.height / 2;
                const x2 = t.x;
                const y2 = t.y + t.height / 2;
                const mx = (x1 + x2) / 2;
                const isActive = selected === fid || selected === tid;
                return (
                  <path
                    key={`${fid}-${tid}`}
                    d={`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`}
                    fill="none"
                    stroke={isActive ? "rgba(34,211,238,0.55)" : "rgba(255,255,255,0.085)"}
                    strokeWidth={isActive ? 1.5 : 1}
                  />
                );
              })}
            </svg>

            {/* Nodes */}
            <AnimatePresence>
              {nodes.map((node) => {
                const cfg = TYPE_CONFIG[node.type];
                const isTreeEx = treeExpanded.has(node.id);
                const isCardEx = cardExpanded.has(node.id);
                const isSel = selected === node.id;
                const hasKids = !!node.children?.length;

                return (
                  <motion.div
                    key={node.id}
                    initial={{ opacity: 0, scale: 0.88, x: node.x, y: node.y, height: node.height }}
                    animate={{ opacity: 1, scale: 1, x: node.x, y: node.y, height: node.height }}
                    exit={{ opacity: 0, scale: 0.88 }}
                    transition={{ duration: 0.22, ease: [0.25, 0.46, 0.45, 0.94] }}
                    style={{ position: "absolute", left: 0, top: 0, width: NODE_W }}
                    data-node
                    onClick={() => setSelected(isSel ? null : node.id)}
                  >
                    <div
                      className="w-full h-full flex flex-col rounded-lg overflow-hidden transition-shadow duration-150"
                      style={{
                        background: isSel ? "rgba(34,211,238,0.045)" : "var(--card)",
                        border: `1px solid ${isSel ? "rgba(34,211,238,0.42)" : "rgba(255,255,255,0.07)"}`,
                        boxShadow: isSel
                          ? "inset 3px 0 0 rgba(34,211,238,0.65), 0 4px 24px rgba(0,0,0,0.45)"
                          : "0 2px 12px rgba(0,0,0,0.3)",
                        cursor: "pointer",
                      }}
                    >
                      {/* ── Card content ── */}
                      <div className="flex-1 flex flex-col justify-center px-3.5 pt-2.5 pb-2 min-h-0">
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <span
                              className="w-1.5 h-1.5 rounded-full shrink-0"
                              style={{ background: cfg.dot }}
                            />
                            <span className="text-[13px] font-medium text-foreground truncate leading-tight">
                              {node.label}
                            </span>
                          </div>
                          {hasKids && (
                            <button
                              data-node
                              className="shrink-0 w-[22px] h-[22px] flex items-center justify-center rounded hover:bg-white/5 transition-colors"
                              style={{ color: isTreeEx ? cfg.dot : "rgba(255,255,255,0.28)" }}
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleTree(node.id);
                              }}
                              aria-label={isTreeEx ? "Collapse children" : "Expand children"}
                            >
                              <ChevronRight
                                size={11}
                                style={{
                                  transform: isTreeEx ? "rotate(90deg)" : "rotate(0deg)",
                                  transition: "transform 0.2s ease",
                                }}
                              />
                            </button>
                          )}
                        </div>
                        <div className="flex items-center gap-2 mt-2">
                          {node.meta && (
                            <span
                              className="text-[10px] px-1.5 py-px rounded leading-none"
                              style={{
                                background: cfg.badge,
                                color: cfg.text,
                                fontFamily: "'JetBrains Mono', monospace",
                              }}
                            >
                              {node.meta}
                            </span>
                          )}
                          {hasKids && (
                            <span
                              className="text-[10px] text-muted-foreground leading-none"
                              style={{ fontFamily: "'JetBrains Mono', monospace" }}
                            >
                              {node.children!.length}&thinsp;children
                            </span>
                          )}
                        </div>
                      </div>

                      {/* ── Image panel (visible when card expanded) ── */}
                      <AnimatePresence>
                        {isCardEx && (
                          <motion.div
                            key="img"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 0.15 }}
                            className="border-t border-border overflow-hidden"
                            style={{ height: NODE_H_IMAGE }}
                          >
                            {node.imageUrl ? (
                              <img
                                src={node.imageUrl}
                                alt={node.label}
                                className="w-full h-full object-cover"
                                draggable={false}
                              />
                            ) : (
                              <div className="w-full h-full flex flex-col items-center justify-center gap-2"
                                style={{ background: "rgba(255,255,255,0.02)" }}>
                                <ImageOff size={18} className="text-muted-foreground opacity-40" />
                                <span
                                  className="text-[10px] text-muted-foreground opacity-50"
                                  style={{ fontFamily: "'JetBrains Mono', monospace" }}
                                >
                                  no image
                                </span>
                              </div>
                            )}
                          </motion.div>
                        )}
                      </AnimatePresence>

                      {/* ── Expand toggle strip ── */}
                      <button
                        data-node
                        className="shrink-0 flex items-center justify-center border-t border-border transition-colors duration-150 hover:bg-white/[0.03]"
                        style={{ height: 22 }}
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleCard(node.id);
                        }}
                        aria-label={isCardEx ? "Hide image" : "Show image"}
                      >
                        <ChevronDown
                          size={10}
                          className="text-muted-foreground"
                          style={{
                            transform: isCardEx ? "rotate(180deg)" : "rotate(0deg)",
                            transition: "transform 0.22s ease",
                          }}
                        />
                      </button>
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        </div>

        {/* ── Status bar ── */}
        <footer
          className="shrink-0 flex items-center justify-between border-t border-border px-5 h-7 text-[11px] text-muted-foreground"
          style={{ fontFamily: "'JetBrains Mono', monospace" }}
        >
          <div className="flex items-center gap-3">
            <span className="tabular-nums">
              x:{Math.round(-pan.x)}&nbsp;&nbsp;y:{Math.round(-pan.y)}
            </span>
            {selected && byId.has(selected) && (
              <>
                <span className="opacity-30">·</span>
                <span style={{ color: "#22d3ee" }}>{byId.get(selected)!.label}</span>
                <span style={{ color: TYPE_CONFIG[byId.get(selected)!.type].dot }} className="opacity-70">
                  {TYPE_CONFIG[byId.get(selected)!.type].label}
                </span>
              </>
            )}
          </div>
          <span>drag to pan&nbsp;&nbsp;·&nbsp;&nbsp;click to select&nbsp;&nbsp;·&nbsp;&nbsp;▸ children&nbsp;&nbsp;·&nbsp;&nbsp;∨ image</span>
        </footer>
      </div>
    </>
  );
}
