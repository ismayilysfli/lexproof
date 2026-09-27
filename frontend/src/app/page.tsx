import { ClaimVerifier } from "@/components/claim-verifier";
import { ArrowIcon, DocumentIcon } from "@/components/icons";
import Link from "next/link";

export default function Home() {
  return (
    <>
      <a className="skip-link" href="#claim">
        Skip to verification
      </a>
      <header className="site-header">
        <Link className="wordmark" href="/" aria-label="LexProof home">
          Lex<span>Proof</span>
          <span className="brand-period">.</span>
        </Link>
        <nav aria-label="Main navigation">
          <a href="#how-it-works">
            How it works <ArrowIcon diagonal />
          </a>
        </nav>
      </header>
      <main id="main-content">
        <section className="hero" aria-labelledby="hero-title">
          <div className="eyebrow">
            <span className="tiny-rule" /> EVIDENCE BEFORE CONFIDENCE
          </div>
          <h1 id="hero-title">
            Can this legal claim
            <br />
            be <span>trusted?</span>
          </h1>
          <p>
            Verify an AI-generated legal statement against
            <br className="desktop-break" /> authoritative legal sources.
          </p>
          <div
            className="workflow"
            aria-label="Claim to primary law to evidence to verdict"
          >
            <span>Claim</span>
            <ArrowIcon />
            <span>Primary law</span>
            <ArrowIcon />
            <span>Evidence</span>
            <ArrowIcon />
            <span>Verdict</span>
          </div>
        </section>
        <ClaimVerifier />
        <section
          className="how-it-works content-width"
          id="how-it-works"
          aria-labelledby="how-title"
        >
          <div className="section-heading">
            <span className="eyebrow">FROM STATEMENT TO SOURCE</span>
            <h2 id="how-title">A claim is only as strong as its evidence.</h2>
          </div>
          <ol className="steps">
            <li>
              <span className="step-number">01</span>
              <div>
                <h3>Search</h3>
                <p>Find relevant primary law.</p>
              </div>
            </li>
            <li>
              <span className="step-number">02</span>
              <div>
                <h3>Verify</h3>
                <p>Compare the claim against legal evidence.</p>
              </div>
            </li>
            <li>
              <span className="step-number">03</span>
              <div>
                <h3>Prove</h3>
                <p>Return a verdict with article, page, and source evidence.</p>
              </div>
            </li>
          </ol>
          <p className="principles">
            <DocumentIcon />
            <span>
              Local AI <span aria-hidden="true">·</span> No paid legal API{" "}
              <span aria-hidden="true">·</span> Evidence-first verification
            </span>
          </p>
        </section>
      </main>
      <footer className="site-footer">
        <span className="footer-brand">LexProof</span>
        <p>Verify AI legal claims against primary law.</p>
        <span>Automated evidence analysis. Not legal advice.</span>
      </footer>
    </>
  );
}
