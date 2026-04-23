import hashlib
import hmac
from django.conf import settings

def validate_github_signature(request):
    signature_header = request.headers.get('X-Hub-Signature-256', '')

    if not signature_header.startswith('sha256='):
        return False

    expected_signature = signature_header[7:]

    mac = hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode('utf-8'),
        msg=request.body,
        digestmod=hashlib.sha256
    )
    computed_signature = mac.hexdigest()

    return hmac.compare_digest(computed_signature, expected_signature)