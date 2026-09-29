import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  BrainCircuit,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleDashed,
  Clock3,
  Database,
  FileText,
  Gauge,
  Home,
  Lightbulb,
  Loader2,
  MessageSquareText,
  MessageCircle,
  Network,
  Play,
  Plus,
  RefreshCw,
  Send,
  ShieldAlert,
  Sparkles,
  Target,
  Trash2,
  UserRound,
  Users,
} from "lucide-react";

const API = "";
const today = new Date().toISOString().slice(0, 10);

type Evidence = {
  memory_id?: string | null;
  text: string;
  source_chunk?: string | null;
  date?: string | null;
  relevance?: number | null;
  feature_that_used_it: string;
};
type Operation = { status: string; operation: string; trace_id?: string | null; message?: string | null };
type MemoryResponse = { query: string; count: number; memories: Evidence[] };
type Deal = { id: string; name: string; company: string; contact_name?: string | null; location?: string | null; stage: string; value?: number | null; decision_date?: string | null };
type PromiseDebt = { score: number; level: "low" | "medium" | "high"; explanation: string; recommended_remediation: string; affected_commitments: Array<{ text: string; status: string; due_date?: string | null; related_objection?: string | null; evidence: Evidence[] }>; supporting_memories: Evidence[] };
type Stakeholder = { name: string; role: string; influence: string; sentiment: string; priority: string; concerns: string[]; relationship_status: string; evidence: Evidence[] };
type StakeholderResponse = { stakeholders: Stakeholder[]; recommended_next_contact?: string | null; rationale?: string | null };
type Simulation = { proposed_action: string; possible_benefits: string[]; risks: string[]; stakeholder_reactions: string[]; recommended_alternative: string; recommended_sequence: string[]; confidence: string; supporting_memories: Evidence[]; limitations: string[]; reflection: string };
type Replay = { label: string; answer: string; supporting_memories: Evidence[]; memory_count?: number; reflect_memory_count?: number };
type ConversationTurn = { role: "inbound" | "outbound"; text: string; evidence?: Evidence[] };
type View = "home" | "clients" | "promise" | "time-machine" | "stakeholders" | "outcomes" | "replay";

const featureMeta: Record<Exclude<View, "home">, { label: string; title: string; description: string }> = {
  clients: { label: "CLIENTS", title: "Your clients", description: "Add, remove, and open a client workspace so every conversation stays connected to the right person." },
  promise: { label: "FOLLOW-UP RISKS", title: "Follow-up risks", description: "See which promises need attention, what they affect, and the next step to keep the client confident." },
  "time-machine": { label: "TRY A NEXT STEP", title: "Try the next step", description: "Check a plan against earlier client concerns before you make the call." },
  stakeholders: { label: "PEOPLE INVOLVED", title: "People involved", description: "See who matters to this client, what they care about, and who to contact next." },
  outcomes: { label: "WHAT HAPPENED", title: "What happened", description: "Record the client's response so future advice gets better over time." },
  replay: { label: "COMPARE ANSWERS", title: "Compare answers", description: "See the difference between a general answer and one informed by this client's past conversations." },
};

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, { headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) }, ...init });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body?.error?.message ?? "The request failed.");
  return body as T;
}

function friendlyFeatureLabel(value: string): string {
  if (value.includes("promise")) return "follow-up check";
  if (value.includes("stakeholder")) return "people involved";
  if (value.includes("time machine")) return "next-step check";
  if (value.includes("briefing")) return "client coaching";
  if (value.includes("replay")) return "answer comparison";
  if (value.includes("memory")) return "past conversation";
  return "client note";
}

function EvidenceList({ items, compact = false }: { items: Evidence[]; compact?: boolean }) {
  if (!items.length) return <div className="empty">No matching past notes yet.</div>;
  return <div className={compact ? "evidence-list compact" : "evidence-list"}>
    {items.slice(0, compact ? 3 : 6).map((item, index) => (
      <div className="evidence" key={`${item.memory_id ?? "memory"}-${index}`}>
        <div className="evidence-meta"><span>PAST NOTE</span><span>{friendlyFeatureLabel(item.feature_that_used_it)}</span></div>
        <p>{item.text}</p>
        {item.source_chunk && <div className="source">Source: {item.source_chunk.slice(0, 180)}{item.source_chunk.length > 180 ? "..." : ""}</div>}
      </div>
    ))}
  </div>;
}

function SectionTitle({ eyebrow, title, icon }: { eyebrow: string; title: string; icon: React.ReactNode }) {
  return <div className="section-title"><div className="icon-wrap">{icon}</div><div><div className="eyebrow">{eyebrow}</div><h2>{title}</h2></div></div>;
}

function App() {
  const [view, setView] = useState<View>(() => {
    const value = window.location.hash.replace("#", "") as View;
    return value in featureMeta || value === "home" ? value : "home";
  });
  const [prospects, setProspects] = useState<Deal[]>([]);
  const [selectedDealId, setSelectedDealId] = useState("");
  const [deal, setDeal] = useState<Deal | null>(null);
  const [memories, setMemories] = useState<MemoryResponse | null>(null);
  const [promise, setPromise] = useState<PromiseDebt | null>(null);
  const [stakeholders, setStakeholders] = useState<StakeholderResponse | null>(null);
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [before, setBefore] = useState<Replay | null>(null);
  const [after, setAfter] = useState<Replay | null>(null);
  const [memoryQuery, setMemoryQuery] = useState("What happened in earlier conversations?");
  const [replayQuestion, setReplayQuestion] = useState("Prepare me for my next call with Acme Logistics.");
  const [action, setAction] = useState("I want to offer a 20% discount. Should I?");
  const [toast, setToast] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [seeded, setSeeded] = useState(false);
  const [interaction, setInteraction] = useState({ content: "", type: "meeting", date: today, source: "" });
  const [outcome, setOutcome] = useState({ action: "", result: "positive response", notes: "", date: new Date().toISOString().slice(0, 16) });
  const [showProspectForm, setShowProspectForm] = useState(false);
  const [newProspect, setNewProspect] = useState({ contactName: "", company: "", location: "" });
  const [conversationInput, setConversationInput] = useState("");
  const [conversation, setConversation] = useState<ConversationTurn[]>([]);

  const navigate = (nextView: View) => {
    setView(nextView);
    window.history.replaceState(null, "", nextView === "home" ? "#home" : `#${nextView}`);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const run = async <T,>(key: string, work: () => Promise<T>, onDone: (value: T) => void) => {
    setLoading((current) => ({ ...current, [key]: true }));
    try { onDone(await work()); } catch (error) { setToast({ kind: "error", text: error instanceof Error ? error.message : "Something went wrong." }); } finally { setLoading((current) => ({ ...current, [key]: false })); }
  };

  const loadProspects = async () => {
    await run("prospects", () => api<Deal[]>("/api/deals"), (list) => {
      setProspects(list);
      if (!selectedDealId || !list.some((item) => item.id === selectedDealId)) {
        setSelectedDealId(list.find((item) => item.id === "acme-logistics")?.id ?? list[0]?.id ?? "");
      }
    });
  };

  const refresh = async () => {
    if (!selectedDealId) return;
    await run("refresh", async () => {
      const [currentDeal, currentMemories, currentPromise, currentStakeholders] = await Promise.all([
        api<Deal>(`/api/deals/${selectedDealId}`),
        api<MemoryResponse>(`/api/deals/${selectedDealId}/memories?query=${encodeURIComponent(memoryQuery)}`),
        api<PromiseDebt>(`/api/deals/${selectedDealId}/promise-debt`),
        api<StakeholderResponse>(`/api/deals/${selectedDealId}/stakeholders`),
      ]);
      return { currentDeal, currentMemories, currentPromise, currentStakeholders };
    }, (value) => { setDeal(value.currentDeal); setMemories(value.currentMemories); setPromise(value.currentPromise); setStakeholders(value.currentStakeholders); });
  };

  useEffect(() => { loadProspects().catch(() => undefined); }, []);
  useEffect(() => {
    const onHashChange = () => {
      const value = window.location.hash.replace("#", "") as View;
      if (value === "home" || value in featureMeta) setView(value);
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);
  useEffect(() => {
    if (selectedDealId) {
      setConversation([]);
      setConversationInput("");
      refresh().catch(() => undefined);
    }
  }, [selectedDealId]);

  const seed = async () => {
    await run("seed", () => api<{ message: string }>("/api/demo/seed", { method: "POST" }), (value) => { setSeeded(true); setSelectedDealId("acme-logistics"); setToast({ kind: "success", text: value.message }); loadProspects(); });
  };

  const createProspect = async (event: FormEvent) => {
    event.preventDefault();
    if (!newProspect.contactName.trim() || !newProspect.company.trim()) return;
    await run("createProspect", () => api<Deal>("/api/deals", { method: "POST", body: JSON.stringify({ name: newProspect.contactName, company: newProspect.company, contact_name: newProspect.contactName, location: newProspect.location || null, stage: "new prospect" }) }), (created) => {
      setProspects((current) => [created, ...current]);
      setSelectedDealId(created.id);
      setNewProspect({ contactName: "", company: "", location: "" });
      setShowProspectForm(false);
      setToast({ kind: "success", text: `${created.company} added to your clients.` });
    });
  };

  const deleteProspect = async (prospect: Deal) => {
    if (!window.confirm(`Remove ${prospect.company} from your clients?`)) return;
    await run("deleteProspect", () => api<{ message: string }>(`/api/deals/${prospect.id}`, { method: "DELETE" }), () => {
      const remaining = prospects.filter((item) => item.id !== prospect.id);
      setProspects(remaining);
      if (selectedDealId === prospect.id) setSelectedDealId(remaining[0]?.id ?? "");
      setToast({ kind: "success", text: `${prospect.company} removed from your clients.` });
    });
  };

  const submitInteraction = async (event: FormEvent) => {
    event.preventDefault();
    if (!interaction.content.trim()) return;
    await run("interaction", () => api<{ operation: Operation }>(`/api/deals/${selectedDealId}/interactions`, { method: "POST", body: JSON.stringify({ content: interaction.content, interaction_date: interaction.date, interaction_type: interaction.type, source: interaction.source || null, participants: [] }) }), () => { setToast({ kind: "success", text: "Client note saved." }); setInteraction({ ...interaction, content: "" }); refresh(); });
  };

  const searchMemories = async (event: FormEvent) => { event.preventDefault(); await run("memories", () => api<MemoryResponse>(`/api/deals/${selectedDealId}/memories?query=${encodeURIComponent(memoryQuery)}`), setMemories); };
  const simulate = async (event: FormEvent) => { event.preventDefault(); await run("simulate", () => api<Simulation>(`/api/deals/${selectedDealId}/simulate`, { method: "POST", body: JSON.stringify({ proposed_action: action }) }), (value) => { setSimulation(value); setToast({ kind: "success", text: `Plan checked against ${value.supporting_memories.length} past notes.` }); }); };
  const replay = async () => {
    await run("replay", async () => { const [without, withMemory] = await Promise.all([api<Replay>("/api/demo/before-memory", { method: "POST", body: JSON.stringify({ question: replayQuestion }) }), api<Replay>("/api/demo/after-memory", { method: "POST", body: JSON.stringify({ deal_id: selectedDealId, question: replayQuestion }) })]); return { without, withMemory }; }, (value) => { setBefore(value.without); setAfter(value.withMemory); setToast({ kind: "success", text: `Compared a general answer with ${value.withMemory.memory_count ?? value.withMemory.supporting_memories.length} past notes.` }); });
  };
  const submitOutcome = async (event: FormEvent) => { event.preventDefault(); await run("outcome", () => api<{ operation: Operation }>(`/api/deals/${selectedDealId}/outcomes`, { method: "POST", body: JSON.stringify({ action: outcome.action, outcome: outcome.result, notes: outcome.notes, occurred_at: new Date(outcome.date).toISOString() }) }), () => { setToast({ kind: "success", text: "Client response saved." }); setOutcome({ ...outcome, action: "", notes: "" }); refresh(); }); };

  const sendConversation = async (event: FormEvent) => {
    event.preventDefault();
    if (!conversationInput.trim() || !selectedDealId) return;
    const inbound = conversationInput.trim();
    setConversation((current) => [...current, { role: "inbound", text: inbound }]);
    setConversationInput("");
    await run("conversation", () => api<{ outbound: string; retain_operation: Operation; reflect_memory_count: number; supporting_memories: Evidence[] }>(`/api/deals/${selectedDealId}/conversation`, { method: "POST", body: JSON.stringify({ content: inbound, interaction_date: today }) }), (value) => {
      setConversation((current) => [...current, { role: "outbound", text: value.outbound, evidence: value.supporting_memories }]);
      setToast({ kind: "success", text: `Your question was saved and answered using ${value.reflect_memory_count} past notes.` });
      refresh();
    });
  };

  const memoryCount = memories?.count ?? 0;
  const dealStatus = deal ? `${deal.stage} · decision ${deal.decision_date ?? "not set"}` : "Connect to the backend to load a deal";
  const promiseTone = promise?.level ?? "low";
  const riskBars = useMemo(() => {
    const commitments = promise?.affected_commitments ?? [];
    const total = Math.max(commitments.length, 1);
    const overdue = commitments.filter((item) => item.status === "overdue").length;
    const concerns = commitments.filter((item) => item.related_objection).length;
    return [
      { label: "Overall risk", chartLabel: "Overall", value: promise?.score ?? 0, detail: promise ? `${promise.score}/100` : "No data", tone: promiseTone },
      { label: "Overdue follow-ups", chartLabel: "Overdue", value: Math.round((overdue / total) * 100), detail: `${overdue}`, tone: "danger" },
      { label: "Client concerns", chartLabel: "Concerns", value: Math.round((concerns / total) * 100), detail: `${concerns}`, tone: "accent2" },
    ];
  }, [promise, promiseTone]);
  const riskChart = useMemo(() => {
    const left = 42;
    const right = 580;
    const top = 22;
    const bottom = 168;
    const points = riskBars.map((bar, index) => ({ ...bar, x: left + (index * (right - left)) / Math.max(riskBars.length - 1, 1), y: bottom - (bar.value / 100) * (bottom - top) }));
    const linePath = points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`).join(" ");
    const lastPoint = points[points.length - 1];
    const areaPath = `M ${points[0].x} ${bottom} ${points.map((point) => `L ${point.x} ${point.y}`).join(" ")} L ${lastPoint.x} ${bottom} Z`;
    const grid = [0, 25, 50, 75, 100].map((value) => ({ value, y: bottom - (value / 100) * (bottom - top) }));
    return { points, linePath, areaPath, grid };
  }, [riskBars]);
  const uniqueRoles = useMemo(() => stakeholders?.stakeholders.filter((item) => item.role !== "unknown").length ?? 0, [stakeholders]);
  const activeFeature = view === "home" ? null : featureMeta[view];

  return <div className={`app-shell view-${view}`}>
    <video className="ambient-video" autoPlay muted loop playsInline preload="auto" aria-hidden="true">
      <source src="/business-meeting.mp4" type="video/mp4" />
    </video>
    <div className="ambient-wash" aria-hidden="true" />
    <header className="topbar">
      <div className="brand"><div className="brand-mark"><BrainCircuit size={19} /></div><div><div className="brand-name">DealTwin</div><div className="tagline">Your client history, ready for the next call.</div></div></div>
      <div className="header-actions"><div className="connection"><span className={`status-dot ${deal ? "online" : "offline"}`} />{deal ? "Ready to help" : "Connecting..."}</div><button className="button secondary" onClick={seed} disabled={loading.seed}><Database size={15} />{loading.seed ? "Loading..." : seeded ? "Sample loaded" : "Load sample client"}</button></div>
    </header>
    <div className="workspace-layout">
      <aside className="prospect-sidebar">
        <nav className="view-nav" aria-label="DealTwin features">
          <span className="view-nav-label">WORKSPACE</span>
          <button className={`view-nav-button ${view === "home" ? "active" : ""}`} onClick={() => navigate("home")}><Home size={15} />Overview</button>
          <button className={`view-nav-button ${view === "clients" ? "active" : ""}`} onClick={() => navigate("clients")}><Users size={15} />Your clients</button>
          <button className={`view-nav-button ${view === "promise" ? "active" : ""}`} onClick={() => navigate("promise")}><Gauge size={15} />Follow-up risks</button>
          <button className={`view-nav-button ${view === "time-machine" ? "active" : ""}`} onClick={() => navigate("time-machine")}><Clock3 size={15} />Try a next step</button>
          <button className={`view-nav-button ${view === "stakeholders" ? "active" : ""}`} onClick={() => navigate("stakeholders")}><Users size={15} />People involved</button>
          <button className={`view-nav-button ${view === "outcomes" ? "active" : ""}`} onClick={() => navigate("outcomes")}><Check size={15} />What happened</button>
          <button className={`view-nav-button ${view === "replay" ? "active" : ""}`} onClick={() => navigate("replay")}><RefreshCw size={15} />Compare answers</button>
        </nav>
        <div className="sidebar-footer"><div className="eyebrow">HOW IT HELPS</div><p>Save what clients say, find it later, and get a clearer next step before every call.</p></div>
      </aside>
      <main>
      {activeFeature && <section className="feature-hero"><div><div className="eyebrow">{activeFeature.label}</div><h1>{activeFeature.title}</h1><p className="hero-copy">{activeFeature.description}</p></div><button className="button secondary" onClick={() => navigate("home")}><Home size={15} />Back to overview</button></section>}
      {view === "clients" && <section className="panel clients-page"><div className="clients-page-toolbar"><div><div className="eyebrow">CLIENT DIRECTORY</div><h2>Choose a client to continue</h2><p>Keep each conversation, note, and next step together in one client workspace.</p></div><button className="button primary" onClick={() => setShowProspectForm((current) => !current)}><Plus size={15} />Add client</button></div>{showProspectForm && <form className="prospect-form client-form" onSubmit={createProspect}><input required placeholder="Contact name" value={newProspect.contactName} onChange={(event) => setNewProspect({ ...newProspect, contactName: event.target.value })} /><input required placeholder="Company" value={newProspect.company} onChange={(event) => setNewProspect({ ...newProspect, company: event.target.value })} /><input placeholder="Location" value={newProspect.location} onChange={(event) => setNewProspect({ ...newProspect, location: event.target.value })} /><div className="prospect-form-actions"><button className="button primary" disabled={loading.createProspect}>Create</button><button type="button" className="button ghost" onClick={() => setShowProspectForm(false)}>Cancel</button></div></form>}<div className="client-grid">{prospects.map((prospect) => { const active = prospect.id === selectedDealId; const initials = (prospect.contact_name ?? prospect.name ?? prospect.company).split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase(); return <article className={`client-card ${active ? "active" : ""}`} key={prospect.id}><div className="client-card-top"><div className="prospect-avatar">{initials}</div><button className="prospect-delete" title={`Delete ${prospect.company}`} aria-label={`Delete ${prospect.company}`} onClick={() => deleteProspect(prospect)} disabled={loading.deleteProspect}><Trash2 size={15} /></button></div><h3>{prospect.contact_name ?? prospect.name}</h3><p className="client-card-company">{prospect.company}</p>{prospect.location && <p className="client-card-location">{prospect.location}</p>}<div className="client-card-footer"><span>{active ? "Currently selected" : "Ready to open"}</span><button className="button secondary" onClick={() => { setSelectedDealId(prospect.id); navigate("home"); }}>Open workspace <ChevronRight size={14} /></button></div></article>; })}{!prospects.length && <div className="client-empty"><Users size={20} /><div><strong>No clients yet</strong><p>Add your first client to start saving conversations.</p></div></div>}</div></section>}
      <section className="hero-row"><div><div className="eyebrow">CLIENT CONVERSATION WORKSPACE</div><h1>Know the client<br /><span>before the next call.</span></h1><p className="hero-copy">Save conversations, find the important details from earlier calls, and get a practical suggestion for what to say next.</p></div><div className="hero-signal"><div className="signal-label"><Sparkles size={15} /> WHAT WE KNOW</div><div className="signal-value">{memoryCount ? `${memoryCount} past notes` : "No notes yet"}</div><div className="signal-note">{memoryCount ? "Earlier client conversations are ready." : "Add the first conversation to get started."}</div></div></section>

      <section className="deal-strip panel"><div className="deal-identity"><div className="company-avatar">{(deal?.company ?? "Prospect").slice(0, 2).toUpperCase()}</div><div><div className="eyebrow">ACTIVE DEAL</div><h2>{deal?.company ?? "Select a prospect"}</h2><div className="deal-meta">{deal?.contact_name ? `${deal.contact_name} · ` : ""}{dealStatus}</div></div></div><div className="stat-cluster"><div><span>Memories</span><strong>{memoryCount}</strong></div><div><span>Stakeholders</span><strong>{stakeholders?.stakeholders.length ?? 0}</strong></div><div><span>Role signals</span><strong>{uniqueRoles}</strong></div><div><span>Promise Debt</span><strong className={`tone-${promiseTone}`}>{promise ? `${promise.score}` : "--"}</strong></div></div></section>

      {toast && <div className={`toast ${toast.kind}`}><span>{toast.kind === "success" ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}</span>{toast.text}<button aria-label="Dismiss" onClick={() => setToast(null)}>×</button></div>}

      <section className="panel conversation-panel"><div className="section-heading-row"><SectionTitle eyebrow="CLIENT COACHING CHAT" title={`Ask about ${deal?.contact_name ?? deal?.company ?? "this prospect"}`} icon={<MessageSquareText size={18} />} /><div className="operation-pill"><span className="status-dot online" />Retains every turn</div></div><p className="section-copy">Ask what happened before, what matters now, or how to talk with this client next. DealTwin responds from remembered conversations.</p><div className="conversation-feed">{conversation.length ? conversation.map((turn, index) => <div className={`conversation-turn ${turn.role}`} key={`${turn.role}-${index}`}><div className="turn-label">{turn.role === "inbound" ? "YOU / PROSPECT NOTE" : "DEALTWIN / MEMORY RESPONSE"}</div><p>{turn.text}</p>{turn.role === "outbound" && turn.evidence?.length ? <div className="turn-evidence"><Sparkles size={13} />{turn.evidence.length} memory facts used</div> : null}</div>) : <div className="conversation-empty"><MessageCircle size={20} /><span>Ask for a next-call recommendation, an objection response, or a recap.</span></div>}</div><form className="conversation-composer" onSubmit={sendConversation}><textarea value={conversationInput} onChange={(event) => setConversationInput(event.target.value)} placeholder="Ask DealTwin how to approach the client..." disabled={!selectedDealId} /><button className="button primary" disabled={loading.conversation || !selectedDealId}><Send size={15} />{loading.conversation ? "Thinking..." : "Ask DealTwin"}</button></form><div className="conversation-foot"><span><span className="status-dot online" />Incoming messages go to Hindsight retain</span><span>Outbound response uses reflect</span></div></section>

      {view === "time-machine" && <section className="panel friendly-time-machine"><SectionTitle eyebrow="TRY A NEXT STEP" title="What could happen next?" icon={<Clock3 size={18} />} /><p className="section-copy">Describe a plan and see the possible upside, risks, and a safer way to start based on earlier client conversations.</p><form className="action-row" onSubmit={simulate}><input value={action} onChange={(event) => setAction(event.target.value)} /><button className="button primary" disabled={loading.simulate}><Play size={15} />{loading.simulate ? "Checking..." : "Check this plan"}</button></form>{simulation && <div className="simulation-result"><div className="result-banner"><div><div className="eyebrow">WHAT MAY HAPPEN · {simulation.confidence.toUpperCase()} CONFIDENCE</div><h3>{simulation.proposed_action}</h3></div><div className="reflect-badge"><Sparkles size={14} /> Based on {simulation.supporting_memories.length} past notes</div></div><div className="tri-grid"><div><h4><Lightbulb size={15} /> Possible upside</h4>{simulation.possible_benefits.map((item) => <p key={item}>{item}</p>)}</div><div><h4><ShieldAlert size={15} /> Watch out for</h4>{simulation.risks.map((item) => <p key={item}>{item}</p>)}</div><div><h4><Users size={15} /> How people may respond</h4>{simulation.stakeholder_reactions.map((item) => <p key={item}>{item}</p>)}</div></div><div className="alternative"><div className="eyebrow">A BETTER FIRST STEP</div><p>{simulation.recommended_alternative}</p><div className="sequence">{simulation.recommended_sequence.map((item, index) => <span key={item}><b>{index + 1}</b>{item}</span>)}</div></div><details><summary>Show the reasoning and limits</summary><p className="reflection">{simulation.reflection}</p>{simulation.limitations.map((item) => <div className="limitation" key={item}><AlertTriangle size={14} />{item}</div>)}</details><div className="simulation-evidence"><div className="eyebrow">PAST NOTES USED</div><EvidenceList items={simulation.supporting_memories} compact /></div></div>}</section>}

      <div className="workspace-grid">
        <div className="main-column">
          <section className="panel capture-panel"><SectionTitle eyebrow="ADD A CLIENT NOTE" title="Save what the client said" icon={<Plus size={18} />} /><p className="section-copy">Paste a meeting note, call summary, email, or transcript. DealTwin saves it so you can use it in a later conversation.</p><form onSubmit={submitInteraction}><textarea value={interaction.content} onChange={(event) => setInteraction({ ...interaction, content: event.target.value })} placeholder="Paste the client conversation here..." /><div className="form-row"><select value={interaction.type} onChange={(event) => setInteraction({ ...interaction, type: event.target.value })}><option value="meeting">Meeting</option><option value="call">Call</option><option value="email">Email</option><option value="note">Note</option><option value="transcript">Transcript</option></select><input type="date" value={interaction.date} onChange={(event) => setInteraction({ ...interaction, date: event.target.value })} /><input placeholder="Where did this come from?" value={interaction.source} onChange={(event) => setInteraction({ ...interaction, source: event.target.value })} /><button className="button primary" disabled={loading.interaction}><Send size={15} />{loading.interaction ? "Saving..." : "Save this note"}</button></div></form></section>

          <section className="panel memory-panel"><div className="section-heading-row"><SectionTitle eyebrow="PAST CONVERSATIONS" title="What happened before" icon={<Database size={18} />} /><div className="operation-pill"><span className="status-dot online" />Past notes</div></div><form className="search-row" onSubmit={searchMemories}><input value={memoryQuery} onChange={(event) => setMemoryQuery(event.target.value)} /><button className="icon-button" title="Search past conversations" disabled={loading.memories}>{loading.memories ? <Loader2 className="spin" size={17} /> : <ArrowRight size={17} />}</button></form><div className="recall-line"><span>Found <strong>{memoryCount}</strong> past notes</span><span>These notes explain the answer</span></div><EvidenceList items={memories?.memories ?? []} /></section>

          <section className="panel time-machine"><SectionTitle eyebrow="SIMULATE THE NEXT MOVE" title="Deal Time Machine" icon={<Clock3 size={18} />} /><p className="section-copy">Ask what could happen before you commit. Reflection is grounded in current-deal evidence and recalled outcomes.</p><form className="action-row" onSubmit={simulate}><input value={action} onChange={(event) => setAction(event.target.value)} /><button className="button primary" disabled={loading.simulate}><Play size={15} />{loading.simulate ? "Reflecting..." : "Simulate action"}</button></form>{simulation && <div className="simulation-result"><div className="result-banner"><div><div className="eyebrow">POSSIBLE OUTCOME · {simulation.confidence.toUpperCase()} CONFIDENCE</div><h3>{simulation.proposed_action}</h3></div><div className="reflect-badge"><Sparkles size={14} /> Reflect used {simulation.supporting_memories.length} facts</div></div><div className="tri-grid"><div><h4><Lightbulb size={15} /> Possible benefits</h4>{simulation.possible_benefits.map((item) => <p key={item}>{item}</p>)}</div><div><h4><ShieldAlert size={15} /> Likely risks</h4>{simulation.risks.map((item) => <p key={item}>{item}</p>)}</div><div><h4><Users size={15} /> Stakeholder reactions</h4>{simulation.stakeholder_reactions.map((item) => <p key={item}>{item}</p>)}</div></div><div className="alternative"><div className="eyebrow">RECOMMENDED ALTERNATIVE</div><p>{simulation.recommended_alternative}</p><div className="sequence">{simulation.recommended_sequence.map((item, index) => <span key={item}><b>{index + 1}</b>{item}</span>)}</div></div><details><summary>Show reflection and limitations</summary><p className="reflection">{simulation.reflection}</p>{simulation.limitations.map((item) => <div className="limitation" key={item}><AlertTriangle size={14} />{item}</div>)}</details><div className="simulation-evidence"><div className="eyebrow">SUPPORTING MEMORIES</div><EvidenceList items={simulation.supporting_memories} compact /></div></div>}</section>
        </div>

        <aside className="side-column">
          <section className={`panel promise-card ${promiseTone}`}>
            <div className="section-heading-row"><SectionTitle eyebrow="FOLLOW-UP RISKS" title="Promises that need attention" icon={<Gauge size={18} />} /><span className={`risk-badge ${promiseTone}`}>{promise?.level ?? "pending"}</span></div>
            <div className="debt-score"><strong>{promise?.score ?? "--"}</strong><span>/ 100</span><div className="risk-chart" role="img" aria-label="Follow-up risk profile line graph"><svg viewBox="0 0 620 224" preserveAspectRatio="none"><defs><linearGradient id="risk-area" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#087f6c" stopOpacity=".22" /><stop offset="100%" stopColor="#087f6c" stopOpacity="0" /></linearGradient></defs>{riskChart.grid.map((level) => <g key={level.value}><line className="risk-chart-grid" x1="42" y1={level.y} x2="580" y2={level.y} /><text className="risk-chart-y-label" x="2" y={level.y + 4}>{level.value}</text></g>)}<path className="risk-chart-area" d={riskChart.areaPath} fill="url(#risk-area)" /><path className="risk-chart-line" d={riskChart.linePath} fill="none" />{riskChart.points.map((point) => <g key={point.label}><circle className="risk-chart-point-ring" cx={point.x} cy={point.y} r="7" /><circle className="risk-chart-point" cx={point.x} cy={point.y} r="3.5" /><text className="risk-chart-point-label" x={point.x} y={point.y - 13} textAnchor="middle">{point.detail}</text><text className="risk-chart-x-label" x={point.x} y="201" textAnchor="middle">{point.chartLabel}</text></g>)}</svg><div className="risk-chart-note">Higher points need more attention</div></div></div>
            <p className="explanation">{promise?.explanation ?? "Add a client note first. DealTwin will point out promises, deadlines, and follow-ups that need attention."}</p>
            {promise?.affected_commitments.slice(0, 3).map((item) => <div className="commitment" key={item.text}><div className="commitment-status"><span className={`status-dot ${item.status === "overdue" ? "danger" : "warning"}`} />{item.status}</div><p>{item.text}</p>{item.related_objection && <span className="tag"><ShieldAlert size={12} />{item.related_objection}</span>}</div>)}
            <div className="remediation"><span>Suggested next step</span><p>{promise?.recommended_remediation ?? "Confirm who owns the next step and when it will be done."}</p></div>
          </section>

          <section className="panel stakeholder-panel"><SectionTitle eyebrow="PEOPLE INVOLVED" title="Who matters to this client" icon={<Network size={18} />} />{stakeholders?.stakeholders.length ? <div className="stakeholder-list">{stakeholders.stakeholders.map((person) => <div className="stakeholder" key={person.name}><div className="avatar"><UserRound size={16} /></div><div className="stakeholder-body"><div className="person-row"><strong>{person.name}</strong><span className={`mini-status ${person.relationship_status}`}>{person.relationship_status}</span></div><div className="role">{person.role} · {person.influence} influence</div><div className="priority"><Target size={12} />{person.priority}</div><div className="chips">{person.concerns.slice(0, 2).map((item) => <span key={item}>{item}</span>)}</div></div></div>)}</div> : <div className="empty">No people have been found in the saved conversations yet.</div>}{stakeholders?.rationale && <div className="next-contact"><div className="eyebrow">WHO TO CONTACT NEXT</div><strong>{stakeholders.recommended_next_contact}</strong><p>{stakeholders.rationale}</p></div>}</section>

          <section className="panel outcome-panel"><SectionTitle eyebrow="WHAT HAPPENED" title="Save the client's response" icon={<Check size={18} />} /><p className="section-copy">Record what the client said or did after a conversation. This helps DealTwin give better advice next time.</p><form onSubmit={submitOutcome}><input placeholder="What did you do?" value={outcome.action} onChange={(event) => setOutcome({ ...outcome, action: event.target.value })} /><div className="form-row"><select value={outcome.result} onChange={(event) => setOutcome({ ...outcome, result: event.target.value })}>{["positive response", "no response", "objection increased", "meeting scheduled", "deal advanced", "deal stalled", "deal won", "deal lost"].map((option) => <option key={option}>{option}</option>)}</select><input type="datetime-local" value={outcome.date} onChange={(event) => setOutcome({ ...outcome, date: event.target.value })} /></div><textarea placeholder="What did the client say or do?" value={outcome.notes} onChange={(event) => setOutcome({ ...outcome, notes: event.target.value })} /><button className="button secondary full" disabled={loading.outcome}><CheckCircle2 size={15} />{loading.outcome ? "Saving..." : "Save the response"}</button></form></section>
        </aside>
      </div>

      <section className="panel replay-panel"><div className="section-heading-row"><SectionTitle eyebrow="COMPARE ANSWERS" title="Does past context change the answer?" icon={<RefreshCw size={18} />} /><div className="replay-proof"><CircleDashed size={14} /> Same question, two answers</div></div><p className="section-copy">Compare a general answer with advice that uses the selected client's earlier conversations. This makes the value of saved context easy to see.</p><div className="replay-controls"><input value={replayQuestion} onChange={(event) => setReplayQuestion(event.target.value)} /><button className="button primary" onClick={replay} disabled={loading.replay}><RefreshCw size={15} />{loading.replay ? "Comparing..." : "Compare answers"}</button></div><div className="replay-grid"><div className="replay-card before"><div className="replay-label"><span className="number">01</span><span>GENERAL ANSWER</span></div>{before ? <><h3>{before.label}</h3><p>{before.answer}</p><div className="no-evidence"><CircleDashed size={14} />No client history used</div></> : <div className="replay-placeholder">Run the comparison to see a general answer.</div>}</div><div className="replay-card after"><div className="replay-label"><span className="number">02</span><span>CLIENT-SPECIFIC ANSWER</span></div>{after ? <><h3>{after.label}</h3><p>{after.answer}</p><div className="memory-proof"><CheckCircle2 size={14} />{after.memory_count ?? after.supporting_memories.length} past notes used</div><EvidenceList items={after.supporting_memories} compact /></> : <div className="replay-placeholder">Run the comparison to see advice based on this client.</div>}</div></div></section>
      </main>
    </div>
    <footer><span>DealTwin prototype</span><span>Save · Find · Ask · Improve</span></footer>
  </div>;
}

export default App;

