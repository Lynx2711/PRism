import { Link } from 'react-router-dom';
import { GitFork, Calendar, Eye, BarChart3 } from 'lucide-react';
import './RepoCard.css';

export default function RepoCard({ repo }) {
  const connectedDate = repo.connected_at
    ? new Date(repo.connected_at).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
    : 'N/A';

  return (
    <div className="repo-card" id={`repo-card-${repo.id}`}>
      <div className="repo-card-header">
        <div className="repo-card-icon">
          <GitFork size={20} />
        </div>
        <div className="repo-card-info">
          <h3 className="repo-card-name">{repo.repo_full_name}</h3>
          {repo.team_name && (
            <span className="repo-card-team">{repo.team_name}</span>
          )}
        </div>
        <div className={`repo-card-status ${repo.is_active ? 'active' : 'inactive'}`}>
          <div className="status-dot"></div>
          {repo.is_active ? 'Active' : 'Inactive'}
        </div>
      </div>

      <div className="repo-card-meta">
        <div className="repo-card-meta-item">
          <Calendar size={14} />
          <span>Connected {connectedDate}</span>
        </div>
      </div>

      <div className="repo-card-actions">
        <Link
          to={`/repos/${repo.id}/reviews`}
          className="btn-secondary repo-card-btn"
          id={`view-reviews-${repo.id}`}
        >
          <Eye size={14} />
          View Reviews
        </Link>
        <Link
          to={`/repos/${repo.id}/analytics`}
          className="btn-ghost repo-card-btn"
          id={`view-analytics-${repo.id}`}
        >
          <BarChart3 size={14} />
          Analytics
        </Link>
      </div>
    </div>
  );
}
