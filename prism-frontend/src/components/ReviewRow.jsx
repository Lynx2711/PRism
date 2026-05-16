import { useState } from 'react';
import { ChevronDown, ChevronUp, Shield, AlertTriangle, Info } from 'lucide-react';
import './ReviewRow.css';

export default function ReviewRow({ review }) {
  const [expanded, setExpanded] = useState(false);

  const statusMap = { pending: 'pending', processing: 'processing', complete: 'complete', failed: 'failed' };

  const riskLevel = (score) => {
    if (score >= 0.7) return { label: 'High', className: 'risk-high' };
    if (score >= 0.4) return { label: 'Medium', className: 'risk-medium' };
    return { label: 'Low', className: 'risk-low' };
  };

  const risk = review.codebert_risk != null ? riskLevel(review.codebert_risk) : null;

  const date = review.created_at
    ? new Date(review.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    : '';

  return (
    <div className={`review-row ${expanded ? 'expanded' : ''}`} id={`review-${review.event_id}`}>
      <div className="review-row-main" onClick={() => setExpanded(!expanded)}>
        <div className="review-col review-pr">
          <span className="review-pr-number">#{review.pr_number}</span>
          <div className="review-pr-info">
            <span className="review-pr-title">{review.pr_title}</span>
            <span className="review-pr-author">by {review.pr_author}</span>
          </div>
        </div>
        <div className="review-col review-status-col">
          <span className={`badge badge-${statusMap[review.status] || 'pending'}`}>{review.status}</span>
        </div>
        <div className="review-col review-issues-col">
          {review.scanner_issues ? (
            <div className="review-issues">
              {review.scanner_issues.critical > 0 && <span className="issue-count critical"><Shield size={12} />{review.scanner_issues.critical}</span>}
              {review.scanner_issues.high > 0 && <span className="issue-count high"><AlertTriangle size={12} />{review.scanner_issues.high}</span>}
              <span className="issue-total">{review.scanner_issues.total || 0} total</span>
            </div>
          ) : <span className="issue-none">—</span>}
        </div>
        <div className="review-col review-risk-col">
          {risk ? (
            <div className={`review-risk ${risk.className}`}>
              <span className="risk-score">{review.codebert_risk.toFixed(2)}</span>
              <span className="risk-label">{risk.label}</span>
            </div>
          ) : <span className="issue-none">—</span>}
        </div>
        <div className="review-col review-date-col"><span className="review-date">{date}</span></div>
        <div className="review-col review-expand-col">{expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}</div>
      </div>

      {expanded && review.scanner_issues && (
        <div className="review-row-details">
          <div className="review-details-header"><Info size={14} /><span>Scanner Findings</span></div>
          <div className="review-findings-grid">
            <div className="finding-stat"><span className="finding-stat-value critical">{review.scanner_issues.critical || 0}</span><span className="finding-stat-label">Critical</span></div>
            <div className="finding-stat"><span className="finding-stat-value high">{review.scanner_issues.high || 0}</span><span className="finding-stat-label">High</span></div>
            <div className="finding-stat"><span className="finding-stat-value medium">{(review.scanner_issues.total || 0) - (review.scanner_issues.critical || 0) - (review.scanner_issues.high || 0)}</span><span className="finding-stat-label">Other</span></div>
          </div>
          {review.codebert_risk != null && (
            <div className="review-codebert-detail">
              <span className="detail-label">CodeBERT Risk Score</span>
              <div className="risk-bar-track">
                <div className={`risk-bar-fill ${risk.className}`} style={{ width: `${Math.round(review.codebert_risk * 100)}%` }}></div>
              </div>
              <span className={`risk-value ${risk.className}`}>{(review.codebert_risk * 100).toFixed(0)}%</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
