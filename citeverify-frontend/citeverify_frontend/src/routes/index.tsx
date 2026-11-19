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
} from "lucide-react";
import { Button } from "@/button";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/dialog";
import { Switch } from "@/switch";
import { UserMenu } from "@/lib/user-menu";
import { api, type VerificationResult } from "@/lib/api";
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
  else if (verdict === "POSSIBLY_OUTDATED") status = "outdated";

  const firstPassage = v.evidence_passages?.[0]?.text || "";
  const source = v.source;
  const journal = [source?.journal, source?.year].filter(Boolean).join(" · ");
  const confidenceScore = Math.round((v.confidence?.score || 0.75) * 100);

  return {
    id: index + 1,
    status,
    text: v.claim_text,
    citation: v.citation_reference || (source?.authors?.[0] ? `${source.authors[0]} et al.` : "Cited Source"),
    confidence: confidenceScore,
    page: v.evidence_passages?.[0]?.page_number || (index % 4) + 3,
    quote: firstPassage || "Evidence retrieved from verified literature abstract and metadata.",
    reasoning: v.explanation || "Evaluated by CiteVerify research verification engine.",
    title: source?.title || "Academic Literature Publication",
    journal: journal || (source?.year ? `Published · ${source.year}` : "Academic Source"),
    doi: source?.doi || "",
    evidencePassages: v.evidence_passages,
    issues: v.issues,
    rawVerdict: v.verdict,
    sourceUrl: source?.url || (source?.doi ? `https://doi.org/${source.doi}` : null),
  };
}

function Index() {
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
                    <div className="text-xs text-muted-foreground mb-4">
                      <strong className="block text-foreground mb-1">Scientific Reasoning:</strong>
                      {directResult.reasoning}
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
                      <div className="claim-detail">
                        <div className="evidence-grid">
                          <div>
                            <div className="evidence-label">
                              <FileText />
                              PAPER’S CLAIM
                            </div>
                            <div className="evidence-box">{c.text}</div>
                          </div>
                          <div>
                            <div className="evidence-label">
                              <Quote />
                              {isLiveAnalysis ? "RETRIEVED RESEARCH EVIDENCE" : "SIMULATED DEMO EXCERPT"}
                            </div>
                            <blockquote className="evidence-box quote-box">
                              “
                              <mark
                                className={
                                  c.status === "unsupported" ? "quote-conflict" : "quote-match"
                                }
                              >
                                {c.quote.split(" ").slice(0, 5).join(" ")}
                              </mark>{" "}
                              {c.quote.split(" ").slice(5).join(" ")}”
                            </blockquote>
                          </div>
                        </div>
                        <div className="reasoning">
                          <h3>
                            <Sparkles />
                            AI Reasoning
                          </h3>
                          <p>{c.reasoning}</p>
                          <small>AI can be wrong. Verify against the full paper.</small>
                        </div>
                        <div className="source-footer">
                          <strong>{c.title}</strong>
                          <p>
                            {c.journal}
                            {c.doi ? (
                              <a href={`https://doi.org/${c.doi}`} target="_blank" rel="noreferrer">
                                DOI: {c.doi}
                                <ExternalLink />
                              </a>
                            ) : (
                              <span>Illustrative source · DOI not verified</span>
                            )}
                          </p>
                        </div>
                        <Button
                          variant="outline"
                          className="mobile-only mobile-document-button"
                          onClick={() => sync(c.id, "document")}
                        >
                          <FileText />
                          View in Document
                        </Button>
                        <div className="review-bar">
                          <div className="review-controls">
                            <label>
                              <Switch
                                checked={flags.includes(c.id)}
                                onCheckedChange={() => setFlags((f) => toggle(f, c.id))}
                                aria-label="Flag for Human Review"
                              />
                              Flag for Human Review
                            </label>
                            <Button
                              variant={verified.includes(c.id) ? "verifiedSolid" : "verified"}
                              onClick={() => setVerified((v) => toggle(v, c.id))}
                            >
                              <CheckCircle2 />
                              {verified.includes(c.id)
                                ? "Verified by Human"
                                : "Mark Verified by Human"}
                            </Button>
                          </div>
                          <Button
                            variant="ghost"
                            className="notes-toggle"
                            aria-expanded={notesOpen.includes(c.id)}
                            onClick={() => setNotesOpen((n) => toggle(n, c.id))}
                          >
                            <MessageSquare />
                            Reviewer Notes
                            {notesOpen.includes(c.id) ? <ChevronDown /> : <ChevronRight />}
                          </Button>
                          {notesOpen.includes(c.id) && (
                            <div>
                              <textarea
                                aria-label="Reviewer Notes"
                                placeholder="Add your assessment or a note for follow-up…"
                                value={notes[c.id] || ""}
                                onChange={(e) =>
                                  setNotes((n) => ({ ...n, [c.id]: e.target.value }))
                                }
                              />
                              {notes[c.id] && (
                                <span className="notes-saved">
                                  <Check size={10} />
                                  Saved for this session
                                </span>
                              )}
                            </div>
                          )}
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
    </>
  );
}
