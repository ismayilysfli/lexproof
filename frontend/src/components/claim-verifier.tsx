"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  EXAMPLES,
  parseVerification,
  type VerificationResult,
} from "@/lib/verification";
import { ArrowIcon, DocumentIcon } from "./icons";
import { VerificationReport } from "./verification-report";

type RequestState =
  | { status: "idle" }
  | { status: "loading"; claim: string }
  | { status: "success"; result: VerificationResult }
  | { status: "error"; code: string };

const ERRORS: Record<string, { title: string; message: string }> = {
  SERVICE_UNAVAILABLE: {
    title: "LexProof couldn’t reach the verification service.",
    message:
      "The service may be offline or taking too long to respond. Please try again.",
  },
  SOURCE_UNAVAILABLE: {
    title: "The legal source isn’t ready yet.",
    message:
      "The verification service needs an indexed source before it can check your claim. Please try again once the source is ready.",
  },
  INVALID_RESPONSE: {
    title: "We couldn’t read the verification result.",
    message:
      "The service returned an incomplete response. Please try verifying your claim again.",
  },
  VERIFICATION_FAILED: {
    title: "This verification couldn’t be completed.",
    message:
      "Something went wrong while checking the evidence. Your claim is still here—please try again.",
  },
  INVALID_CLAIM: {
    title: "Please check your claim.",
    message: "Enter a legal statement between 3 and 1,000 characters.",
  },
};

export function VerificationProgress() {
  const [takingLonger, setTakingLonger] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setTakingLonger(true), 12_000);
    return () => clearTimeout(timer);
  }, []);
  return (
    <div className="verification-progress" role="status" aria-live="polite">
      <div className="progress-heading">
        <span className="activity-dot" />
        <strong>Following the evidence</strong>
        <span>Verification in progress</span>
      </div>
      <ol className="progress-stages">
        {[
          "Searching primary law",
          "Finding relevant provisions",
          "Testing claim against evidence",
        ].map((label, index) => (
          <li key={label}>
            <span className="progress-number">0{index + 1}</span>
            <span>{label}</span>
            <span className="stage-track" />
          </li>
        ))}
      </ol>
      <p>
        {takingLonger
          ? "The first verification can take a little longer while the local service gets ready. We’re still waiting for the evidence."
          : "Checking your statement against the indexed legal source."}
      </p>
    </div>
  );
}

export function ClaimVerifier() {
  const [claim, setClaim] = useState("");
  const [state, setState] = useState<RequestState>({ status: "idle" });
  const [validation, setValidation] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const resultRef = useRef<HTMLDivElement>(null);
  const requestRef = useRef<AbortController | null>(null);
  const loading = state.status === "loading";

  useEffect(() => () => requestRef.current?.abort(), []);
  useEffect(() => {
    if (state.status === "success" || state.status === "error") {
      resultRef.current?.focus({ preventScroll: true });
      resultRef.current?.scrollIntoView({
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "instant"
          : "smooth",
        block: "start",
      });
    }
  }, [state.status]);

  function updateClaim(value: string) {
    setClaim(value);
    setValidation("");
    if (state.status !== "idle") setState({ status: "idle" });
  }

  async function verify(event?: FormEvent) {
    event?.preventDefault();
    if (requestRef.current) return;
    const submittedClaim = claim.trim();
    if (submittedClaim.length < 3 || submittedClaim.length > 1000) {
      setValidation("Enter a legal statement between 3 and 1,000 characters.");
      textareaRef.current?.focus();
      return;
    }
    const controller = new AbortController();
    requestRef.current = controller;
    setValidation("");
    setState({ status: "loading", claim: submittedClaim });
    try {
      const response = await fetch("/api/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claim: submittedClaim }),
        signal: AbortSignal.any([
          controller.signal,
          AbortSignal.timeout(125_000),
        ]),
      });
      let body: unknown;
      try {
        body = await response.json();
      } catch {
        setState({ status: "error", code: "INVALID_RESPONSE" });
        return;
      }
      if (!response.ok) {
        const code =
          body &&
          typeof body === "object" &&
          "code" in body &&
          typeof body.code === "string"
            ? body.code
            : "VERIFICATION_FAILED";
        setState({ status: "error", code });
        return;
      }
      try {
        const result = parseVerification(body);
        if (result.claim !== submittedClaim)
          throw new Error("Mismatched claim");
        setState({ status: "success", result });
      } catch {
        setState({ status: "error", code: "INVALID_RESPONSE" });
      }
    } catch {
      if (!controller.signal.aborted)
        setState({ status: "error", code: "SERVICE_UNAVAILABLE" });
    } finally {
      requestRef.current = null;
    }
  }

  const error =
    state.status === "error"
      ? (ERRORS[state.code] ?? ERRORS.VERIFICATION_FAILED)
      : null;

  return (
    <section
      className="verifier content-width"
      aria-label="Legal claim verification"
    >
      <form className="claim-form" onSubmit={verify} aria-busy={loading}>
        <div className="input-heading">
          <label htmlFor="claim">Your legal claim</label>
          <span>Start with a statement. Follow the evidence.</span>
        </div>
        <textarea
          ref={textareaRef}
          id="claim"
          name="claim"
          value={claim}
          onChange={(event) => updateClaim(event.target.value)}
          placeholder="A controller must report a personal data breach within 24 hours."
          maxLength={1000}
          rows={3}
          readOnly={loading}
          aria-invalid={!!validation}
          aria-describedby={
            validation ? "claim-error claim-hint" : "claim-hint"
          }
          onKeyDown={(event) => {
            if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
              event.preventDefault();
              void verify();
            }
          }}
        />
        {validation && (
          <p className="field-error" id="claim-error" role="alert">
            {validation}
          </p>
        )}
        <div className="input-footer">
          <span id="claim-hint">
            One claim at a time, up to 1,000 characters.
          </span>
          <span className="character-count" aria-hidden="true">
            {claim.length.toLocaleString()} / 1,000
          </span>
        </div>
        <div className="form-toolbar">
          <div className="corpus">
            <DocumentIcon />
            <div>
              <span className="corpus-label">VERIFY AGAINST</span>
              <span>
                EU GDPR <span className="muted">· Official Journal</span>
              </span>
            </div>
          </div>
          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? "Verifying claim" : "Verify claim"}
            {loading ? <span className="button-activity" /> : <ArrowIcon />}
          </button>
        </div>
      </form>
      <div className="examples">
        <p className="examples-label">
          A place to start <span>Try an example</span>
        </p>
        <div className="example-grid">
          {EXAMPLES.map((example) => (
            <button
              type="button"
              className="example-button"
              key={example.label}
              disabled={loading}
              onClick={() => {
                updateClaim(example.claim);
                textareaRef.current?.focus();
              }}
            >
              <span>
                <span className="example-topic">{example.topic}</span>
                <span className="example-title">{example.label}</span>
              </span>
              <ArrowIcon diagonal />
            </button>
          ))}
        </div>
      </div>
      <div
        className="request-announcement sr-only"
        aria-live="polite"
        aria-atomic="true"
      >
        {state.status === "success"
          ? `Verification complete: ${state.result.verdict.replaceAll("_", " ")}.`
          : ""}
      </div>
      {loading && <VerificationProgress />}
      {error && (
        <div
          className="error-state result-reveal"
          role="alert"
          ref={resultRef}
          tabIndex={-1}
        >
          <div>
            <span className="eyebrow">VERIFICATION UNAVAILABLE</span>
            <h2>{error.title}</h2>
            <p>{error.message}</p>
          </div>
          <button className="secondary-button" onClick={() => void verify()}>
            Try again <ArrowIcon />
          </button>
        </div>
      )}
      {state.status === "success" && (
        <div
          ref={resultRef}
          tabIndex={-1}
          className="result-focus"
          aria-label="Verification result"
        >
          <VerificationReport result={state.result} />
        </div>
      )}
    </section>
  );
}
