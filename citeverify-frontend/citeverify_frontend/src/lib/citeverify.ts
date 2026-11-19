export type Status = "supported" | "partial" | "unsupported" | "outdated";
export const statusLabels: Record<Status, string> = {
  supported: "Supported",
  partial: "Partially Supported",
  unsupported: "Unsupported",
  outdated: "Outdated",
};

export function mapBackendVerdictToStatus(verdict: string): Status {
  const v = (verdict || "").toUpperCase();
  if (v === "SUPPORTED") return "supported";
  if (v === "PARTIALLY_SUPPORTED") return "partial";
  if (v === "UNSUPPORTED" || v === "CONTRADICTORY") return "unsupported";
  if (v === "POSSIBLY_OUTDATED") return "outdated";
  return "partial";
}

export interface ClaimItem {
  id: number;
  status: Status;
  text: string;
  citation: string;
  confidence: number;
  page: number | string;
  quote: string;
  reasoning: string;
  title: string;
  journal: string;
  doi: string;
  evidencePassages?: Array<{ text: string; page_number?: number | null; source_url?: string | null }>;
  issues?: string[];
  limitations?: string[];
  rawVerdict?: string;
  sourceUrl?: string | null;
  authors?: string[];
  year?: number | null;
  publisher?: string | null;
  evidenceType?: string;
  matchingStatus?: string;
  humanReviewRequired?: boolean;
  alignmentScore?: number;
  alignmentTier?: string;
  alignmentDisplay?: string;
  isScoreable?: boolean;
  traceabilityNodeId?: string;
}
export const documentTitle = "Applications of Machine Learning in Early Disease Detection";
export const sampleFilename = "machine_learning_disease_detection.pdf";
export const steps = [
  "Parsing Document Structure",
  "Isolating Scientific Claims",
  "Matching Inline Citations",
  "Retrieving Source Abstracts",
  "Evaluating Evidence Alignment",
];
export function validateDocument(file: { name: string; size: number }) {
  const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  const allowed = [".pdf", ".docx", ".txt"];
  if (!allowed.includes(ext)) {
    return "Unsupported format. CiteVerify supports PDF (.pdf), Word (.docx), and Text (.txt) files.";
  }
  if (file.size === 0) {
    return "Uploaded file is empty (0 bytes). Please upload a valid document containing scientific content.";
  }
  if (file.size > 25 * 1024 * 1024) {
    return "Your document must be 25 MB or smaller";
  }
  return "";
}

export function validatePdf(file: { name: string; size: number }) {
  if (!file.name.toLowerCase().endsWith(".pdf")) return "Only .pdf files are supported";
  if (file.size > 25 * 1024 * 1024) return "Your PDF must be 25 MB or smaller";
  return "";
}
export const claims: {
  id: number;
  status: Status;
  text: string;
  citation: string;
  confidence: number;
  page: number;
  quote: string;
  reasoning: string;
  title: string;
  journal: string;
  doi: string;
}[] = [
  {
    id: 1,
    status: "partial",
    text: "Deep learning models achieved diagnostic accuracy of 94.5% in detecting early-stage diabetic retinopathy from retinal fundus images.",
    citation: "Gulshan et al., 2016",
    confidence: 62,
    page: 3,
    quote:
      "The algorithm had an area under the receiver operating characteristic curve (AUC) of 0.991 for the EyePACS-1 data set and 0.990 for the Messidor-2 data set.",
    reasoning:
      "Metric Mismatch: The cited paper measures Area Under the ROC Curve (AUC 0.991 for EyePACS-1, 0.990 for Messidor-2), not threshold-specific diagnostic accuracy. In medical imaging, AUC evaluates discriminative capability across all cutoffs; accuracy varies depending on the operational decision threshold selected.",
    title:
      "Development and Validation of a Deep Learning Algorithm for Detection of Diabetic Retinopathy in Retinal Fundus Photographs",
    journal: "JAMA · 2016",
    doi: "10.1001/jama.2016.17216",
    issues: [
      "Metric Mismatch: Claim asserts specific diagnostic accuracy (%), but source evidence measures Area Under the ROC Curve (AUC). AUC and diagnostic accuracy are fundamentally different performance metrics."
    ],
    alignmentScore: 62,
    alignmentTier: "MODERATE",
    alignmentDisplay: "62% — Moderate Evidence Alignment",
  },
  {
    id: 2,
    status: "partial",
    text: "Machine learning algorithms can predict cardiovascular disease up to 10 years before clinical symptoms appear, with an accuracy exceeding 90%.",
    citation: "Chen et al., 2023",
    confidence: 74,
    page: 3,
    quote:
      "Machine learning methods improved cardiovascular risk prediction compared with established approaches, with performance varying across populations and prediction horizons.",
    reasoning:
      "The source supports the use of machine learning for cardiovascular risk prediction. However, the abstract does not substantiate the specific 10-year horizon or the claim of accuracy exceeding 90%.",
    title: "Machine learning approaches to cardiovascular risk prediction: a systematic review",
    journal: "Journal of Medical Systems · 2023",
    doi: "",
  },
  {
    id: 3,
    status: "unsupported",
    text: "AI-based screening eliminates the need for specialist review in all early-stage cancer diagnoses.",
    citation: "Esteva et al., 2017",
    confidence: 92,
    page: 4,
    quote:
      "We demonstrate classification of skin lesions using a single convolutional neural network, trained end-to-end from images directly, using only pixels and disease labels as inputs.",
    reasoning:
      "The source evaluates image classification, not the removal of clinical oversight. The universal claim about all cancer diagnoses extends beyond the scope of the study.",
    title: "Dermatologist-level classification of skin cancer with deep neural networks",
    journal: "Nature · 2017",
    doi: "10.1038/nature21056",
  },
  {
    id: 4,
    status: "outdated",
    text: "Support vector machines remain the most accurate approach for medical image classification.",
    citation: "Kourou et al., 2015",
    confidence: 88,
    page: 4,
    quote:
      "Machine learning techniques, including artificial neural networks, Bayesian networks, support vector machines and decision trees, have been widely applied in cancer research.",
    reasoning:
      "This review predates more recent deep learning advances. It discusses support vector machines but does not establish their continued superiority for medical imaging.",
    title: "Machine learning applications in cancer prognosis and prediction",
    journal: "Computational and Structural Biotechnology Journal · 2015",
    doi: "10.1016/j.csbj.2014.11.005",
  },
  {
    id: 5,
    status: "supported",
    text: "Convolutional neural networks demonstrate dermatologist-level performance in skin lesion classification.",
    citation: "Esteva et al., 2017",
    confidence: 98,
    page: 5,
    quote: "The CNN achieves performance on par with all tested experts across both tasks.",
    reasoning:
      "The source directly supports this comparison in the tested classification tasks. Clinical deployment requires additional evaluation.",
    title: "Dermatologist-level classification of skin cancer with deep neural networks",
    journal: "Nature · 2017",
    doi: "10.1038/nature21056",
  },
  {
    id: 6,
    status: "supported",
    text: "Machine learning methods have been widely applied to cancer prognosis and prediction.",
    citation: "Kourou et al., 2015",
    confidence: 95,
    page: 5,
    quote: "Machine learning techniques have been widely applied in cancer research.",
    reasoning:
      "The review directly supports the broad application of these methods. This is not evidence of clinical effectiveness for every application.",
    title: "Machine learning applications in cancer prognosis and prediction",
    journal: "CSBJ · 2015",
    doi: "10.1016/j.csbj.2014.11.005",
  },
  {
    id: 7,
    status: "partial",
    text: "Automated retinal screening generalizes reliably across all demographic populations.",
    citation: "Gulshan et al., 2016",
    confidence: 69,
    page: 6,
    quote:
      "Further research is necessary to determine the feasibility of applying this algorithm in the clinical setting.",
    reasoning:
      "Validation on two datasets supports promise, not universal demographic generalization. Broader prospective evaluation is required.",
    title:
      "Development and Validation of a Deep Learning Algorithm for Detection of Diabetic Retinopathy",
    journal: "JAMA · 2016",
    doi: "10.1001/jama.2016.17216",
  },
  {
    id: 8,
    status: "unsupported",
    text: "All machine learning models are inherently interpretable to clinicians without additional tools.",
    citation: "Chen et al., 2023",
    confidence: 94,
    page: 7,
    quote:
      "Interpretability remains an important challenge for the adoption of machine learning in clinical practice.",
    reasoning:
      "The demo excerpt directly conflicts with the claim of inherent interpretability. Explainability depends on model architecture and supporting methods.",
    title: "Machine learning approaches to cardiovascular risk prediction: a systematic review",
    journal: "Journal of Medical Systems · 2023",
    doi: "",
  },
  {
    id: 9,
    status: "supported",
    text: "Independent validation is necessary before incorporating automated diagnostic models into clinical practice.",
    citation: "Gulshan et al., 2016",
    confidence: 97,
    page: 8,
    quote:
      "Further research is necessary to determine the feasibility of applying this algorithm in the clinical setting.",
    reasoning:
      "The source explicitly calls for further clinical evaluation. This aligns with the paper’s recommendation for independent validation.",
    title:
      "Development and Validation of a Deep Learning Algorithm for Detection of Diabetic Retinopathy",
    journal: "JAMA · 2016",
    doi: "10.1001/jama.2016.17216",
  },
];
