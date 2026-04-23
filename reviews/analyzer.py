"""diff patch
    ↓
Split into chunks (one function or 20 lines at a time)
    ↓
Feed each chunk to CodeBERT → get embedding vector
    ↓
Run simple risk classifier on embedding → risk score 0.0 to 1.0. The risk classifier for now is simple — we use cosine similarity against known bad patterns. In Week 7 when the knowledge graph exists, the classifier gets repo-specific context fed into it
    ↓
Combine with scanner findings:
  scanner found critical issue → severity: critical regardless of score
  scanner found nothing + score > 0.7 → severity: high
  scanner found nothing + score 0.4-0.7 → severity: medium
  scanner found nothing + score < 0.4 → looks fine
    ↓
Build structured review object
    ↓
PyGithub posts comments to GitHub PR"""

import logging
import numpy as np
from transformers import AutoTokenizer, AutoModel
import torch

logger = logging.getLogger(__name__)

# Known dangerous code patterns — these are your "reference points" in vector space
# CodeBERT will compare new code against these to compute similarity
# The closer new code is to these patterns, the higher the risk score
KNOWN_RISKY_PATTERNS = [
    "password = 'secret'",
    'api_key = "hardcoded"',
    "execute(f'SELECT * FROM users WHERE id = {user_id}')",
    "DEBUG = True",
    "secret_key = 'abc123'",
    "token = 'hardcoded_token'",
    "eval(user_input)",
    "os.system(user_input)",
    "pickle.loads(data)",
    "md5(password)",
]

KNOWN_SAFE_PATTERNS = [
    "def calculate_total(price, tax):",
    "return render(request, 'index.html', context)",
    "logger.info('Processing complete')",
    "if user.is_authenticated:",
    "queryset = User.objects.filter(is_active=True)",
]


class CodeBERTAnalyzer:
    def __init__(self):
        self.tokenizer = None
        self.model = None
        self.risky_embeddings = None
        self.safe_embeddings = None
        self._loaded = False

    def load(self):
        """
        Load model lazily — only when first needed.
        This means Celery workers don't load a 500MB model on startup,
        only when an actual PR comes in.
        """
        if self._loaded:
            return

        logger.info("Loading CodeBERT model — this takes ~30 seconds first time...")

        model_name = "microsoft/codebert-base"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.eval()  # inference mode — not training

        # Pre-compute embeddings for known patterns
        # This happens once at load time, not on every PR
        logger.info("Pre-computing reference pattern embeddings...")
        self.risky_embeddings = [
            self._get_embedding(p) for p in KNOWN_RISKY_PATTERNS
        ]
        self.safe_embeddings = [
            self._get_embedding(p) for p in KNOWN_SAFE_PATTERNS
        ]

        self._loaded = True
        logger.info("CodeBERT ready")

    def _get_embedding(self, code_text):
        """
        Convert code text into a 768-dimensional vector.
        This is the core operation — text goes in, numbers come out.
        """
        # Tokenizer converts text to token IDs the model understands
        # truncation=True handles code longer than 512 tokens
        inputs = self.tokenizer(
            code_text,
            return_tensors='pt',       # pt = PyTorch tensors
            truncation=True,
            max_length=512,
            padding=True,
        )

        # torch.no_grad() tells PyTorch we're not training
        # saves memory and speeds up inference significantly
        with torch.no_grad():
            outputs = self.model(**inputs)

        # outputs.last_hidden_state shape: (1, sequence_length, 768)
        # We take the mean across the sequence dimension to get
        # one vector representing the whole code snippet
        # Shape becomes: (768,) — one number per dimension
        embedding = outputs.last_hidden_state.mean(dim=1).squeeze()
        return embedding.numpy()

    def _cosine_similarity(self, vec_a, vec_b):
        """
        Cosine similarity between two vectors.
        Returns a value between -1 and 1.
        1.0 = identical meaning, 0.0 = unrelated, -1.0 = opposite
        """
        dot_product = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def compute_risk_score(self, code_text):
        """
        Compare code against known risky and safe patterns.
        Returns a score from 0.0 (safe) to 1.0 (risky).
        """
        embedding = self._get_embedding(code_text)

        # How similar is this code to known risky patterns?
        risky_similarities = [
            self._cosine_similarity(embedding, ref)
            for ref in self.risky_embeddings
        ]
        max_risky_similarity = max(risky_similarities)

        # How similar is this code to known safe patterns?
        safe_similarities = [
            self._cosine_similarity(embedding, ref)
            for ref in self.safe_embeddings
        ]
        max_safe_similarity = max(safe_similarities)

        # Risk score = how much more it resembles risky than safe
        # Normalized to 0.0-1.0 range
        raw_score = max_risky_similarity - max_safe_similarity
        risk_score = (raw_score + 1) / 2  # shift from [-1,1] to [0,1]

        return round(float(risk_score), 3)

    def analyze_diff(self, diff_content):
        """
        Analyze all files in a PR diff.
        Returns findings with risk scores for each chunk of code.
        """
        self.load()  # lazy load — only loads model once

        findings = []

        for file in diff_content:
            if file['status'] == 'removed':
                continue

            patch = file.get('patch', '')
            if not patch:
                continue

            # Extract only the added lines for analysis
            # We join them into one chunk per file
            added_lines = []
            for line in patch.splitlines():
                if line.startswith('+') and not line.startswith('+++'):
                    added_lines.append(line[1:])  # strip leading +

            if not added_lines:
                continue

            code_chunk = '\n'.join(added_lines)
            risk_score = self.compute_risk_score(code_chunk)

            # Translate score to severity
            if risk_score >= 0.75:
                severity = 'high'
            elif risk_score >= 0.55:
                severity = 'medium'
            else:
                severity = 'low'

            findings.append({
                'filename': file['filename'],
                'risk_score': risk_score,
                'severity': severity,
                'description': f'CodeBERT risk score: {risk_score}',
                'code_summary': code_chunk[:200],
            })

            logger.info(
                f"CodeBERT analysis — {file['filename']}: "
                f"risk score {risk_score} ({severity})"
            )

        return findings


# Module-level singleton — one instance shared across all Celery tasks
# Model loads once, stays in memory, reused for every PR
analyzer = CodeBERTAnalyzer()