export type Verdict = "SUPPORTED" | "CONTRADICTED" | "INSUFFICIENT_EVIDENCE";

export interface Evidence {
  document: string | null;
  heading: string | null;
  title: string | null;
  chapter: string | null;
  section: string | null;
  page_start: number | null;
  page_end: number | null;
  text: string;
  heuristics?: {
    time_conflict?: boolean;
    overbroad_claim?: boolean;
    overbroad_conflict?: boolean;
  };
}

export interface VerificationResult {
  claim: string;
  verdict: Verdict;
  confidence: number;
  document: string;
  primary_evidence: Evidence;
  evidence: Evidence[];
  notice: string;
}

export const EXAMPLES = [
  {
    label: "The 72-hour rule",
    topic: "Breach notification",
    claim:
      "A controller must notify the supervisory authority of certain personal data breaches within 72 hours where feasible.",
  },
  {
    label: "A 24-hour deadline?",
    topic: "A claim to check",
    claim: "A controller must report a personal data breach within 24 hours.",
  },
  {
    label: "A free laptop?",
    topic: "An unusual obligation",
    claim:
      "Every company must give customers a free laptop after a personal data breach.",
  },
] as const;

export const GDPR_SOURCE = {
  name: "EU GDPR",
  publisher: "Official Journal of the European Union",
  url: "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
};

export function isGdpr(document: string | null) {
  return document?.toLowerCase() === "gdpr.pdf";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseEvidence(value: unknown): Evidence {
  if (!isRecord(value) || typeof value.text !== "string" || !value.text.trim())
    throw new Error("Invalid evidence");
  const nullableString = (key: string) => {
    if (value[key] == null) return null;
    if (typeof value[key] !== "string") throw new Error("Invalid metadata");
    return value[key];
  };
  const page = (key: string) => {
    if (value[key] == null) return null;
    if (
      typeof value[key] !== "number" ||
      !Number.isInteger(value[key]) ||
      value[key] < 1
    )
      throw new Error("Invalid citation");
    return value[key];
  };
  const heuristics = isRecord(value.heuristics) ? value.heuristics : {};
  const start = page("page_start");
  const end = page("page_end");
  if (start !== null && end !== null && end < start)
    throw new Error("Invalid page range");
  return {
    document: nullableString("document"),
    heading: nullableString("heading"),
    title: nullableString("title"),
    chapter: nullableString("chapter"),
    section: nullableString("section"),
    page_start: start,
    page_end: end,
    text: value.text,
    heuristics: {
      time_conflict: heuristics.time_conflict === true,
      overbroad_claim: heuristics.overbroad_claim === true,
      overbroad_conflict: heuristics.overbroad_conflict === true,
    },
  };
}

// Validate the API boundary and omit internal model fields from the UI contract.
export function parseVerification(value: unknown): VerificationResult {
  if (
    !isRecord(value) ||
    typeof value.claim !== "string" ||
    !value.claim.trim() ||
    typeof value.document !== "string" ||
    !value.document.trim() ||
    !["SUPPORTED", "CONTRADICTED", "INSUFFICIENT_EVIDENCE"].includes(
      String(value.verdict),
    ) ||
    typeof value.confidence !== "number" ||
    !Number.isFinite(value.confidence) ||
    value.confidence < 0 ||
    value.confidence > 1 ||
    !Array.isArray(value.evidence) ||
    value.evidence.length === 0
  )
    throw new Error("Invalid verification response");
  return {
    claim: value.claim,
    verdict: value.verdict as Verdict,
    confidence: value.confidence,
    document: value.document,
    primary_evidence: parseEvidence(value.primary_evidence),
    evidence: value.evidence.map(parseEvidence),
    notice:
      typeof value.notice === "string"
        ? value.notice
        : "Automated evidence analysis. Not legal advice.",
  };
}

export function pageLabel(evidence: Evidence) {
  if (evidence.page_start === null) return "Page unavailable";
  return evidence.page_end && evidence.page_end !== evidence.page_start
    ? `Pages ${evidence.page_start}–${evidence.page_end}`
    : `Page ${evidence.page_start}`;
}

export function evidenceKey(evidence: Evidence) {
  return `${evidence.document}|${evidence.heading}|${evidence.page_start}|${evidence.text}`;
}

export function evidenceTitle(evidence: Evidence) {
  const prefix = `${evidence.heading}: `;
  return evidence.title?.startsWith(prefix)
    ? evidence.title.slice(prefix.length)
    : evidence.title;
}

// Intentionally narrow: do not infer arbitrary numeric conflicts or legal deadlines.
export function getTimeComparison(result: VerificationResult) {
  const evidence = result.primary_evidence;
  const claimTimes = [
    ...result.claim.matchAll(/\b(\d+(?:\.\d+)?)\s*hours?\b/gi),
  ];
  if (
    result.verdict !== "CONTRADICTED" ||
    !isGdpr(result.document) ||
    !isGdpr(evidence.document ?? result.document) ||
    evidence.heading !== "Article 33" ||
    !evidence.heuristics?.time_conflict ||
    claimTimes.length !== 1 ||
    claimTimes[0][1] !== "24" ||
    !/personal data breach/i.test(result.claim) ||
    !/\b(report|notify|notification)\b/i.test(result.claim) ||
    !/where feasible,?\s+not later than\s+72\s+hours/i.test(evidence.text)
  )
    return null;
  return {
    claim: "24 hours",
    law: "72 hours",
    qualification: "where feasible",
  };
}
