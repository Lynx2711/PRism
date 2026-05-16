import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Settings, Save, Loader2 } from 'lucide-react';
import API from '../api/axios';
import Sidebar from '../components/Sidebar';
import './ConfigPage.css';

export default function ConfigPage() {
  const { id } = useParams();
  const [config, setConfig] = useState({
    max_function_lines: 50,
    enforce_naming: false,
    run_security_scanner: true,
    run_codebert: true,
    notify_on_critical: true,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const res = await API.get(`/api/repos/${id}/reviews/`);
        // The repo config comes from the repo endpoint
        const repoRes = await API.get('/api/repos/');
        const repo = repoRes.data.find((r) => String(r.id) === String(id));
        if (repo && repo.config) {
          setConfig((prev) => ({ ...prev, ...repo.config }));
        }
      } catch (err) {
        console.error('Failed to fetch config:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchConfig();
  }, [id]);

  const handleToggle = (key) => {
    setConfig((prev) => ({ ...prev, [key]: !prev[key] }));
    setSaved(false);
  };

  const handleNumberChange = (key, value) => {
    setConfig((prev) => ({ ...prev, [key]: parseInt(value) || 0 }));
    setSaved(false);
  };

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      await API.patch(`/api/repos/${id}/config/`, { config });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error('Failed to save config:', err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="dashboard-layout" id="config-page">
        <Sidebar />
        <main className="dashboard-main">
          <div className="dashboard-loading">
            <div className="spinner"></div>
            <span>Loading configuration...</span>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="dashboard-layout" id="config-page">
      <Sidebar />

      <main className="dashboard-main">
        <div className="reviews-header">
          <div className="reviews-header-left">
            <Link to="/dashboard" className="back-link">
              <ArrowLeft size={16} />
              Back
            </Link>
            <div>
              <h1 className="dashboard-title">Repository Configuration</h1>
              <p className="dashboard-subtitle">Customize review settings</p>
            </div>
          </div>
        </div>

        <div className="config-card">
          <div className="config-section">
            <h3 className="config-section-title">
              <Settings size={16} />
              Analysis Settings
            </h3>

            <div className="config-field">
              <div className="config-field-info">
                <label className="config-label" htmlFor="max-func-lines">Max Function Lines</label>
                <p className="config-desc">Flag functions exceeding this line count</p>
              </div>
              <input
                id="max-func-lines"
                type="number"
                className="form-input config-number-input"
                value={config.max_function_lines}
                onChange={(e) => handleNumberChange('max_function_lines', e.target.value)}
                min="10"
                max="500"
              />
            </div>

            <div className="toggle-wrapper">
              <div className="config-field-info">
                <span className="config-label">Enforce Naming Conventions</span>
                <p className="config-desc">Check variable and function naming patterns</p>
              </div>
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={config.enforce_naming}
                  onChange={() => handleToggle('enforce_naming')}
                  id="toggle-naming"
                />
                <span className="toggle-slider"></span>
              </label>
            </div>

            <div className="toggle-wrapper">
              <div className="config-field-info">
                <span className="config-label">Run Security Scanner</span>
                <p className="config-desc">Detect hardcoded secrets, API keys, and injections</p>
              </div>
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={config.run_security_scanner}
                  onChange={() => handleToggle('run_security_scanner')}
                  id="toggle-scanner"
                />
                <span className="toggle-slider"></span>
              </label>
            </div>

            <div className="toggle-wrapper">
              <div className="config-field-info">
                <span className="config-label">Run CodeBERT Analysis</span>
                <p className="config-desc">AI-powered risk scoring for code changes</p>
              </div>
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={config.run_codebert}
                  onChange={() => handleToggle('run_codebert')}
                  id="toggle-codebert"
                />
                <span className="toggle-slider"></span>
              </label>
            </div>

            <div className="toggle-wrapper">
              <div className="config-field-info">
                <span className="config-label">Notify on Critical Issues</span>
                <p className="config-desc">Send alerts when critical vulnerabilities are found</p>
              </div>
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={config.notify_on_critical}
                  onChange={() => handleToggle('notify_on_critical')}
                  id="toggle-notify"
                />
                <span className="toggle-slider"></span>
              </label>
            </div>
          </div>

          <div className="config-actions">
            {saved && <span className="config-saved-msg">✓ Configuration saved</span>}
            <button
              className="btn-primary"
              onClick={handleSave}
              disabled={saving}
              id="save-config"
            >
              {saving ? <Loader2 size={16} className="spin" /> : <Save size={16} />}
              {saving ? 'Saving...' : 'Save Configuration'}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
