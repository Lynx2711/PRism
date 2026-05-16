import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, BarChart3, AlertTriangle, Shield, TrendingUp, Users, FileWarning } from 'lucide-react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import API from '../api/axios';
import Sidebar from '../components/Sidebar';
import StatCard from '../components/StatCard';
import './AnalyticsPage.css';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="chart-tooltip">
        <p className="chart-tooltip-label">{label}</p>
        {payload.map((p, i) => (
          <p key={i} className="chart-tooltip-value" style={{ color: p.color }}>
            {p.name}: {typeof p.value === 'number' ? p.value.toFixed(2) : p.value}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

export default function AnalyticsPage() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const res = await API.get(`/api/repos/${id}/analytics/`);
        setData(res.data);
      } catch (err) {
        console.error('Failed to fetch analytics:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, [id]);

  if (loading) {
    return (
      <div className="dashboard-layout" id="analytics-page">
        <Sidebar />
        <main className="dashboard-main">
          <div className="dashboard-loading">
            <div className="spinner"></div>
            <span>Loading analytics...</span>
          </div>
        </main>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="dashboard-layout" id="analytics-page">
        <Sidebar />
        <main className="dashboard-main">
          <div className="empty-state">
            <BarChart3 size={48} />
            <h3>No analytics data</h3>
            <p>Analytics will appear after PRs are reviewed.</p>
          </div>
        </main>
      </div>
    );
  }

  const riskTrendData = (data.risk_trend || []).map((item, i) => ({
    name: `PR ${i + 1}`,
    risk: item.risk_score || item,
  }));

  const fileData = (data.most_problematic_files || []).map((f) => ({
    name: typeof f === 'string' ? f : f.file || f.name,
    issues: typeof f === 'object' ? (f.count || f.issues || 0) : 0,
  }));

  return (
    <div className="dashboard-layout" id="analytics-page">
      <Sidebar />

      <main className="dashboard-main">
        <div className="reviews-header">
          <div className="reviews-header-left">
            <Link to="/dashboard" className="back-link">
              <ArrowLeft size={16} />
              Back
            </Link>
            <h1 className="dashboard-title">Analytics</h1>
          </div>
        </div>

        {/* Stat Cards */}
        <div className="analytics-stats">
          <StatCard
            icon={<BarChart3 size={22} />}
            label="Total PRs Reviewed"
            value={data.total_prs_reviewed || 0}
            color="purple"
          />
          <StatCard
            icon={<AlertTriangle size={22} />}
            label="Total Issues Found"
            value={data.total_issues_found || 0}
            color="amber"
          />
          <StatCard
            icon={<Shield size={22} />}
            label="Critical Issues"
            value={data.issues_by_severity?.critical || 0}
            color="red"
          />
          <StatCard
            icon={<TrendingUp size={22} />}
            label="High Issues"
            value={data.issues_by_severity?.high || 0}
            color="amber"
          />
        </div>

        {/* Charts Row */}
        <div className="analytics-charts">
          {/* Risk Trend */}
          <div className="analytics-chart-card">
            <h3 className="chart-title">
              <TrendingUp size={16} />
              Risk Trend
            </h3>
            {riskTrendData.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={riskTrendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="name" tick={{ fill: '#94A3B8', fontSize: 11 }} axisLine={{ stroke: 'rgba(255,255,255,0.08)' }} />
                  <YAxis domain={[0, 1]} tick={{ fill: '#94A3B8', fontSize: 11 }} axisLine={{ stroke: 'rgba(255,255,255,0.08)' }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Line type="monotone" dataKey="risk" stroke="#7C3AED" strokeWidth={2} dot={{ fill: '#7C3AED', r: 4 }} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="chart-empty">No risk data yet</div>
            )}
          </div>

          {/* Most Problematic Files */}
          <div className="analytics-chart-card">
            <h3 className="chart-title">
              <FileWarning size={16} />
              Most Problematic Files
            </h3>
            {fileData.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={fileData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis type="number" tick={{ fill: '#94A3B8', fontSize: 11 }} axisLine={{ stroke: 'rgba(255,255,255,0.08)' }} />
                  <YAxis dataKey="name" type="category" width={140} tick={{ fill: '#94A3B8', fontSize: 11 }} axisLine={{ stroke: 'rgba(255,255,255,0.08)' }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="issues" fill="#0EA5E9" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="chart-empty">No file data yet</div>
            )}
          </div>
        </div>

        {/* Bottom Row */}
        <div className="analytics-bottom">
          {/* Top Patterns */}
          <div className="analytics-card">
            <h3 className="chart-title">
              <Shield size={16} />
              Top Patterns
            </h3>
            <div className="patterns-list">
              {(data.top_patterns || []).length > 0 ? (
                data.top_patterns.map((p, i) => (
                  <div key={i} className="pattern-item">
                    <div className="pattern-info">
                      <span className="pattern-name">{p.pattern || p.name || p}</span>
                      {p.severity && (
                        <span className={`badge badge-${p.severity}`}>{p.severity}</span>
                      )}
                    </div>
                    <span className="pattern-count">{p.count || p.occurrences || 0}</span>
                  </div>
                ))
              ) : (
                <div className="chart-empty">No patterns detected</div>
              )}
            </div>
          </div>

          {/* Author Stats */}
          <div className="analytics-card">
            <h3 className="chart-title">
              <Users size={16} />
              Author Stats
            </h3>
            {(data.author_stats || []).length > 0 ? (
              <div className="author-table">
                <div className="author-table-header">
                  <span>Author</span>
                  <span>PRs</span>
                  <span>Issues</span>
                </div>
                {data.author_stats.map((a, i) => (
                  <div key={i} className="author-row">
                    <span className="author-name">{a.author || a.name}</span>
                    <span className="author-prs">{a.prs || a.pr_count || 0}</span>
                    <span className="author-issues">{a.issues || a.issue_count || 0}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="chart-empty">No author data yet</div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
