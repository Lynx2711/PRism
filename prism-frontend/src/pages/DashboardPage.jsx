import { useState, useEffect } from 'react';
import { Plus, Loader2, GitFork, X } from 'lucide-react';
import API from '../api/axios';
import Sidebar from '../components/Sidebar';
import RepoCard from '../components/RepoCard';
import './DashboardPage.css';

export default function DashboardPage() {
  const [repos, setRepos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [repoName, setRepoName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const fetchRepos = async () => {
    try {
      const res = await API.get('/api/repos/');
      setRepos(res.data);
    } catch (err) {
      console.error('Failed to fetch repos:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRepos();
  }, []);

  const handleConnect = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await API.post('/api/repos/', { repo_full_name: repoName });
      setRepoName('');
      setModalOpen(false);
      fetchRepos();
    } catch (err) {
      setError(err.response?.data?.detail || err.response?.data?.repo_full_name?.[0] || 'Failed to connect repository.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="dashboard-layout" id="dashboard-page">
      <Sidebar />

      <main className="dashboard-main">
        <div className="dashboard-header">
          <div>
            <h1 className="dashboard-title">Your Repositories</h1>
            <p className="dashboard-subtitle">
              {repos.length} {repos.length === 1 ? 'repository' : 'repositories'} connected
            </p>
          </div>
          <button
            className="btn-primary"
            onClick={() => setModalOpen(true)}
            id="connect-repo-btn"
          >
            <Plus size={16} />
            Connect Repository
          </button>
        </div>

        {loading ? (
          <div className="dashboard-loading">
            <div className="spinner"></div>
            <span>Loading repositories...</span>
          </div>
        ) : repos.length === 0 ? (
          <div className="empty-state">
            <GitFork size={48} />
            <h3>No repositories connected</h3>
            <p>Connect your first GitHub repository to start reviewing PRs with AI.</p>
            <button className="btn-primary" onClick={() => setModalOpen(true)}>
              <Plus size={16} />
              Connect Repository
            </button>
          </div>
        ) : (
          <div className="repos-grid">
            {repos.map((repo) => (
              <RepoCard key={repo.id} repo={repo} />
            ))}
          </div>
        )}
      </main>

      {/* Connect Repo Modal */}
      {modalOpen && (
        <div className="modal-overlay" onClick={() => setModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">Connect Repository</h2>
              <button className="btn-ghost modal-close" onClick={() => setModalOpen(false)}>
                <X size={18} />
              </button>
            </div>

            {error && <div className="auth-error" style={{ marginBottom: 16 }}>{error}</div>}

            <form onSubmit={handleConnect}>
              <div className="form-group">
                <label className="form-label" htmlFor="repo-name">Repository Full Name</label>
                <input
                  id="repo-name"
                  type="text"
                  className="form-input"
                  placeholder="owner/repository"
                  value={repoName}
                  onChange={(e) => setRepoName(e.target.value)}
                  required
                  autoFocus
                />
                <span className="form-hint">Enter the full name like <code>Lynx2711/backend</code></span>
              </div>

              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={submitting} id="connect-submit">
                  {submitting ? <Loader2 size={16} className="spin" /> : <Plus size={16} />}
                  {submitting ? 'Connecting...' : 'Connect'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
