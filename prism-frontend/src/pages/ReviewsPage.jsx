import { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Wifi, WifiOff, RefreshCw, FileSearch } from 'lucide-react';
import API from '../api/axios';
import Sidebar from '../components/Sidebar';
import ReviewRow from '../components/ReviewRow';
import Toast from '../components/Toast';
import './ReviewsPage.css';

export default function ReviewsPage() {
  const { id } = useParams();
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);
  const [toasts, setToasts] = useState([]);
  const wsRef = useRef(null);
  const toastIdRef = useRef(0);

  const fetchReviews = async () => {
    try {
      const res = await API.get(`/api/repos/${id}/reviews/`);
      setReviews(res.data);
    } catch (err) {
      console.error('Failed to fetch reviews:', err);
    } finally {
      setLoading(false);
    }
  };

  const addToast = (message, type = 'success') => {
    const toastId = ++toastIdRef.current;
    setToasts((prev) => [...prev, { id: toastId, message, type }]);
  };

  const removeToast = (toastId) => {
    setToasts((prev) => prev.filter((t) => t.id !== toastId));
  };

  useEffect(() => {
    fetchReviews();
  }, [id]);

  // WebSocket connection
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    const wsUrl = `ws://localhost:8000/ws/repos/${id}/reviews/?token=${token}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'review_complete') {
          const updatedReview = data;
          setReviews((prev) => {
            const exists = prev.find((r) => r.event_id === updatedReview.event_id);
            if (exists) {
              return prev.map((r) =>
                r.event_id === updatedReview.event_id ? { ...r, ...updatedReview } : r
              );
            }
            return [updatedReview, ...prev];
          });
          addToast(`PR #${updatedReview.pr_number} analysis complete`);
        }
      } catch (err) {
        console.error('WebSocket message parse error:', err);
      }
    };

    ws.onclose = () => {
      setWsConnected(false);
    };

    ws.onerror = () => {
      setWsConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [id]);

  return (
    <div className="dashboard-layout" id="reviews-page">
      <Sidebar />

      <main className="dashboard-main">
        <div className="reviews-header">
          <div className="reviews-header-left">
            <Link to="/dashboard" className="back-link">
              <ArrowLeft size={16} />
              Back
            </Link>
            <div>
              <h1 className="dashboard-title">Pull Request Reviews</h1>
              <p className="dashboard-subtitle">{reviews.length} reviews</p>
            </div>
          </div>
          <div className="reviews-header-right">
            <div className={`ws-indicator ${wsConnected ? 'connected' : 'disconnected'}`}>
              {wsConnected ? <Wifi size={14} /> : <WifiOff size={14} />}
              {wsConnected ? 'Live' : 'Offline'}
            </div>
            <button className="btn-secondary" onClick={() => { setLoading(true); fetchReviews(); }} id="refresh-reviews">
              <RefreshCw size={14} />
              Refresh
            </button>
          </div>
        </div>

        {/* Table Header */}
        <div className="reviews-table-header">
          <div className="review-col-header" style={{ flex: 2 }}>Pull Request</div>
          <div className="review-col-header" style={{ width: 100 }}>Status</div>
          <div className="review-col-header" style={{ width: 140 }}>Issues</div>
          <div className="review-col-header" style={{ width: 120 }}>Risk Score</div>
          <div className="review-col-header" style={{ width: 110 }}>Date</div>
          <div className="review-col-header" style={{ width: 40 }}></div>
        </div>

        {loading ? (
          <div className="dashboard-loading">
            <div className="spinner"></div>
            <span>Loading reviews...</span>
          </div>
        ) : reviews.length === 0 ? (
          <div className="empty-state">
            <FileSearch size={48} />
            <h3>No reviews yet</h3>
            <p>Reviews will appear here when Pull Requests are analyzed.</p>
          </div>
        ) : (
          <div className="reviews-list">
            {reviews.map((review) => (
              <ReviewRow key={review.event_id} review={review} />
            ))}
          </div>
        )}
      </main>

      {/* Toast Notifications */}
      <div className="toast-container">
        {toasts.map((toast) => (
          <Toast
            key={toast.id}
            message={toast.message}
            type={toast.type}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </div>
    </div>
  );
}
