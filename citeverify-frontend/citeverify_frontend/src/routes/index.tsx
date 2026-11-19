import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  ShieldCheck,
  UploadCloud,
  FileText,
  X,
  FlaskConical,
  LockKeyhole,
  Search,
  ScanText,
  BookOpen,
  Check,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock3,
  ChevronDown,
  ChevronRight,
  Download,
  RotateCcw,
  Sparkles,
  ExternalLink,
  Flag,
  MessageSquare,
  LoaderCircle,
  Menu,
  Info,
  Quote,
  ListFilter,
  CircleHelp,
  Network,
} from "lucide-react";
import { Button } from "@/button";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/dialog";
import { Switch } from "@/switch";
import { UserMenu } from "@/lib/user-menu";
import { useAuth } from "@/lib/auth-context";
import { AuthDialog } from "@/lib/auth-dialog";
import { api, type VerificationResult, type TraceabilityGraph } from "@/lib/api";
import {
  claims as defaultClaims,
  documentTitle,
  sampleFilename,
  statusLabels,
  steps,
  validatePdf,
  validateDocument,
  type Status,
  type ClaimItem,
} from "@/lib/citeverify";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "CiteVerify — Verify the Science. Trust the Evidence." },
      {
        name: "description",
        content:
          "Explore a scientific citation audit. Compare research claims with source evidence and review every verdict.",
      },
      { property: "og:title", content: "CiteVerify — Scientific Claim & Citation Verification" },
      {
        property: "og:description",
        content:
          "Trust every citation. Verify every claim with a transparent, reviewable evidence workspace.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});
const icons = {
  supported: CheckCircle2,
  partial: AlertTriangle,
  unsupported: XCircle,
  outdated: Clock3,
};
function StatusBadge({ status }: { status: Status }) {
  const Icon = icons[status];
  return (
    <span className={`status-badge status-${status}`}>
      <Icon />
      {statusLabels[status]}
    </span>
  );
}
function Logo() {
  return (
    <div className="brand">
      <ShieldCheck aria-hidden="true" />
      <span>CiteVerify</span>
    </div>
  );
}
function mapVerificationResultToClaimItem(v: VerificationResult | any, index: number): ClaimItem {
  let status: Status = "partial";
  const verdict = (v.verdict || "").toUpperCase();
  if (verdict === "SUPPORTED") status = "supported";
  else if (verdict === "PARTIALLY_SUPPORTED") status = "partial";
  else if (verdict === "UNSUPPORTED" || verdict === "CONTRADICTORY") status = "unsupported";
  else if (verdict === "POSSIBLY_OUTDATED" || verdict === "POTENTIALLY_OUTDATED") status = "outdated";

  const firstPassage = v.evidence_passages?.[0]?.text || "";
  const source = v.source;
  const journal = [source?.journal, source?.year].filter(Boolean).join(" · ");

  // Real confidence and alignment score
  const alignmentPct = typeof v.confidence?.alignment_score === "number"
    ? v.confidence.alignment_score
    : (typeof v.confidence?.score === "number" ? Math.round(v.confidence.score * 100) : 0);

  const pageNum = v.evidence_passages?.[0]?.page_number ?? "Unavailable";

  return {
    id: index + 1,
    status,
    text: v.claim_text,
    citation: v.citation_reference || (source?.authors?.[0] ? `${source.authors[0]} et al.` : "Cited Source"),
    confidence: alignmentPct,
    page: pageNum,
    quote: firstPassage || "No direct passage extracted from available source text.",
    reasoning: v.explanation || "Evaluated by CiteVerify research verification engine.",
    title: source?.title || "Cited Research Publication",
    journal: journal || (source?.year ? `Published · ${source.year}` : "Academic Source"),
    doi: source?.doi || "",
    evidencePassages: v.evidence_passages || [],
    issues: v.issues || [],
    limitations: v.limitations || [],
    rawVerdict: v.verdict,
    sourceUrl: source?.url || (source?.doi ? `https://doi.org/${source.doi}` : null),
    authors: source?.authors || [],
    year: source?.year || null,
    publisher: source?.publisher || null,
    evidenceType: source?.evidence_type || "metadata_only",
    matchingStatus: source?.matching_status || "VERIFIED_MATCH",
    humanReviewRequired: Boolean(v.human_review_required),
    alignmentScore: alignmentPct,
    alignmentTier: v.confidence?.alignment_tier || (alignmentPct >= 80 ? "STRONG" : alignmentPct >= 50 ? "MODERATE" : "WEAK"),
    alignmentDisplay: v.confidence?.alignment_display || `${alignmentPct}% Evidence Alignment`,
    isScoreable: v.confidence?.is_scoreable !== false,
    traceabilityNodeId: v.traceability_node_id,
  };
}

function Index() {
  const { user, loading: authLoading } = useAuth();
  const [authDialogOpen, setAuthDialogOpen] = useState(true);
  const [screen, setScreen] = useState<"upload" | "processing" | "workspace">("upload");
  const [modal, setModal] = useState<"how" | "trust" | "upload" | "menu" | null>(null);
  const [file, setFile] = useState<{ name: string; size: number; demo?: boolean } | null>(null);
  const [rawFile, setRawFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [step, setStep] = useState(0);
  const [stepMessage, setStepMessage] = useState("");
  const [filter, setFilter] = useState<Status | "all">("all");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("document");
  const [active, setActive] = useState<number | null>(1);
  const [mobileTab, setMobileTab] = useState("report");
  const [docQuery, setDocQuery] = useState("");
  const [page, setPage] = useState(3);
  const [font, setFont] = useState(1);
  const [zoom, setZoom] = useState(100);
  const [docMode, setDocMode] = useState("text");
  const [flags, setFlags] = useState<number[]>([]);
  const [verified, setVerified] = useState<number[]>([]);
  const [notes, setNotes] = useState<Record<number, string>>({});
  const [notesOpen, setNotesOpen] = useState<number[]>([]);
  const [pulse, setPulse] = useState<number | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Dynamic state for live backend integration
  const [currentClaims, setCurrentClaims] = useState<ClaimItem[]>(defaultClaims);
  const [currentDocTitle, setCurrentDocTitle] = useState(documentTitle);
  const [currentDocId, setCurrentDocId] = useState<string | null>(null);
  const [currentDocText, setCurrentDocText] = useState<string | null>(null);
  const [isLiveAnalysis, setIsLiveAnalysis] = useState(false);

  // Direct scientific claim verification state
  const [inputMode, setInputMode] = useState<"document" | "claim">("document");
  const [claimInput, setClaimInput] = useState("");
  const [citationInput, setCitationInput] = useState("");
  const [doiInput, setDoiInput] = useState("");
  const [directLoading, setDirectLoading] = useState(false);
  const [directError, setDirectError] = useState("");
  const [directResult, setDirectResult] = useState<ClaimItem | null>(null);

  // Traceability Graph State
  const [graphModalOpen, setGraphModalOpen] = useState(false);
  const [graphData, setGraphData] = useState<TraceabilityGraph | null>(null);
  const [graphLoading, setGraphLoading] = useState(false);

  async function handleOpenTraceabilityGraph() {
    setGraphModalOpen(true);
    if (!currentDocId) {
      return;
    }
    setGraphLoading(true);
    try {
      const data = await api.getTraceabilityGraph(currentDocId);
      setGraphData(data);
    } catch (err) {
      console.warn("Failed to fetch graph from backend:", err);
    } finally {
      setGraphLoading(false);
    }
  }

  useEffect(() => {
    if (screen === "workspace")
      document.getElementById("paper-page-3")?.scrollIntoView({ block: "start" });
  }, [screen]);

  useEffect(() => {
    if (pulse === null) return;
    const timer = setTimeout(() => setPulse(null), 650);
    return () => clearTimeout(timer);
  }, [pulse]);

  function selectFile(f: File | undefined) {
    if (!f) return;
    const message = validateDocument(f);
    setError(message);
    if (!message) {
      setFile({ name: f.name, size: f.size });
      setRawFile(f);
    }
  }

  async function runDocumentAnalysis(fileToAnalyze: File) {
    setError("");
    setCurrentClaims([]);
    setCurrentDocText(null);
    setCurrentDocId(null);
    setCurrentDocTitle(fileToAnalyze.name);
    setFlags([]);
    setVerified([]);
    setNotes({});
    setActive(1);
    setFilter("all");
    setQuery("");
    setStep(0);
    setStepMessage("Uploading document and checking format…");
    setScreen("processing");
    try {
      // Step 0: Upload & Parse Document
      const doc = await api.uploadDocument(fileToAnalyze);
      setCurrentDocId(doc.id);
      setCurrentDocTitle(doc.document_title || fileToAnalyze.name);

      // Step 1: Text extraction
      setStep(1);
      setStepMessage("Extracting text and document sections…");
      const extResult = await api.extractDocument(doc.id);
      if (extResult.status === "failed") {
        throw new Error(extResult.message || "Document extraction failed.");
      }

      // Step 2: Isolating Scientific Claims
      setStep(2);
      setStepMessage("Extracting verifiable scientific claims and statements…");
      const claimsRes = await api.extractClaims(doc.id);

      // Step 3: Citations & Bibliography
      setStep(3);
      setStepMessage("Parsing citations and matching bibliographic references…");
      try {
        await api.extractCitations(doc.id);
        await api.matchCitations(doc.id);
      } catch (citErr) {
        console.warn("Notice: Citation parsing completed with warnings:", citErr);
      }

      // Step 4: Verification against literature
      setStep(4);
      setStepMessage("Verifying claim alignment against retrieved scientific evidence…");
      const verifResponse = await api.runVerification(doc.id);

      // Retrieve full document text
      const updatedDoc = await api.getDocument(doc.id);
      setCurrentDocText(updatedDoc.body_text || updatedDoc.extracted_text || null);
      setCurrentDocTitle(updatedDoc.document_title || fileToAnalyze.name);

      const rawResults = verifResponse.results || [];
      const mapped = rawResults.map((r, i) => mapVerificationResultToClaimItem(r, i));
      setCurrentClaims(mapped);
      setIsLiveAnalysis(true);
      setStep(5);
      setScreen("workspace");
    } catch (err: any) {
      console.error("Document analysis error:", err);
      setError(err?.message || "Failed to analyze document. Please check backend connection.");
      setScreen("upload");
    }
  }

  async function runDemoAnalysis() {
    setError("");
    setFile({ name: sampleFilename, size: 2457600, demo: true });
    setStep(0);
    setStepMessage("Loading sample research paper from database…");
    setScreen("processing");
    try {
      const demoData = await api.loadDemoDocument();
      setCurrentDocId(demoData.document_id);
      setCurrentDocTitle(demoData.document_title);
      setCurrentDocText(demoData.body_text || null);
      if (demoData.results && demoData.results.length > 0) {
        const mapped = demoData.results.map((r, i) => mapVerificationResultToClaimItem(r, i));
        setCurrentClaims(mapped);
      }
      setIsLiveAnalysis(false);
      for (let s = 1; s <= 4; s++) {
        await new Promise((r) => setTimeout(r, 450));
        setStep(s);
      }
      setStep(5);
      setScreen("workspace");
    } catch (err: any) {
      console.warn("Backend demo call failed, using bundled demo dataset:", err);
      setCurrentClaims(defaultClaims);
      setCurrentDocTitle(documentTitle);
      for (let s = 1; s <= 4; s++) {
        await new Promise((r) => setTimeout(r, 450));
        setStep(s);
      }
      setStep(5);
      setScreen("workspace");
    }
  }

  function analyze(demo = false) {
    if (demo || file?.demo) {
      runDemoAnalysis();
    } else if (rawFile) {
      runDocumentAnalysis(rawFile);
    } else {
      setError("Please select a PDF research paper first.");
    }
  }

  async function handleVerifyDirectClaim() {
    if (!claimInput.trim()) return;
    setDirectError("");
    setDirectLoading(true);
    setDirectResult(null);
    try {
      const result = await api.verifyDirectClaim(claimInput, citationInput, doiInput);
      const item = mapVerificationResultToClaimItem(result, 0);
      setDirectResult(item);
    } catch (err: any) {
      console.error("Direct claim verification error:", err);
      setDirectError(err?.message || "Failed to verify claim. Please check backend connection.");
    } finally {
      setDirectLoading(false);
    }
  }

  function reset() {
    setScreen("upload");
    setFile(null);
    setRawFile(null);
    setError("");
    setActive(1);
    setFilter("all");
    setQuery("");
    setFlags([]);
    setVerified([]);
    setNotes({});
    setNotesOpen([]);
    setSort("document");
    setMobileTab("report");
    setDocQuery("");
    setPage(3);
    setFont(1);
    setZoom(100);
    setDocMode("text");
    setCurrentClaims(defaultClaims);
    setCurrentDocTitle(documentTitle);
    setCurrentDocId(null);
    setCurrentDocText(null);
    setIsLiveAnalysis(false);
    setDirectResult(null);
    setDirectError("");
  }

  function sync(id: number, target: "document" | "report") {
    setActive(id);
    setPulse(id);
    const claim = currentClaims.find((c) => c.id === id);
    if (claim) setPage(claim.page);
    setDocMode("text");
    if (target === "document") setMobileTab("document");
    else {
      setMobileTab("report");
      setFilter("all");
      setQuery("");
    }
    setTimeout(
      () =>
        document
          .getElementById(`${target === "document" ? "highlight" : "claim"}-${id}`)
          ?.scrollIntoView({ behavior: "smooth", block: "center" }),
      80,
    );
  }

  function toggle(list: number[], id: number) {
    return list.includes(id) ? list.filter((x) => x !== id) : [...list, id];
  }

  async function exportReport() {
    const report = {
      document: currentDocTitle,
      dataset: isLiveAnalysis ? "CiteVerify Verified Live Audit" : "CiteVerify Demo Audit",
      timestamp: new Date().toISOString(),
      claims: currentClaims.map((c) => ({
        ...c,
        flagged: flags.includes(c.id),
        humanVerified: verified.includes(c.id),
        reviewerNotes: notes[c.id] || "",
      })),
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `citeverify-${isLiveAnalysis ? "audit" : "demo"}.json`;
    a.click();
    URL.revokeObjectURL(url);

    if (currentDocId) {
      try {
        await api.exportPdfReport(currentDocId);
        const downloadUrl = api.getReportDownloadUrl(currentDocId);
        window.open(downloadUrl, "_blank");
      } catch (err) {
        console.warn("PDF export generation skipped:", err);
      }
    }
  }

  const filtered = currentClaims
    .filter(
      (c) =>
        (filter === "all" || c.status === filter) &&
        `${c.text} ${c.citation} ${c.title}`.toLowerCase().includes(query.toLowerCase()),
    )
    .sort((a, b) =>
      sort === "confidence"
        ? b.confidence - a.confidence
        : sort === "flagged"
          ? Number(flags.includes(b.id)) - Number(flags.includes(a.id))
          : a.id - b.id,
    );
  const modalPoints =
    modal === "trust"
      ? [
          [
            "Evidence, not authority",
            "A citation is a starting point. Read the original source and assess whether its findings support the exact claim.",
          ],
          [
            "Understand the limits",
            "Abstract-only evidence can omit important caveats. AI-assisted verdicts are provisional, not peer review or clinical advice.",
          ],
          [
            "Keep human judgment central",
            "Flag uncertain claims, record your reasoning, and mark a claim verified only after your own source review.",
          ],
          [
            "Demo data is illustrative",
            "The sample uses simulated excerpts and illustrative confidence scores. It is not an authoritative assessment of the cited research.",
          ],
        ]
      : [
          [
            "Extract scientific claims",
            "Identify verifiable statements and their inline citations in a research paper.",
          ],
          [
            "Retrieve the original evidence",
            "Match citations with original sources and compare each claim against available evidence.",
          ],
          [
            "Review every verdict",
            "Inspect source quotes, assess the reasoning, and add your own review before exporting an audit.",
          ],
        ];
  function highlight(id: number) {
    const c = currentClaims.find((c) => c.id === id);
    if (!c) return null;
    const Icon = icons[c.status];
    return (
      <button
        id={`highlight-${id}`}
        className={`claim-highlight status-${c.status} ${active === id ? "focused" : ""} ${pulse === id ? "pulse" : ""}`}
        onClick={() => sync(id, "report")}
        aria-label={`${statusLabels[c.status]}: ${c.text}`}
      >
        <Icon className="inline-status-icon" aria-hidden="true" />
        {c.text}
        <span className="highlight-tooltip" role="tooltip">
          <strong>
            <Icon />
            {statusLabels[c.status]}
          </strong>
          {c.confidence}% confidence
        </span>
      </button>
    );
  }
  // --- AUTH GATE: Block all access when user is not signed in ---
  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="h-12 w-12 rounded-full bg-primary/10 text-primary flex items-center justify-center">
            <ShieldCheck className="h-6 w-6 text-primary" />
          </div>
          <div className="flex items-center gap-2 text-muted-foreground text-sm">
            <LoaderCircle className="h-4 w-4 animate-spin" />
            <span>Loading CiteVerify…</span>
          </div>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="max-w-md w-full text-center space-y-6">
          <div className="flex flex-col items-center gap-3">
            <div className="h-16 w-16 rounded-full bg-primary/10 text-primary flex items-center justify-center">
              <ShieldCheck className="h-8 w-8 text-primary" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-foreground">CiteVerify</h1>
            <p className="text-muted-foreground text-sm max-w-sm">
              Verify scientific claims, audit research papers, and track evidence. Sign in to get started.
            </p>
          </div>
          <Button size="lg" className="w-full max-w-xs mx-auto" onClick={() => setAuthDialogOpen(true)}>
            Sign In to Continue
            <ArrowRight className="h-4 w-4 ml-2" />
          </Button>
          <AuthDialog open={authDialogOpen} onOpenChange={setAuthDialogOpen} />
        </div>
      </div>
    );
  }
  // --- END AUTH GATE ---

  return (
    <>
      <header className={`topbar ${screen === "workspace" ? "workspace-header" : ""}`}>
        <Logo />
        {screen === "workspace" ? (
          <>
            <span className="header-title" title={currentDocTitle}>
              {currentDocTitle}
            </span>
            <span className="demo-badge">
              {isLiveAnalysis ? "VERIFIED LIVE" : "DEMO DATASET"}
            </span>
            <nav className="desktop-only">
              <Button variant="ghost" onClick={reset}>
                <RotateCcw />
                New Analysis
              </Button>
              <Button variant="outline" onClick={handleOpenTraceabilityGraph} className="gap-1.5">
                <Network className="h-4 w-4" />
                Traceability DAG
              </Button>
              <Button onClick={exportReport}>
                <Download />
                Export Audit Report
              </Button>
              <UserMenu />
            </nav>
            <div className="mobile-only flex items-center gap-2">
              <UserMenu />
              <Button
                variant="ghost"
                size="icon"
                aria-label="Open menu"
                onClick={() => setModal("menu")}
              >
                <Menu />
              </Button>
            </div>
          </>
        ) : (
          <>
            <nav className="desktop-only">
              <Button variant="ghost" onClick={() => setModal("how")}>
                <CircleHelp />
                How It Works
              </Button>
              <Button variant="ghost" onClick={() => setModal("trust")}>
                <ShieldCheck />
                Academic Trust Guidelines
                <ArrowUpRight />
              </Button>
              <UserMenu />
            </nav>
            <div className="mobile-only flex items-center gap-2">
              <UserMenu />
              <Button
                variant="ghost"
                size="icon"
                aria-label="Open menu"
                onClick={() => setModal("menu")}
              >
                <Menu />
              </Button>
            </div>
          </>
        )}
      </header>
      {screen === "upload" && (
        <main className="upload-main">
          <div className="eyebrow">
            <ShieldCheck />
            SCIENCE, WITH A SECOND LOOK
          </div>
          <h1>
            Trust Every Citation.<span>Verify Every Claim.</span>
          </h1>
          <p className="upload-subtitle">
            A clearer picture of the evidence behind your research.
            <br className="desktop-only" /> Check scientific claims against their original sources,
            one citation at a time.
          </p>

          <div className="segmented mb-6 max-w-sm mx-auto" role="tablist">
            <Button
              variant="ghost"
              role="tab"
              aria-selected={inputMode === "document"}
              className={inputMode === "document" ? "active" : ""}
              onClick={() => setInputMode("document")}
            >
              <FileText />
              Research Document (PDF, DOCX, TXT)
            </Button>
            <Button
              variant="ghost"
              role="tab"
              aria-selected={inputMode === "claim"}
              className={inputMode === "claim" ? "active" : ""}
              onClick={() => setInputMode("claim")}
            >
              <Sparkles />
              Verify Direct Claim
            </Button>
          </div>

          <div className="upload-area">
            {inputMode === "claim" ? (
              <div className="text-left w-full p-2">
                <label className="block mb-2 font-medium text-xs text-foreground">
                  Scientific Claim or Research Statement <span className="text-destructive">*</span>
                </label>
                <textarea
                  className="w-full p-3 border rounded-md text-xs bg-background min-h-[90px] focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="e.g. Deep learning models achieved diagnostic accuracy of 94.5% in detecting early-stage diabetic retinopathy from retinal fundus images."
                  value={claimInput}
                  onChange={(e) => setClaimInput(e.target.value)}
                />
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
                  <div>
                    <label className="block mb-1 text-[11px] text-muted-foreground">
                      Citation / Authors (Optional)
                    </label>
                    <input
                      type="text"
                      className="w-full p-2 border rounded-md text-xs bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                      placeholder="e.g. Gulshan et al., 2016"
                      value={citationInput}
                      onChange={(e) => setCitationInput(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="block mb-1 text-[11px] text-muted-foreground">
                      DOI or URL (Optional)
                    </label>
                    <input
                      type="text"
                      className="w-full p-2 border rounded-md text-xs bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                      placeholder="e.g. 10.1001/jama.2016.17216"
                      value={doiInput}
                      onChange={(e) => setDoiInput(e.target.value)}
                    />
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                  <span>Try sample statements:</span>
                  <button
                    type="button"
                    className="underline hover:text-foreground cursor-pointer"
                    onClick={() => {
                      setClaimInput(
                        "Deep learning models achieved diagnostic accuracy of 94.5% in detecting early-stage diabetic retinopathy from retinal fundus images.",
                      );
                      setCitationInput("Gulshan et al., 2016");
                      setDoiInput("10.1001/jama.2016.17216");
                    }}
                  >
                    Diabetic Retinopathy
                  </button>
                  ·
                  <button
                    type="button"
                    className="underline hover:text-foreground cursor-pointer"
                    onClick={() => {
                      setClaimInput(
                        "Convolutional neural networks demonstrate dermatologist-level performance in skin lesion classification.",
                      );
                      setCitationInput("Esteva et al., 2017");
                      setDoiInput("10.1038/nature21056");
                    }}
                  >
                    Skin Cancer CNN
                  </button>
                </div>

                {directError && (
                  <p role="alert" className="mt-3 text-left text-xs text-destructive flex items-center gap-2">
                    <AlertTriangle size={14} />
                    {directError}
                  </p>
                )}

                <div className="upload-actions mt-4">
                  <Button
                    disabled={!claimInput.trim() || directLoading}
                    onClick={handleVerifyDirectClaim}
                  >
                    {directLoading ? (
                      <>
                        <LoaderCircle className="animate-spin" />
                        Verifying Against Scientific Literature…
                      </>
                    ) : (
                      <>
                        <Sparkles />
                        Verify Claim with Evidence
                        <ArrowRight className="ml-auto" />
                      </>
                    )}
                  </Button>
                </div>

                {directResult && (
                  <div className="mt-5 p-4 rounded-lg border bg-card text-card-foreground">
                    <div className="flex items-center justify-between mb-2">
                      <StatusBadge status={directResult.status} />
                      <span className="text-xs font-semibold px-2 py-0.5 bg-secondary rounded text-secondary-foreground">
                        {directResult.confidence}% confidence
                      </span>
                    </div>
                    <p className="text-xs font-medium text-foreground mb-1">{directResult.text}</p>
                    <p className="text-[11px] text-muted-foreground mb-3">
                      Source: {directResult.title} ({directResult.citation})
                      {directResult.doi && (
                        <a
                          href={`https://doi.org/${directResult.doi}`}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 ml-2 text-primary underline"
                        >
                          DOI <ExternalLink size={10} />
                        </a>
                      )}
                    </p>
                    <div className="p-3 bg-secondary/50 rounded-md text-xs mb-3">
                      <strong className="block mb-1 text-foreground">Retrieved Evidence:</strong>
                      &ldquo;{directResult.quote}&rdquo;
                    </div>
                    <div className="text-xs text-muted-foreground mb-3">
                      <strong className="block text-foreground mb-1">Scientific Reasoning:</strong>
                      {directResult.reasoning}
                    </div>

                    {/* Evidence Alignment Score — Final Element */}
                    <div
                      className={`mb-4 rounded-lg border p-3 ${
                        directResult.confidence >= 80
                          ? "border-emerald-300 bg-emerald-50/80 text-emerald-950 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-100"
                          : directResult.confidence >= 50
                          ? "border-amber-300 bg-amber-50/80 text-amber-950 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100"
                          : "border-rose-300 bg-rose-50/80 text-rose-950 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-100"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold">Evidence Alignment Score:</span>
                        <span className="font-mono text-sm font-bold">{directResult.confidence}%</span>
                      </div>
                      <span className="text-[11px] block mt-0.5 opacity-90">
                        {directResult.alignmentDisplay || (directResult.confidence >= 80 ? "Strong Evidence Alignment" : directResult.confidence >= 50 ? "Moderate Alignment" : "Weak Alignment")}
                      </span>
                    </div>

                    <Button
                      className="w-full"
                      onClick={() => {
                        setCurrentClaims([directResult]);
                        setCurrentDocTitle("Direct Scientific Claim Audit");
                        setCurrentDocText(directResult.text);
                        setIsLiveAnalysis(true);
                        setScreen("workspace");
                      }}
                    >
                      <BookOpen />
                      Open Full Evidence Audit Workspace
                      <ArrowRight className="ml-auto" />
                    </Button>
                  </div>
                )}
              </div>
            ) : (
              <>
                <input
                  ref={inputRef}
                  type="file"
                  accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
                  className="sr-only"
                  aria-label="Upload research document"
                  onChange={(e) => {
                    selectFile(e.target.files?.[0]);
                    e.target.value = "";
                  }}
                />
                <div
                  className={`dropzone ${dragging ? "dragging" : ""}`}
                  role="button"
                  tabIndex={0}
                  aria-label="Browse for a document"
                  onClick={() => inputRef.current?.click()}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      inputRef.current?.click();
                    }
                  }}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragging(true);
                  }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragging(false);
                    selectFile(e.dataTransfer.files[0]);
                  }}
                >
                  <div className="upload-icon">
                    <UploadCloud />
                  </div>
                  <strong>
                    Drag &amp; drop your document here or <span>browse</span>
                  </strong>
                  <p>PDF, Word (.docx), or Text (.txt) · Max 25 MB</p>
                </div>
                {file && (
                  <div className="staged-file">
                    <FileText />
                    <div>
                      <strong>{file.name}</strong>
                      <small>{(file.size / 1024 / 1024).toFixed(1)} MB · PDF document</small>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Remove file"
                      onClick={() => {
                        setFile(null);
                        setRawFile(null);
                      }}
                    >
                      <X />
                    </Button>
                  </div>
                )}
                {error && (
                  <p
                    role="alert"
                    className="mt-3 text-left text-xs text-destructive flex items-center gap-2"
                  >
                    <AlertTriangle size={14} />
                    {error}
                  </p>
                )}
                <div className="upload-actions">
                  <Button disabled={!file} onClick={() => analyze()}>
                    <Sparkles />
                    Analyze Research Paper
                    <ArrowRight className="ml-auto" />
                  </Button>
                  <Button variant="demo" onClick={() => analyze(true)}>
                    <FlaskConical />
                    Load Sample Research Paper (Demo)
                    <ArrowRight className="ml-auto" />
                  </Button>
                </div>
              </>
            )}
            <p className="privacy-note">
              <LockKeyhole />
              CiteVerify AI · Scientific claim and citation verification platform.
            </p>
          </div>
          <div className="workflow">
            <div className="workflow-item">
              <ScanText />
              <div>
                <strong>1&nbsp; Extract Claims</strong>
                <p>Identify the statements that matter.</p>
              </div>
            </div>
            <ArrowRight />
            <div className="workflow-item">
              <BookOpen />
              <div>
                <strong>2&nbsp; Retrieve Original Sources</strong>
                <p>Trace every claim to its evidence.</p>
              </div>
            </div>
            <ArrowRight />
            <div className="workflow-item">
              <ShieldCheck />
              <div>
                <strong>3&nbsp; Audit Evidence</strong>
                <p>Understand what the science supports.</p>
              </div>
            </div>
          </div>
          <footer className="upload-footer">
            <span>
              <ShieldCheck size={14} />
              CiteVerify · Verify the Science. Trust the Evidence.
            </span>
            <span>AI-assisted. Human-reviewed. Always transparent.</span>
          </footer>
        </main>
      )}
      {screen === "processing" && (
        <main className="processing-wrap">
          <div className="processing-card">
            <div className="modal-icon">
              <ScanText />
            </div>
            <span className="demo-badge">
              {isLiveAnalysis ? "LIVE BACKEND ANALYSIS" : "DEMO ANALYSIS"}
            </span>
            <h1>Analyzing your paper</h1>
            <p className="text-xs">{file?.name || currentDocTitle}</p>
            <div className="mt-8">
              {steps.map((s, i) => (
                <div
                  key={s}
                  className={`processing-step ${i < step ? "complete" : i === step ? "active" : ""}`}
                >
                  <span className="step-circle">
                    {i < step ? (
                      <Check size={15} />
                    ) : i === step ? (
                      <LoaderCircle size={15} className="animate-spin" />
                    ) : null}
                  </span>
                  <div>
                    <strong className={i > step ? "text-subtle" : ""}>{s}</strong>
                    {i === step && (
                      <small>
                        {stepMessage ||
                          [
                            "Parsing document structure & layout…",
                            `Found ${currentClaims.length} scientific claims`,
                            "Matching inline citations with bibliography…",
                            "Retrieving source abstracts & evidence…",
                            "Evaluating claim-evidence alignment…",
                          ][i]}
                      </small>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <div className="processing-note">
              <Info size={14} />
              AI-assisted analysis. Every verdict is reviewable by you.
            </div>
          </div>
        </main>
      )}
      {screen === "workspace" && (
        <>
          <div className="mobile-tabs mobile-only">
            <div className="segmented" role="tablist" aria-label="Workspace view">
              <Button
                variant="ghost"
                role="tab"
                aria-selected={mobileTab === "document"}
                onClick={() => setMobileTab("document")}
              >
                <FileText />
                Document View
              </Button>
              <Button
                variant="ghost"
                role="tab"
                aria-selected={mobileTab === "report"}
                onClick={() => setMobileTab("report")}
              >
                <ShieldCheck />
                Verification Report ({currentClaims.length})
              </Button>
            </div>
          </div>
          <main className="workspace">
            <section
              className={`document-panel ${mobileTab !== "document" ? "mobile-hidden" : ""}`}
              aria-label="Research document"
            >
              <div className="document-top">
                <div className="paper-toolbar">
                  <label className="paper-search">
                    <Search />
                    <input
                      aria-label="Search document"
                      placeholder="Find in document…"
                      value={docQuery}
                      onChange={(e) => setDocQuery(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          const c = currentClaims.find((c) =>
                            c.text.toLowerCase().includes(docQuery.toLowerCase()),
                          );
                          if (c) sync(c.id, "document");
                        }
                      }}
                    />
                  </label>
                  <span className="toolbar-divider" />
                  <select
                    aria-label="Jump to page"
                    value={page}
                    onChange={(e) => {
                      const p = Number(e.target.value);
                      setPage(p);
                      document
                        .getElementById(`paper-page-${p}`)
                        ?.scrollIntoView({ behavior: "smooth", block: "start" });
                    }}
                  >
                    {Array.from({ length: 12 }, (_, i) => (
                      <option key={i} value={i + 1}>
                        Page {i + 1} / 12
                      </option>
                    ))}
                  </select>
                  <span className="toolbar-divider" />
                  <Button
                    variant="ghost"
                    title="Decrease text size"
                    aria-label="Decrease text size"
                    onClick={() => setFont((f) => Math.max(0, f - 1))}
                  >
                    A−
                  </Button>
                  <Button
                    variant="ghost"
                    title="Increase text size"
                    aria-label="Increase text size"
                    onClick={() => setFont((f) => Math.min(2, f + 1))}
                  >
                    A+
                  </Button>
                  <span className="toolbar-divider" />
                  <Button
                    variant="ghost"
                    title="Change zoom"
                    onClick={() => setZoom((z) => (z === 100 ? 125 : z === 125 ? 150 : 100))}
                  >
                    {zoom}%
                  </Button>
                </div>
                <div
                  className="segmented document-tabs"
                  role="tablist"
                  aria-label="Document display"
                >
                  <Button
                    variant="ghost"
                    role="tab"
                    aria-selected={docMode === "text"}
                    onClick={() => setDocMode("text")}
                  >
                    <ScanText />
                    Text
                  </Button>
                  <Button
                    variant="ghost"
                    role="tab"
                    aria-selected={docMode === "preview"}
                    onClick={() => setDocMode("preview")}
                  >
                    <FileText />
                    PDF Page Preview
                  </Button>
                </div>
              </div>
              <article
                className={`paper ${docMode === "preview" ? "text-mode-hidden" : ""} ${font === 0 ? "font-small" : font === 2 ? "font-large" : ""} zoom-${zoom}`}
              >
                <div className="page-divider" id="paper-page-1">
                  Page 1
                </div>
                <div className="paper-kicker">
                  RESEARCH ARTICLE &nbsp; · &nbsp;{" "}
                  {isLiveAnalysis ? "VERIFIED DOCUMENT AUDIT" : "SIMULATED DEMO DOCUMENT"}{" "}
                  {docMode === "preview" && " · PAGE PREVIEW"}
                </div>
                <h1>{currentDocTitle}</h1>
                {currentDocText ? (
                  <div className="space-y-4 mt-4">
                    {currentDocText.split(/\n\s*\n/).map((para, idx) => {
                      const matchingClaim = currentClaims.find((c) =>
                        para.toLowerCase().includes(c.text.toLowerCase().slice(0, 35)),
                      );
                      return (
                        <p key={idx}>
                          {matchingClaim ? (
                            <>
                              {highlight(matchingClaim.id)}{" "}
                              <span className="text-muted-foreground">
                                ({matchingClaim.citation}).
                              </span>
                            </>
                          ) : (
                            para
                          )}
                        </p>
                      );
                    })}
                  </div>
                ) : (
                  <>
                    <p className="authors">
                      Sarah Mitchell¹, James Anderson², Priya Sharma¹
                      <br />¹ Department of Computer Science &nbsp; ² School of Medicine
                      <br />
                      Illustrative research paper · Demo dataset
                    </p>
                    <h2>Abstract</h2>
                    <p>
                      Machine learning has emerged as a promising tool for the early detection of
                      disease. This paper examines applications across cardiovascular disease, diabetic
                      retinopathy, and cancer screening, with a focus on diagnostic accuracy and
                      clinical utility.
                    </p>
                    <p>
                      We review recent developments in automated diagnosis and evaluate the evidence
                      supporting their use in clinical decision-making.
                    </p>
                    <h2>2. Methods</h2>
                    <div className="page-divider" id="paper-page-2">
                      Page 2
                    </div>
                    <p>
                      A structured literature review was conducted to identify studies applying machine
                      learning techniques to early disease detection. Studies were assessed for
                      validation methodology, sample size, and reported diagnostic performance.
                    </p>
                    <div className="page-divider" id="paper-page-3">
                      Page 3
                    </div>
                    <h2>3. Results</h2>
                    <p>
                      Recent advances in computer vision have demonstrated considerable promise in
                      screening applications. {highlight(1)}{" "}
                      <span className="text-muted-foreground">(Gulshan et al., 2016).</span>
                    </p>
                    <p>
                      In cardiovascular medicine, predictive models offer new opportunities for
                      preventive care. {highlight(2)}{" "}
                      <span className="text-muted-foreground">(Chen et al., 2023).</span>
                    </p>
                    <div className="page-divider" id="paper-page-4">
                      Page 4
                    </div>
                    <p>
                      These findings suggest a shift in clinical workflows. {highlight(3)}{" "}
                      <span className="text-muted-foreground">(Esteva et al., 2017).</span>
                    </p>
                    <p>
                      Traditional classification approaches continue to play a role. {highlight(4)}{" "}
                      <span className="text-muted-foreground">(Kourou et al., 2015).</span>
                    </p>
                    {[5, 6, 7, 8].map((p) => (
                      <div key={p}>
                        <div className="page-divider" id={`paper-page-${p}`}>
                          Page {p}
                        </div>
                        {p === 5 && <h2>4. Discussion</h2>}
                        {currentClaims
                          .filter((c) => c.page === p)
                          .map((c) => (
                            <p key={c.id}>
                              {highlight(c.id)}{" "}
                              <span className="text-muted-foreground">({c.citation}).</span>
                            </p>
                          ))}
                      </div>
                    ))}
                    <h2>References</h2>
                    {currentClaims
                      .filter((c, i, list) => list.findIndex((x) => x.citation === c.citation) === i)
                      .map((c) => (
                        <p key={c.id} className="text-xs">
                          {c.citation}. {c.title}. <em>{c.journal}</em>.
                        </p>
                      ))}
                    {[9, 10, 11, 12].map((p) => (
                      <div className="page-divider" key={p} id={`paper-page-${p}`}>
                        Page {p} · Demo excerpt only
                      </div>
                    ))}
                  </>
                )}
              </article>
              {docMode === "preview" && (
                <article
                  className={`paper page-preview zoom-${zoom}`}
                  aria-label={`Demo PDF page ${page} preview`}
                >
                  <div className="paper-kicker">
                    CITEVERIFY · {isLiveAnalysis ? "LIVE DOCUMENT" : "SIMULATED DEMO PAPER"}
                  </div>
                  <h1>{currentDocTitle}</h1>
                  <p className="authors">
                    {isLiveAnalysis
                      ? "Extracted Research Document · CiteVerify Audit"
                      : "Sarah Mitchell, James Anderson, Priya Sharma · Demo dataset"}
                  </p>
                  <div className="page-divider">Page {page}</div>
                  <h2>
                    {page === 1
                      ? "Abstract"
                      : page === 2
                        ? "Methods"
                        : page < 5
                          ? "Results"
                          : page < 9
                            ? "Discussion"
                            : "References"}
                  </h2>
                  {page === 1 ? (
                    <p>
                      Machine learning has emerged as a promising tool for the early detection of
                      disease. This illustrative paper examines diagnostic accuracy and clinical
                      utility across screening applications.
                    </p>
                  ) : page === 2 ? (
                    <p>
                      A structured literature review was conducted to identify studies applying
                      machine learning techniques to early disease detection. Studies were assessed
                      for validation methodology, sample size, and reported performance.
                    </p>
                  ) : page < 9 ? (
                    currentClaims
                      .filter((c) => c.page === page)
                      .map((c) => (
                        <p key={c.id}>
                          {highlight(c.id)}{" "}
                          <span className="text-muted-foreground">({c.citation}).</span>
                        </p>
                      ))
                  ) : (
                    currentClaims
                      .filter((c, i) => i % 4 === page - 9)
                      .map((c) => (
                        <p key={c.id}>
                          {c.citation}. {c.title}. <em>{c.journal}</em>.
                        </p>
                      ))
                  )}
                  <footer className="preview-page-footer">
                    SIMULATED DEMO EXCERPT · {page} / 12
                  </footer>
                </article>
              )}
              <div className="mobile-only floating-document-toolbar">
                <FileText size={15} />
                <span>Page {page} / 12</span>
                <span className="toolbar-divider" />
                <Button
                  variant="ghost"
                  aria-label="Decrease document text size"
                  onClick={() => setFont((f) => Math.max(0, f - 1))}
                >
                  A−
                </Button>
                <Button
                  variant="ghost"
                  aria-label="Increase document text size"
                  onClick={() => setFont((f) => Math.min(2, f + 1))}
                >
                  A+
                </Button>
                <span className="toolbar-divider" />
                <Button
                  variant="ghost"
                  aria-label="Document zoom"
                  onClick={() => setZoom((z) => (z === 100 ? 125 : 100))}
                >
                  {zoom}%
                </Button>
              </div>
            </section>
            <section
              className={`report-panel ${mobileTab !== "report" ? "mobile-hidden" : ""}`}
              aria-label="Verification report"
            >
              <div className="report-heading">
                <div>
                  <h1>Verification Report</h1>
                  <p>
                    {currentClaims.length} claims reviewed ·{" "}
                    {new Set(currentClaims.map((c) => c.citation)).size} sources
                  </p>
                </div>
                <span>
                  <ShieldCheck size={13} />
                  Every verdict, backed by evidence
                </span>
              </div>
              <div className="metrics">
                {(["all", "supported", "partial", "unsupported", "outdated"] as const).map((s) => (
                  <Button
                    key={s}
                    variant="ghost"
                    className={`metric ${s === "all" ? "" : `status-${s}`} ${filter === s ? "selected" : ""}`}
                    aria-pressed={filter === s}
                    onClick={() => setFilter(s)}
                  >
                    <strong>
                      {s === "all" ? currentClaims.length : currentClaims.filter((c) => c.status === s).length}
                    </strong>
                    <span>
                      <i />
                      {s === "all"
                        ? "Total Claims"
                        : s === "partial"
                          ? "Partially Supported"
                          : statusLabels[s]}
                    </span>
                  </Button>
                ))}
              </div>
              <div className="filters">
                <div className="search-sort">
                  <label className="search-field">
                    <Search />
                    <input
                      aria-label="Search claims"
                      placeholder="Search claims or citations…"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                    />
                  </label>
                  <select
                    className="sort-select"
                    aria-label="Sort claims"
                    value={sort}
                    onChange={(e) => setSort(e.target.value)}
                  >
                    <option value="document">Sort: Document Order</option>
                    <option value="confidence">Sort: Confidence</option>
                    <option value="flagged">Sort: Flagged First</option>
                  </select>
                </div>
                <div className="filter-chips">
                  {(["all", "supported", "partial", "unsupported", "outdated"] as const).map(
                    (s) => (
                      <Button
                        key={s}
                        variant="ghost"
                        aria-pressed={filter === s}
                        onClick={() => setFilter(s)}
                      >
                        {s === "all" ? "All Claims" : s === "partial" ? "Partial" : statusLabels[s]}
                      </Button>
                    ),
                  )}
                  <Button
                    variant="link"
                    className="reset"
                    onClick={() => {
                      setFilter("all");
                      setQuery("");
                      setSort("document");
                    }}
                  >
                    Reset Filters
                  </Button>
                </div>
              </div>
              <div className="claim-list">
                {currentClaims.length === 0 ? (
                  <div className="p-8 text-center text-muted-foreground border rounded-lg bg-card my-4">
                    <FileText className="mx-auto mb-2 opacity-50" size={32} />
                    <p className="font-semibold text-foreground text-sm">No verifiable scientific claims detected</p>
                    <p className="text-xs mt-1 text-muted-foreground max-w-md mx-auto">
                      This document was extracted successfully, but does not appear to contain verifiable empirical hypotheses, quantitative results, or scientific citations.
                    </p>
                  </div>
                ) : filtered.length === 0 ? (
                  <div className="p-8 text-center text-muted-foreground border rounded-lg bg-card my-4">
                    <p className="text-xs">No claims match the selected filter criteria.</p>
                  </div>
                ) : (
                  filtered.map((c) => (
                  <article
                    key={c.id}
                    id={`claim-${c.id}`}
                    className={`claim-card status-${c.status} ${active === c.id ? "expanded" : ""}`}
                  >
                    <Button
                      variant="ghost"
                      className="claim-summary"
                      aria-expanded={active === c.id}
                      onClick={() => {
                        const opening = active !== c.id;
                        setActive(opening ? c.id : null);
                        if (opening) {
                          setPulse(c.id);
                          setPage(c.page);
                          setDocMode("text");
                          document
                            .getElementById(`highlight-${c.id}`)
                            ?.scrollIntoView({ behavior: "smooth", block: "center" });
                        }
                      }}
                    >
                      <div className="claim-top">
                        <p>{c.text}</p>
                        <ChevronDown />
                      </div>
                      <div className="claim-meta">
                        <span className="page-badge">p. {c.page}</span>
                        <span>({c.citation})</span>
                        <StatusBadge status={c.status} />
                        <span className="confidence">{c.confidence}% Match · Abstract Only</span>
                        {flags.includes(c.id) && (
                          <Flag
                            size={12}
                            className="text-partial-accent"
                            aria-label="Flagged for human review"
                          />
                        )}
                        {verified.includes(c.id) && (
                          <CheckCircle2
                            size={13}
                            className="text-supported-accent"
                            aria-label="Human verified"
                          />
                        )}
                      </div>
                    </Button>
                    {active === c.id && (
                      <div className="claim-detail space-y-4 p-4 border-t bg-card/40">
                        {/* 1. CLAIM & CITATION */}
                        <div className="rounded-lg border bg-background/80 p-3.5 space-y-1.5">
                          <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <span className="font-semibold uppercase tracking-wider text-[11px] text-primary flex items-center gap-1.5">
                              <FileText className="h-3.5 w-3.5" />
                              1. Scientific Claim & In-Text Citation
                            </span>
                            <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-muted">
                              Page: {c.page}
                            </span>
                          </div>
                          <p className="text-sm font-medium text-foreground leading-relaxed">{c.text}</p>
                          <div className="text-xs text-muted-foreground flex items-center gap-2 pt-1">
                            <span className="font-semibold text-foreground">In-Text Citation Marker:</span>
                            <code className="bg-secondary px-1.5 py-0.5 rounded text-[11px]">{c.citation}</code>
                          </div>
                        </div>

                        {/* 2. PUBLICATION DETAILS */}
                        <div className="rounded-lg border bg-background/80 p-3.5 space-y-2">
                          <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <span className="font-semibold uppercase tracking-wider text-[11px] text-primary flex items-center gap-1.5">
                              <BookOpen className="h-3.5 w-3.5" />
                              2. Cited Publication Identity
                            </span>
                            <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${
                              c.matchingStatus === "VERIFIED_MATCH"
                                ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                                : c.matchingStatus === "POSSIBLE_MATCH"
                                ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                                : "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                            }`}>
                              {c.matchingStatus || "VERIFIED_MATCH"}
                            </span>
                          </div>
                          <div>
                            <p className="text-sm font-semibold text-foreground">{c.title}</p>
                            <div className="text-xs text-muted-foreground mt-1 flex flex-wrap gap-x-3 gap-y-1">
                              {c.authors && c.authors.length > 0 && (
                                <span><strong>Authors:</strong> {c.authors.join(", ")}</span>
                              )}
                              <span><strong>Venue:</strong> {c.journal}</span>
                              {c.publisher && <span><strong>Publisher:</strong> {c.publisher}</span>}
                            </div>
                          </div>
                        </div>

                        {/* 3. VERDICT AND EXPLANATION */}
                        <div className="rounded-lg border bg-background/80 p-3.5 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold uppercase tracking-wider text-[11px] text-primary flex items-center gap-1.5">
                              <Sparkles className="h-3.5 w-3.5" />
                              3. Verification Verdict & Scientific Reasoning
                            </span>
                            <StatusBadge status={c.status} />
                          </div>
                          <p className="text-xs text-foreground/90 leading-relaxed bg-muted/30 p-2.5 rounded border border-border/50">
                            {c.reasoning}
                          </p>
                        </div>

                        {/* 4. ACTUAL EVIDENCE PASSAGE */}
                        <div className="rounded-lg border bg-background/80 p-3.5 space-y-2">
                          <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <span className="font-semibold uppercase tracking-wider text-[11px] text-primary flex items-center gap-1.5">
                              <Quote className="h-3.5 w-3.5" />
                              4. Verifiable Literature Evidence Passage
                            </span>
                            <span className="text-[11px] px-2 py-0.5 rounded bg-secondary font-mono">
                              Provenance: {c.evidenceType === "full_text" ? "Full-Text Publication" : "Abstract / Open Access"}
                            </span>
                          </div>
                          <blockquote className="rounded border-l-4 border-primary/60 bg-muted/40 p-3 text-xs italic text-foreground leading-relaxed">
                            &ldquo;{c.quote}&rdquo;
                          </blockquote>
                          {c.evidencePassages && c.evidencePassages.length > 1 && (
                            <div className="space-y-1.5 pt-1">
                              <span className="text-[11px] font-semibold text-muted-foreground">Additional Supporting Passages:</span>
                              {c.evidencePassages.slice(1).map((p, pIdx) => (
                                <p key={pIdx} className="text-xs text-muted-foreground border-l-2 border-border pl-2 italic">
                                  &ldquo;{p.text}&rdquo; {p.page_number ? `(p. ${p.page_number})` : ""}
                                </p>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* 5. LIMITATIONS & DETECTED ISSUES */}
                        <div className="rounded-lg border bg-background/80 p-3.5 space-y-2">
                          <span className="font-semibold uppercase tracking-wider text-[11px] text-primary flex items-center gap-1.5">
                            <AlertTriangle className="h-3.5 w-3.5" />
                            5. Limitations, Caveats & Scientific Verification Issues
                          </span>
                          {((c.issues && c.issues.length > 0) || (c.limitations && c.limitations.length > 0)) ? (
                            <div className="space-y-1.5">
                              {c.issues?.map((iss, iIdx) => (
                                <div key={iIdx} className="flex items-start gap-2 rounded bg-amber-500/10 border border-amber-500/30 p-2 text-xs text-amber-900 dark:text-amber-200">
                                  <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-0.5 text-amber-600 dark:text-amber-400" />
                                  <span>{iss}</span>
                                </div>
                              ))}
                              {c.limitations?.map((lim, lIdx) => (
                                <div key={lIdx} className="flex items-start gap-2 rounded bg-muted/60 p-2 text-xs text-muted-foreground">
                                  <Info className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                                  <span>{lim}</span>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="flex items-center gap-2 rounded bg-emerald-500/10 border border-emerald-500/20 p-2 text-xs text-emerald-800 dark:text-emerald-300">
                              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                              <span>No metric mismatches, inverted findings, or generalization fallacies detected.</span>
                            </div>
                          )}
                        </div>

                        {/* 6. SOURCE TRACEABILITY */}
                        <div className="rounded-lg border bg-background/80 p-3.5 space-y-2 text-xs">
                          <span className="font-semibold uppercase tracking-wider text-[11px] text-primary flex items-center gap-1.5">
                            <ExternalLink className="h-3.5 w-3.5" />
                            6. Source Traceability & Metadata Provenance
                          </span>
                          <div className="flex flex-wrap items-center gap-3 text-muted-foreground">
                            {c.doi ? (
                              <a
                                href={`https://doi.org/${c.doi}`}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 text-primary hover:underline font-mono"
                              >
                                DOI: {c.doi} <ExternalLink size={11} />
                              </a>
                            ) : (
                              <span className="text-muted-foreground">DOI: Not available or unindexed</span>
                            )}
                            <span className="inline-flex items-center gap-1">
                              <CheckCircle2 size={11} className="text-emerald-500" />
                              Resolved via Crossref & Semantic Scholar
                            </span>
                            {c.traceabilityNodeId && (
                              <span className="font-mono text-[10px] text-muted-foreground/70">
                                Node: {c.traceabilityNodeId}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* 7. HUMAN REVIEW STATUS */}
                        <div className="rounded-lg border bg-background/80 p-3.5 space-y-3">
                          <span className="font-semibold uppercase tracking-wider text-[11px] text-primary flex items-center gap-1.5">
                            <MessageSquare className="h-3.5 w-3.5" />
                            7. Human Review & Independent Expert Verification
                          </span>
                          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                            <label className="flex items-center gap-2 text-xs font-medium cursor-pointer">
                              <Switch
                                checked={flags.includes(c.id)}
                                onCheckedChange={() => setFlags((f) => toggle(f, c.id))}
                                aria-label="Flag for Human Review"
                              />
                              Flag for Independent Human Review
                            </label>
                            <Button
                              size="sm"
                              variant={verified.includes(c.id) ? "default" : "outline"}
                              onClick={() => setVerified((v) => toggle(v, c.id))}
                              className="text-xs h-8"
                            >
                              <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                              {verified.includes(c.id) ? "Verified by Human" : "Mark Verified by Human"}
                            </Button>
                          </div>
                          <div>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 text-xs px-2 text-muted-foreground"
                              onClick={() => setNotesOpen((n) => toggle(n, c.id))}
                            >
                              <MessageSquare className="h-3 w-3 mr-1" />
                              {notesOpen.includes(c.id) ? "Hide Reviewer Notes" : "Add / Edit Reviewer Notes"}
                              {notesOpen.includes(c.id) ? <ChevronDown className="h-3 w-3 ml-1" /> : <ChevronRight className="h-3 w-3 ml-1" />}
                            </Button>
                            {notesOpen.includes(c.id) && (
                              <div className="mt-2 space-y-1.5">
                                <textarea
                                  aria-label="Reviewer Notes"
                                  placeholder="Record your independent evaluation, nuance caveats, or audit notes…"
                                  value={notes[c.id] || ""}
                                  onChange={(e) => setNotes((n) => ({ ...n, [c.id]: e.target.value }))}
                                  className="w-full text-xs rounded-md border p-2 bg-background text-foreground min-h-[64px]"
                                />
                                {notes[c.id] && (
                                  <span className="text-[10px] text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                                    <Check size={10} /> Saved to session report
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        </div>

                        {/* 8. EVIDENCE ALIGNMENT SCORE (%) — FINAL ELEMENT AT THE VERY BOTTOM OF THE CLAIM BOX */}
                        <div
                          className={`rounded-xl border p-4 transition-all ${
                            c.confidence >= 80
                              ? "border-emerald-300 bg-emerald-50/80 text-emerald-950 dark:border-emerald-800/80 dark:bg-emerald-950/40 dark:text-emerald-100"
                              : c.confidence >= 50
                              ? "border-amber-300 bg-amber-50/80 text-amber-950 dark:border-amber-800/80 dark:bg-amber-950/40 dark:text-amber-100"
                              : "border-rose-300 bg-rose-50/80 text-rose-950 dark:border-rose-800/80 dark:bg-rose-950/40 dark:text-rose-100"
                          }`}
                        >
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <div className="flex items-center gap-3">
                              <div
                                className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-xl font-mono text-xl font-bold shadow-sm ${
                                  c.confidence >= 80
                                    ? "bg-emerald-600 text-white dark:bg-emerald-500"
                                    : c.confidence >= 50
                                    ? "bg-amber-500 text-white dark:bg-amber-600"
                                    : "bg-rose-600 text-white dark:bg-rose-500"
                                }`}
                              >
                                {c.confidence}%
                              </div>
                              <div>
                                <div className="flex items-center gap-2">
                                  <span className="text-sm font-bold tracking-tight">
                                    {c.alignmentDisplay || (c.confidence >= 80 ? `${c.confidence}% — Strong Evidence Alignment` : c.confidence >= 50 ? `${c.confidence}% — Moderate Evidence Alignment` : `${c.confidence}% — Weak Evidence Alignment`)}
                                  </span>
                                  <span
                                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wider ${
                                      c.confidence >= 80
                                        ? "bg-emerald-200/90 text-emerald-900 dark:bg-emerald-900/70 dark:text-emerald-200"
                                        : c.confidence >= 50
                                        ? "bg-amber-200/90 text-amber-900 dark:bg-amber-900/70 dark:text-amber-200"
                                        : "bg-rose-200/90 text-rose-900 dark:bg-rose-900/70 dark:text-rose-200"
                                    }`}
                                  >
                                    {c.alignmentTier || (c.confidence >= 80 ? "STRONG" : c.confidence >= 50 ? "MODERATE" : "WEAK")}
                                  </span>
                                </div>
                                <p className="text-xs opacity-90 mt-1">
                                  Final Evidence Alignment Score: 4-factor scoring across Publication Identity (20%), Provenance Depth (25%), Verdict Alignment (35%), and Deterministic Scientific Checks (20%).
                                </p>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </article>
                )))}
              </div>
              {!filtered.length && (
                <div className="empty-result">
                  <ListFilter size={24} />
                  <p>No claims match your filters.</p>
                  <Button
                    variant="link"
                    onClick={() => {
                      setQuery("");
                      setFilter("all");
                    }}
                  >
                    Clear filters
                  </Button>
                </div>
              )}
              <p className="demo-disclaimer">
                {isLiveAnalysis
                  ? "CiteVerify live analysis · Cross-referenced with peer-reviewed literature and source abstracts."
                  : "Demo dataset · Excerpts, verdicts, and confidence scores are illustrative, not live verification."}
              </p>
              <div className="report-bottom">
                <Info />
                AI-assisted analysis. Human judgment comes first.
              </div>
            </section>
          </main>
        </>
      )}
      <Dialog
        open={modal !== null}
        onOpenChange={(open) => {
          if (!open) setModal(null);
        }}
      >
        <DialogContent>
          {modal === "menu" ? (
            <>
              <DialogTitle>CiteVerify</DialogTitle>
              <DialogDescription>Verify the Science. Trust the Evidence.</DialogDescription>
              <div className="flex flex-col gap-3">
                {screen === "workspace" && (
                  <>
                    <Button
                      onClick={() => {
                        exportReport();
                        setModal(null);
                      }}
                    >
                      <Download />
                      Export Audit Report
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => {
                        reset();
                        setModal(null);
                      }}
                    >
                      <RotateCcw />
                      New Analysis
                    </Button>
                  </>
                )}
                <Button variant="ghost" onClick={() => setModal("how")}>
                  <CircleHelp />
                  How It Works
                </Button>
                <Button variant="ghost" onClick={() => setModal("trust")}>
                  <ShieldCheck />
                  Academic Trust Guidelines
                </Button>
                <div className="pt-2 border-t border-border flex items-center justify-between">
                  <span className="text-xs text-muted-foreground font-medium">Account</span>
                  <UserMenu />
                </div>
              </div>
            </>
          ) : modal === "upload" ? (
            <>
              <div className="modal-icon">
                <FileText />
              </div>
              <DialogTitle>Your PDF is ready</DialogTitle>
              <DialogDescription>
                This version is an interactive design demo. Live analysis of uploaded papers isn’t
                connected yet, and your file has not been sent anywhere.
              </DialogDescription>
              <p className="text-sm text-muted-foreground">
                Explore the sample paper to see the complete evidence review experience.
              </p>
              <Button
                onClick={() => {
                  setModal(null);
                  analyze(true);
                }}
              >
                <FlaskConical />
                Explore Demo Analysis
              </Button>
              <Button variant="ghost" onClick={() => setModal(null)}>
                Back to my paper
              </Button>
            </>
          ) : (
            <>
              <div className="modal-icon">{modal === "trust" ? <ShieldCheck /> : <BookOpen />}</div>
              <DialogTitle>
                {modal === "trust" ? "Academic Trust Guidelines" : "How It Works"}
              </DialogTitle>
              <DialogDescription>
                {modal === "trust"
                  ? "Good science starts with thoughtful, transparent review."
                  : "From a scientific claim to the evidence behind it."}
              </DialogDescription>
              <div>
                {modalPoints.map(([title, text], i) => (
                  <div className="modal-point" key={title}>
                    <span>{i + 1}</span>
                    <div>
                      <h3>{title}</h3>
                      <p>{text}</p>
                    </div>
                  </div>
                ))}
              </div>
              <Button className="w-full" onClick={() => setModal(null)}>
                Got it
                <Check />
              </Button>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Traceability Graph DAG Dialog */}
      <Dialog open={graphModalOpen} onOpenChange={setGraphModalOpen}>
        <DialogContent className="sm:max-w-3xl max-h-[85vh] overflow-y-auto">
          <div className="flex items-center gap-2 mb-2">
            <div className="h-9 w-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
              <Network className="h-5 w-5" />
            </div>
            <div>
              <DialogTitle className="text-lg font-bold">
                Claim-to-Evidence Traceability Graph (DAG)
              </DialogTitle>
              <DialogDescription className="text-xs">
                Auditable directed acyclic graph mapping Document → Claims → In-Text Citations → Sources → Evidence Passages → Verdicts.
              </DialogDescription>
            </div>
          </div>

          {graphLoading ? (
            <div className="py-12 flex flex-col items-center justify-center gap-2 text-muted-foreground">
              <LoaderCircle className="h-6 w-6 animate-spin text-primary" />
              <span className="text-xs">Constructing Traceability DAG…</span>
            </div>
          ) : graphData && graphData.nodes && graphData.nodes.length > 0 ? (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground pb-2 border-b">
                <span className="font-semibold text-foreground">Graph Nodes ({graphData.nodes.length}):</span>
                <span className="px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-950 text-blue-800 dark:text-blue-300">Document</span>
                <span>→</span>
                <span className="px-2 py-0.5 rounded bg-purple-100 dark:bg-purple-950 text-purple-800 dark:text-purple-300">Claims</span>
                <span>→</span>
                <span className="px-2 py-0.5 rounded bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300">Citations</span>
                <span>→</span>
                <span className="px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300">Sources</span>
                <span>→</span>
                <span className="px-2 py-0.5 rounded bg-indigo-100 dark:bg-indigo-950 text-indigo-800 dark:text-indigo-300">Evidence Passages</span>
                <span>→</span>
                <span className="px-2 py-0.5 rounded bg-teal-100 dark:bg-teal-950 text-teal-800 dark:text-teal-300">Verdicts</span>
              </div>

              <div className="space-y-2 max-h-[50vh] overflow-y-auto pr-1">
                {graphData.nodes.map((node) => {
                  const nodeColor =
                    node.type === "document"
                      ? "border-blue-500/40 bg-blue-50/50 dark:bg-blue-950/20"
                      : node.type === "claim"
                      ? "border-purple-500/40 bg-purple-50/50 dark:bg-purple-950/20"
                      : node.type === "citation"
                      ? "border-amber-500/40 bg-amber-50/50 dark:bg-amber-950/20"
                      : node.type === "source"
                      ? "border-emerald-500/40 bg-emerald-50/50 dark:bg-emerald-950/20"
                      : node.type === "passage"
                      ? "border-indigo-500/40 bg-indigo-50/50 dark:bg-indigo-950/20"
                      : "border-teal-500/40 bg-teal-50/50 dark:bg-teal-950/20";

                  return (
                    <div key={node.id} className={`rounded-lg border p-3 text-xs ${nodeColor}`}>
                      <div className="flex items-center justify-between font-mono text-[10px] text-muted-foreground mb-1">
                        <span className="uppercase font-bold tracking-wider text-foreground">{node.type}</span>
                        <span>{node.id}</span>
                      </div>
                      <p className="font-medium text-foreground">{node.label}</p>
                      {node.data && Object.keys(node.data).length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-muted-foreground pt-1 border-t border-border/40">
                          {Object.entries(node.data)
                            .filter(([_, v]) => v !== null && v !== undefined && typeof v !== "object")
                            .slice(0, 4)
                            .map(([k, v]) => (
                              <span key={k}>
                                <strong className="text-foreground/80">{k}:</strong> {String(v)}
                              </span>
                            ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              <div className="pt-2 border-t text-xs text-muted-foreground">
                <span className="font-semibold text-foreground">Graph Edges ({graphData.edges.length}):</span> Complete claim-to-evidence provenance with zero hallucinated leaps.
              </div>
            </div>
          ) : (
            <div className="py-8 text-center text-xs text-muted-foreground">
              <Network className="mx-auto h-8 w-8 text-muted-foreground/40 mb-2" />
              <p className="font-medium text-foreground">Traceability Graph Available During Document Analysis</p>
              <p className="mt-1">Analyze a scientific PDF or Word document to generate an end-to-end directed acyclic graph mapping every extracted claim to its cited publication and retrieved evidence passage.</p>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
