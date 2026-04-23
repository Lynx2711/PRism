#hunk header: something like this @@ -14,7 +14,7 @@ which states where in a file, changes have been made and compares it to the previous version of that file. -14,7 — old file, starting line 14, showing 7 lines +14,7 — new file, starting line 14, showing 7 lines. scanner needs to catch these by parsing the hunk header to find where the hunk starts and then count + lines from there

#the job of the scanner is add an additional layer before the code reaches the ai model inorder to catch vulnerabilities like a hardcoded password, or some confidential information like the api key. find the error and tell pygithub to comment on that line


import re #for reegular expressions
import logging

logger = logging.getLogger(__name__)
SECURITY_PATTERNS = [
    (
        'hardcoded_password',
        re.compile(r'password\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
        'critical',
        'Hardcoded password detected'
    ),
    (
        'hardcoded_api_key',
        re.compile(r'api_key\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
        'critical',
        'Hardcoded API key detected'
    ),
    (
        'hardcoded_secret_key',
        re.compile(r'secret_key\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
        'critical',
        'Hardcoded secret key detected'
    ),
    (
        'hardcoded_token',
        re.compile(r'token\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
        'critical',
        'Hardcoded token detected'
    ),
    (
        'aws_access_key',
        re.compile(r'AKIA[0-9A-Z]{16}'),
        'critical',
        'AWS access key detected'
    ),
    (
        'private_key_header',
        re.compile(r'-----BEGIN (RSA |EC )?PRIVATE KEY-----'),
        'critical',
        'Private key material detected'
    ),
    (
        'sql_injection_risk',
        re.compile(r'(execute|query)\s*\(\s*f["\'].*\{', re.IGNORECASE),
        'high',
        'Possible SQL injection via f-string query'
    ),
    (
        'debug_true',
        re.compile(r'DEBUG\s*=\s*True'),
        'medium',
        'DEBUG=True should not be committed'
    ),
]

def parse_hunk_header(line):
    """
    Parse @@ -old_start,old_count +new_start,new_count @@
    Returns the new file starting line number.
    We only care about the new file (+) side since that's
    what GitHub shows in the PR and what we comment on.track current_line by incrementing it for every non-header line, resetting it at each @@
    """
    match = re.search(r'\+(\d+)(?:,\d+)?', line)
    if match:
        return int(match.group(1)) #return the new file starting line number
    return 1 #default to 1 if no match found

def scan_patch(filename, patch):
    """
    Scan a single file's diff patch for security issues.
    Returns a list of findings, each with line number and details.
    """
    if not patch:
        return []

    findings = []
    current_file_line = 1
    diff_position = 0  # counts every line in the diff including headers

    for line in patch.splitlines():
        diff_position += 1

        if line.startswith('@@'):
            current_file_line = parse_hunk_header(line)
            continue

        if line.startswith('-'):
            continue

        if line.startswith('+'):
            code_line = line[1:]

            for pattern_id, pattern, severity, message in SECURITY_PATTERNS:
                if pattern.search(code_line):
                    findings.append({
                        'filename': filename,
                        'line': diff_position,  # diff position for GitHub API
                        'file_line': current_file_line,  # actual file line for display
                        'pattern_name': pattern_id,
                        'severity': severity,
                        'description': message,
                        'code': code_line.strip(),
                    })
                    logger.warning(
                        f"Security issue found: {pattern_id} in {filename} "
                        f"at line {current_file_line}: {message}"
                    )

            current_file_line += 1

        else:
            current_file_line += 1

    return findings

def scan_diff(diff_text):
    """
    Scan the diff text of a PR for security vulnerabilities.
    Returns a list of findings, sorted by severity.
    """
    findings = []
    # Only scan added or modified files — skip deleted files
    # No point flagging secrets in code being removed
    for file in diff_text:
        if file['status'] == 'removed':
            continue
        #scan the patch for vulnerabilities
        file_findings = scan_patch(file['filename'], file['patch'])
        findings.extend(file_findings)
    #sort findings by severity
    findings.sort(key=lambda x: ['critical', 'high', 'medium', 'low'].index(x['severity']))
    logger.info(f"Scan complete. Found {len(findings)} potential security issues.")
    return findings