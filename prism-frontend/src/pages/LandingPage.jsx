import { Link } from 'react-router-dom';
import { Shield, Brain, GitBranch, ArrowRight, ChevronDown } from 'lucide-react';
import './LandingPage.css';

export default function LandingPage() {
  return (
    <div className="landing" id="landing-page">
      {/* ── Navbar ── */}
      <nav className="landing-nav">
        <div className="landing-logo">
          <div className="landing-logo-icon">P</div>
          <span>PR<span className="logo-accent">ism</span></span>
        </div>
        <Link to="/login" className="btn-secondary" id="landing-signin">
          Sign In
        </Link>
      </nav>

      {/* ── Hero ── */}
      <section className="hero">
        <div className="hero-orb hero-orb-1"></div>
        <div className="hero-orb hero-orb-2"></div>
        <div className="hero-orb hero-orb-3"></div>
        <div className="hero-grid"></div>

        <div className="hero-badge">
          <div className="hero-badge-dot"></div>
          Now with CodeBERT + Knowledge Graph
        </div>

        <h1 className="hero-title">
          Code Review,<br />
          <span className="hero-accent-purple">Reimagined</span>
        </h1>

        <p className="hero-subtitle">
          PRism analyzes every Pull Request automatically — security vulnerabilities, 
          AI risk scoring, and insights that improve the longer you use it.
        </p>

        <div className="hero-actions">
          <Link to="/register" className="btn-primary hero-cta" id="hero-get-started">
            Get Started
            <ArrowRight size={16} />
          </Link>
          <a href="#features" className="btn-ghost hero-cta-secondary">
            <ChevronDown size={16} />
            Learn More
          </a>
        </div>

        {/* Terminal Preview */}
        <div className="hero-terminal">
          <div className="terminal-bar">
            <div className="terminal-dots">
              <span className="dot dot-red"></span>
              <span className="dot dot-yellow"></span>
              <span className="dot dot-green"></span>
            </div>
            <span className="terminal-title">PRism — analyzing PR #47</span>
          </div>
          <div className="terminal-body">
            <div className="t-line"><span className="t-dim">$</span> <span className="t-teal">prism</span> <span className="t-white">analyze</span> <span className="t-dim">Lynx2711/backend #47</span></div>
            <div className="t-line">&nbsp;</div>
            <div className="t-line"><span className="t-dim">▸ fetching diff...</span> <span className="t-green">3 files changed (+127 -23)</span></div>
            <div className="t-line"><span className="t-dim">▸ security scan...</span> <span className="t-red">2 CRITICAL findings</span></div>
            <div className="t-line">  <span className="t-dim">auth.py:4</span>  <span className="t-amber">[CRITICAL]</span> <span className="t-white">Hardcoded API key detected</span></div>
            <div className="t-line">  <span className="t-dim">config.py:1</span> <span className="t-amber">[CRITICAL]</span> <span className="t-white">Hardcoded password detected</span></div>
            <div className="t-line"><span className="t-dim">▸ CodeBERT analysis...</span> <span className="t-purple">risk score 0.87 (HIGH)</span></div>
            <div className="t-line"><span className="t-dim">▸ knowledge graph...</span> <span className="t-teal">auth.py ↔ permissions.py usually change together</span></div>
            <div className="t-line"><span className="t-dim">▸ posting 3 inline comments to GitHub...</span> <span className="t-green">done</span></div>
            <div className="t-line">&nbsp;</div>
            <div className="t-line"><span className="t-green">✓ Review complete</span> <span className="t-dim">in 12.4s — 3 issues flagged</span> <span className="cursor-blink"></span></div>
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section className="features" id="features">
        <div className="section-header">
          <span className="section-tag">Features</span>
          <h2 className="section-title">Three layers of intelligent analysis</h2>
          <p className="section-subtitle">Each one smarter than any single tool.</p>
        </div>

        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon feature-icon--red">
              <Shield size={24} />
            </div>
            <h3 className="feature-name">Security Scanner</h3>
            <p className="feature-desc">
              Detects hardcoded secrets, API keys, and SQL injection before code ships.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon feature-icon--purple">
              <Brain size={24} />
            </div>
            <h3 className="feature-name">CodeBERT Analysis</h3>
            <p className="feature-desc">
              Microsoft's code understanding model scores every diff for risk patterns.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon feature-icon--teal">
              <GitBranch size={24} />
            </div>
            <h3 className="feature-name">Stateful Knowledge Graph</h3>
            <p className="feature-desc">
              PRism remembers your codebase. Reviews improve with every PR analyzed.
            </p>
          </div>
        </div>
      </section>

      {/* ── Stats Bar ── */}
      <div className="stats-bar">
        <div className="stats-bar-inner">
          <div className="stat-item">
            <span className="stat-value">10k+</span>
            <span className="stat-label">PRs Reviewed</span>
          </div>
          <div className="stat-divider"></div>
          <div className="stat-item">
            <span className="stat-value">99.2%</span>
            <span className="stat-label">Uptime</span>
          </div>
          <div className="stat-divider"></div>
          <div className="stat-item">
            <span className="stat-value">&lt; 30s</span>
            <span className="stat-label">Analysis Time</span>
          </div>
          <div className="stat-divider"></div>
          <div className="stat-item">
            <span className="stat-value">SOC2</span>
            <span className="stat-label">Ready</span>
          </div>
        </div>
      </div>

      {/* ── Footer ── */}
      <footer className="landing-footer">
        <p>PRism — Built for engineering teams that ship fast</p>
      </footer>
    </div>
  );
}
