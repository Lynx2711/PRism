<p align="center">
  <img src="https://img.shields.io/badge/PRism-AI%20Code%20Review-blueviolet?style=for-the-badge&logo=github" alt="PRism Badge" />
  <img src="https://img.shields.io/badge/Django-5.2-092E20?style=for-the-badge&logo=django" alt="Django" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react" alt="React" />
  <img src="https://img.shields.io/badge/CodeBERT-Microsoft-orange?style=for-the-badge" alt="CodeBERT" />
</p>

# 🔬 PRism — AI-Powered GitHub Code Review Platform

**PRism** is a full-stack, AI-powered code review platform that automatically analyzes pull requests on your GitHub repositories. It combines Microsoft's **CodeBERT** deep learning model with a **rule-based security scanner** and a **knowledge graph** that learns from your codebase over time — delivering context-aware, intelligent reviews directly on your PRs.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🤖 **CodeBERT Analysis** | Uses Microsoft's CodeBERT transformer model to compute semantic risk scores for every code change |
| 🔒 **Security Scanner** | Rule-based pattern matching catches hardcoded secrets, SQL injection risks, debug flags, and more |
| 🧠 **Knowledge Graph** | A per-repository graph (built with NetworkX) that remembers file coupling, recurring patterns, and author ownership — making reviews smarter over time |
| 🔔 **Real-Time Notifications** | WebSocket-powered live updates via Django Channels — see review results the moment they're ready |
| 👥 **Multi-Tenant Teams** | Team-based isolation with admin/member roles, per-repo configuration, and GitHub org integration |
| 📊 **Analytics Dashboard** | Visual insights into review trends, severity distributions, top hotspot files, and more |
| ⚙️ **Per-Repo Configuration** | Customize review rules per repository — max function lines, naming enforcement, scanner toggles |
| 🔗 **GitHub App Integration** | Installs as a GitHub App, receives webhooks on PR events, and posts review comments directly on the PR |

---

## 🏗️ Architecture

```
┌─────────────────┐       Webhook        ┌──────────────────────────┐
│   GitHub         │ ──────────────────▸  │   Django REST Backend    │
│   (PR opened)    │                      │   (Daphne ASGI Server)   │
└─────────────────┘                      └────────┬─────────────────┘
                                                  │
                                    ┌─────────────┼──────────────┐
                                    ▼             ▼              ▼
                              ┌──────────┐ ┌───────────┐ ┌────────────┐
                              │  Celery   │ │  Channels  │ │  REST API  │
                              │  Worker   │ │ WebSocket  │ │  Endpoints │
                              └────┬─────┘ └───────────┘ └────────────┘
                                   │
                     ┌─────────────┼──────────────┐
                     ▼             ▼              ▼
               ┌──────────┐ ┌───────────┐ ┌────────────────┐
               │ Security  │ │  CodeBERT  │ │  Knowledge     │
               │ Scanner   │ │  Analyzer  │ │  Graph Engine  │
               └──────────┘ └───────────┘ └────────────────┘
                                   │
                                   ▼
                        ┌────────────────────┐
                        │  PyGithub → Posts   │
                        │  comments on PR    │
                        └────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                React Frontend (Vite)                      │
│  Landing • Auth • Dashboard • Reviews • Analytics • Config│
└──────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
PRism/
├── config/                 # Django project settings
│   ├── settings.py         # Main settings (env-based, no hardcoded secrets)
│   ├── urls.py             # Root URL configuration
│   ├── asgi.py             # ASGI app with Channels routing
│   ├── celery.py           # Celery app configuration
│   └── routing.py          # WebSocket URL routing
│
├── webhooks/               # GitHub webhook handling
│   ├── models.py           # PullRequestEvent model
│   ├── views.py            # Webhook receiver (signature verification)
│   ├── tasks.py            # Celery tasks — orchestrates the full review pipeline
│   └── utils.py            # GitHub App authentication helpers
│
├── reviews/                # AI analysis engine
│   ├── analyzer.py         # CodeBERT-based risk scoring
│   ├── scanner.py          # Regex-based security pattern scanner
│   ├── knowledge_graph.py  # NetworkX-powered repository knowledge graph
│   ├── analytics.py        # Aggregated analytics queries
│   ├── consumers.py        # WebSocket consumer for live notifications
│   └── middleware.py        # JWT auth middleware for WebSocket connections
│
├── teams/                  # Multi-tenant user & team management
│   ├── models.py           # User, Team, TeamMembership, RepositoryConfig
│   ├── serializers.py      # DRF serializers
│   ├── views.py            # Auth, team, repo, review, analytics API views
│   └── urls.py             # API URL routing
│
├── prism-frontend/         # React frontend (Vite)
│   ├── src/
│   │   ├── api/            # Axios instance with JWT interceptors
│   │   ├── components/     # Navbar, Sidebar, RepoCard, ReviewRow, StatCard, Toast
│   │   ├── pages/          # Landing, Login, Register, Dashboard, Reviews, Analytics, Config
│   │   ├── App.jsx         # Route definitions
│   │   └── index.css       # Global styles & design tokens
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── docker-compose.yml      # PostgreSQL + Redis containers
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── manage.py               # Django management script
└── README.md
```

---

## 🛠️ Prerequisites

Before setting up PRism, make sure you have:

- **Python 3.11+**
- **Node.js 18+** and **npm 9+**
- **PostgreSQL 15+**
- **Redis 7+**
- **Docker & Docker Compose** (optional — for running Postgres & Redis)
- **Git**
- A **GitHub App** configured to receive webhook events (see [GitHub App Setup](#-github-app-setup))

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/Lynx2711/PRism.git
cd PRism
```

### 2. Set Up Infrastructure (PostgreSQL & Redis)

**Option A — Docker (recommended):**

```bash
# Create your .env file first (see Step 3), then:
docker-compose up -d
```

**Option B — Local installations:**

- Install and start PostgreSQL, create a database named `codesense`
- Install and start Redis on the default port (`6379`)

### 3. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```ini
SECRET_KEY=your-random-secret-key          # Generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
DEBUG=True
DB_NAME=codesense
DB_USER=postgres
DB_PASSWORD=your-database-password
DB_HOST=127.0.0.1
DB_PORT=5432
REDIS_URL=redis://localhost:6379/0
GITHUB_WEBHOOK_SECRET=your-webhook-secret
GITHUB_APP_ID=your-github-app-id
GITHUB_APP_PRIVATE_KEY_PATH=path/to/your-private-key.pem
```

### 4. Install Backend Dependencies

```bash
# Create and activate a virtual environment (recommended)
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Run Database Migrations

```bash
python manage.py migrate
```

### 6. Start the Backend (3 terminals)

**Terminal 1 — ASGI Server (Daphne):**

```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

**Terminal 2 — Celery Worker:**

```bash
# Windows
celery -A config worker --loglevel=info --pool=solo

# macOS/Linux
celery -A config worker --loglevel=info
```

**Terminal 3 — Expose to GitHub (for local development):**

```bash
ngrok http 8000
```

Copy the ngrok URL and set it as the webhook URL in your GitHub App settings:
`https://your-ngrok-url.ngrok-free.app/api/webhooks/github/`

### 7. Set Up the Frontend

```bash
cd prism-frontend
npm install
npm run dev
```

The frontend will be available at **http://localhost:5173**

---

## 🔗 GitHub App Setup

1. Go to **GitHub Settings → Developer Settings → GitHub Apps → New GitHub App**
2. Set the following:
   - **Webhook URL:** `https://your-domain.com/api/webhooks/github/` (or your ngrok URL for development)
   - **Webhook Secret:** Same value as `GITHUB_WEBHOOK_SECRET` in your `.env`
   - **Permissions:**
     - Repository: Pull Requests → Read & Write
     - Repository: Contents → Read
   - **Events:** Subscribe to **Pull request** events
3. After creating the app:
   - Note the **App ID** → set as `GITHUB_APP_ID` in `.env`
   - Generate a **Private Key** → save the `.pem` file and set the path as `GITHUB_APP_PRIVATE_KEY_PATH` in `.env`
4. Install the app on the repositories you want PRism to review

---

## 📡 API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/register/` | Register a new user and auto-create a team |
| `POST` | `/api/login/` | Login and receive JWT access/refresh tokens |

### Team & Repository Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/teams/` | List your teams |
| `GET` | `/api/repos/` | List connected repositories |
| `GET` | `/api/repos/<id>/reviews/` | List PR reviews for a repository |
| `GET/PUT` | `/api/repos/<id>/config/` | Get or update repository configuration |
| `GET` | `/api/repos/<id>/analytics/` | Get aggregated analytics for a repository |

### Webhooks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/webhooks/github/` | GitHub webhook receiver (signature-verified) |

### WebSocket

| Protocol | Endpoint | Description |
|----------|----------|-------------|
| `WSS` | `/ws/reviews/` | Real-time review notifications (JWT-authenticated) |

---

## 🔄 How It Works

1. **Developer opens a PR** on a connected GitHub repository
2. **GitHub sends a webhook** to PRism's `/api/webhooks/github/` endpoint
3. **Webhook receiver** verifies the signature, creates a `PullRequestEvent`, and dispatches a Celery task
4. **Celery worker** runs the analysis pipeline:
   - Fetches the PR diff via GitHub API
   - **Security Scanner** checks for hardcoded secrets, SQL injection, debug flags
   - **CodeBERT Analyzer** computes semantic risk scores for each changed file
   - **Knowledge Graph** updates with file coupling, patterns, and author data
   - Results are combined into a structured review
5. **PyGithub posts review comments** directly on the pull request
6. **WebSocket notification** is sent to connected frontend clients in real time
7. **Dashboard updates** with the latest review data and analytics

---

## ⚙️ Configuration

Each repository can be configured independently via the Config page or API:

| Setting | Default | Description |
|---------|---------|-------------|
| `max_function_lines` | `50` | Maximum lines per function before flagging |
| `enforce_naming` | `true` | Check naming convention compliance |
| `run_security_scanner` | `true` | Enable regex-based security scanning |
| `run_codebert` | `true` | Enable CodeBERT AI analysis |
| `notify_on_critical` | `true` | Send real-time alerts for critical findings |

---

## 🧰 Tech Stack

### Backend
- **Django 5.2** — Web framework
- **Django REST Framework** — API layer
- **Django Channels** — WebSocket support
- **Daphne** — ASGI server
- **Celery** — Async task processing
- **PostgreSQL** — Primary database
- **Redis** — Message broker & channel layer
- **CodeBERT** (Microsoft) — Code understanding transformer model
- **NetworkX** — Knowledge graph engine
- **PyGithub** — GitHub API client

### Frontend
- **React 19** — UI framework
- **Vite** — Build tool & dev server
- **React Router v7** — Client-side routing
- **Recharts** — Data visualization
- **Axios** — HTTP client with JWT interceptors
- **Lucide React** — Icon library

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "Add my feature"`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).

---

<p align="center">
  Built with 💜 by <a href="https://github.com/Lynx2711">Lynx2711</a>
</p>
