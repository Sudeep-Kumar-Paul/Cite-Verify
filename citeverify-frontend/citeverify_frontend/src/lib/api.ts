/**
 * CiteVerify Centralized API Client
 * Connects frontend UI to CiteVerify FastAPI Backend
 */

export interface SourceInfo {
  title: string;
  doi?: string | null;
  url?: string | null;
  evidence_type?: string;
  authors?: string[] | null;
  year?: number | null;
  journal?: string | null;
  publisher?: string | null;
  doi_url?: string | null;
}

export interface ConfidenceInfo {
  level: "HIGH" | "MEDIUM" | "LOW" | string;
  score: number;
  reason: string;
  alignment_score?: number | null;
  alignment_tier?: "STRONG" | "MODERATE" | "WEAK" | "NOT_SCOREABLE" | string | null;
  alignment_display?: string | null;
  is_scoreable?: boolean;
}

export interface EvidencePassage {
  text: string;
  page_number?: number | null;
  source_url?: string | null;
}

export interface VerificationResult {
  claim_id: string;
  claim_text: string;
  citation_reference?: string | null;
  source?: SourceInfo | null;
  verdict:
    | "SUPPORTED"
    | "PARTIALLY_SUPPORTED"
    | "UNSUPPORTED"
    | "CONTRADICTORY"
    | "NEEDS_HUMAN_REVIEW"
    | "POSSIBLY_OUTDATED"
    | string;
  explanation: string;
  evidence_passages: EvidencePassage[];
  confidence: ConfidenceInfo;
  issues: string[];
  limitations?: string[];
  human_review_required: boolean;
  traceability_node_id?: string | null;
}

export interface TraceabilityNode {
  id: string;
  type: "document" | "claim" | "citation" | "source" | "passage" | "verdict";
  label: string;
  data: Record<string, any>;
}

export interface TraceabilityEdge {
  source: string;
  target: string;
  relationship: string;
}

export interface TraceabilityGraph {
  document_id: string;
  nodes: TraceabilityNode[];
  edges: TraceabilityEdge[];
}

export interface VerificationResponse {
  document_id: string;
  results: VerificationResult[];
  total_claims: number;
  supported: number;
  partially_supported: number;
  unsupported: number;
  contradictory: number;
  needs_human_review: number;
  possibly_outdated: number;
  message: string;
}

export interface DocumentResponse {
  id: string;
  filename: string;
  upload_date: string;
  processing_status: string;
  page_count?: number | null;
  is_scanned: boolean;
  extraction_error?: string | null;
  document_title?: string | null;
  upload_path: string;
  extracted_text?: string | null;
  body_text?: string | null;
  references_text?: string | null;
}

export interface ExtractionStatus {
  document_id: string;
  status: string;
  page_count?: number | null;
  has_body: boolean;
  has_references: boolean;
  is_scanned: boolean;
  message: string;
}

export interface HistoryItem {
  document_id: string;
  filename: string;
  upload_date?: string | null;
  processing_status: string;
  document_title?: string | null;
  page_count?: number | null;
  total_claims: number;
  verified_claims: number;
  has_report: boolean;
}

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  environment: string;
  timestamp: string;
}

export function getApiBaseUrl(): string {
  const envUrl = typeof import.meta !== "undefined" && import.meta.env ? import.meta.env.VITE_API_BASE_URL : "";
  return envUrl || "http://localhost:8000";
}

let authTokenProvider: (() => Promise<string | null>) | null = null;

export function setAuthTokenProvider(provider: () => Promise<string | null>) {
  authTokenProvider = provider;
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = getApiBaseUrl().replace(/\/$/, "");
  const url = `${baseUrl}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;

  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (authTokenProvider && !headers.has("Authorization")) {
    try {
      const token = await authTokenProvider();
      if (token) {
        headers.set("Authorization", `Bearer ${token}`);
      }
    } catch {
      // Continue without token if provider fails
    }
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    try {
      const errorJson = await response.json();
      errorDetail = errorJson.detail || errorJson.message || JSON.stringify(errorJson);
    } catch {
      // Ignore JSON parse error and use statusText
      if (response.statusText) {
        errorDetail = response.statusText;
      }
    }
    throw new Error(errorDetail);
  }

  return response.json() as Promise<T>;
}

export const api = {
  getApiBaseUrl,

  async checkHealth(): Promise<HealthResponse> {
    return request<HealthResponse>("/api/health");
  },

  async uploadDocument(file: File): Promise<DocumentResponse> {
    const formData = new FormData();
    formData.append("file", file);
    return request<DocumentResponse>("/api/documents/", {
      method: "POST",
      body: formData,
    });
  },

  async extractDocument(documentId: string): Promise<ExtractionStatus> {
    return request<ExtractionStatus>(`/api/documents/${encodeURIComponent(documentId)}/extract`, {
      method: "POST",
    });
  },

  async extractClaims(documentId: string): Promise<any> {
    return request<any>(`/api/documents/${encodeURIComponent(documentId)}/extract-claims`, {
      method: "POST",
    });
  },

  async extractCitations(documentId: string): Promise<any> {
    return request<any>(`/api/documents/${encodeURIComponent(documentId)}/extract-citations`, {
      method: "POST",
    });
  },

  async matchCitations(documentId: string): Promise<any> {
    return request<any>(`/api/documents/${encodeURIComponent(documentId)}/match-citations`, {
      method: "POST",
    });
  },

  async runVerification(
    documentId: string,
    claimIds?: string[],
  ): Promise<VerificationResponse> {
    return request<VerificationResponse>("/api/verification/run", {
      method: "POST",
      body: JSON.stringify({
        document_id: documentId,
        claim_ids: claimIds,
      }),
    });
  },

  async getVerificationResults(documentId: string): Promise<VerificationResponse> {
    return request<VerificationResponse>(
      `/api/verification/documents/${encodeURIComponent(documentId)}/results`,
    );
  },

  async runPipeline(documentId: string): Promise<{
    success: boolean;
    document_id: string;
    job_id: string;
    filename: string;
    document_title: string;
    extraction_status: string;
    page_count: number;
    body_text?: string;
    results: VerificationResult[];
    claims: VerificationResult[];
    summary: {
      total_claims: number;
      supported: number;
      partially_supported: number;
      unsupported: number;
      contradictory: number;
      needs_human_review: number;
      possibly_outdated: number;
    };
    total_claims: number;
    message: string;
  }> {
    return request<any>(`/api/documents/${encodeURIComponent(documentId)}/pipeline`, {
      method: "POST",
    });
  },

  async loadDemoDocument(): Promise<{
    document_id: string;
    document_title: string;
    filename: string;
    page_count: number;
    body_text?: string;
    results: VerificationResult[];
    total_claims: number;
    is_demo: boolean;
    message: string;
  }> {
    return request<{
      document_id: string;
      document_title: string;
      filename: string;
      page_count: number;
      body_text?: string;
      results: VerificationResult[];
      total_claims: number;
      is_demo: boolean;
      message: string;
    }>("/api/documents/demo", {
      method: "POST",
    });
  },

  async verifyDirectClaim(
    claimText: string,
    citation?: string,
    doi?: string,
    context?: string,
  ): Promise<VerificationResult> {
    return request<VerificationResult>("/api/verification/verify-claim", {
      method: "POST",
      body: JSON.stringify({
        claim_text: claimText,
        citation: citation || null,
        doi: doi || null,
        context: context || null,
      }),
    });
  },

  async getDocument(documentId: string): Promise<DocumentResponse> {
    return request<DocumentResponse>(`/api/documents/${encodeURIComponent(documentId)}`);
  },

  async exportPdfReport(
    documentId: string,
    includeEvidence = true,
  ): Promise<{
    document_id: string;
    report_path: string;
    download_url: string;
    generated_at: string;
  }> {
    return request<{
      document_id: string;
      report_path: string;
      download_url: string;
      generated_at: string;
    }>(`/api/reports/${encodeURIComponent(documentId)}/export`, {
      method: "POST",
      body: JSON.stringify({
        document_id: documentId,
        include_evidence_passages: includeEvidence,
        include_source_metadata: true,
      }),
    });
  },

  getReportDownloadUrl(documentId: string): string {
    const baseUrl = getApiBaseUrl().replace(/\/$/, "");
    return `${baseUrl}/api/reports/${encodeURIComponent(documentId)}/download`;
  },

  async getTraceabilityGraph(documentId: string): Promise<TraceabilityGraph> {
    return request<TraceabilityGraph>(`/api/verification/documents/${encodeURIComponent(documentId)}/graph`);
  },

  async getHistory(): Promise<HistoryItem[]> {
    return request<HistoryItem[]>("/api/history/");
  },
};
