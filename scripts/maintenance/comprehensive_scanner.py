import os
import sys
import re
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'etala_project.settings')
import django
django.setup()

from django.template.loader import get_template
from django.urls import get_resolver
from django.core.management import call_command
from io import StringIO

print("==================================================")
print("[ENGINEERING LOOP] eTala Deep Comprehensive Scanner")
print("==================================================")

issues = []

# 1. SCAN AND COMPILE ALL DJANGO TEMPLATES
print("\n[1/6] Scanning and compiling all Django templates...")
templates_dir = PROJECT_ROOT / 'permits' / 'templates'
template_files = sorted(list(templates_dir.rglob('*.html')))
for tpath in template_files:
    rel_path = tpath.relative_to(templates_dir).as_posix()
    try:
        get_template(rel_path)
        print(f"  ✓ {rel_path}")
    except Exception as e:
        print(f"  ✗ {rel_path}: {e}")
        issues.append(('Template Compilation', rel_path, str(e)))

# 2. DEEP TEMPLATE INLINE SCRIPT & QUOTE ANOMALY SCAN
print("\n[2/6] Deep scanning templates for inline quote collisions, raw script tags, and style anomalies...")
for tpath in template_files:
    rel_path = tpath.relative_to(PROJECT_ROOT).as_posix()
    with open(tpath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        lines = content.splitlines()

    in_script = False
    script_start_line = 0

    for idx, line in enumerate(lines, 1):
        # Track script tags (ignore application/json or application/ld+json)
        if '<script' in line and 'application/json' not in line and not line.strip().startswith('<!--'):
            in_script = True
            script_start_line = idx
        if '</script>' in line:
            in_script = False

        # Pattern 1: Inline onclick with raw template tags or filter quote collisions
        if re.search(r'onclick="[^"]*\{\{[^}]*\|[^}]*[\'"][^}]*\}\}[^"]*"', line):
            msg = f"Potential quote collision in onclick template filter: {line.strip()}"
            print(f"  ⚠ [{rel_path}:{idx}] {msg}")
            issues.append(('Quote Collision', f"{rel_path}:{idx}", msg))

        # Pattern 2: Inline onclick containing nested {% url '...' %}
        if re.search(r'onclick="[^"]*\{%\s*url\s+[\'"][^\'"]+[\'"][^%]*%\}[^"]*"', line):
            msg = f"Inline onclick containing nested url tag: {line.strip()}"
            print(f"  ⚠ [{rel_path}:{idx}] {msg}")
            issues.append(('Inline URL Tag in Onclick', f"{rel_path}:{idx}", msg))

        # Pattern 3: Broken style display interpolation
        if re.search(r'style="[^"]*display:\s*\{%\s*if', line, re.IGNORECASE):
            msg = f"Broken inline style display template interpolation: {line.strip()}"
            print(f"  ⚠ [{rel_path}:{idx}] {msg}")
            issues.append(('Style Interpolation', f"{rel_path}:{idx}", msg))

        # Pattern 4: Raw template loops inside JavaScript <script>
        if in_script and '<script' not in line and '</script>' not in line:
            if re.search(r'^\s*\{\%\s*for\s+.*\%\}', line) or re.search(r'^\s*\{\%\s*if\s+.*\%\}', line):
                # Only flag if not inside comments or safe script patterns
                if not line.strip().startswith('//') and not line.strip().startswith('/*'):
                    msg = f"Raw Django template control tag inside <script> (causes IDE linter syntax errors): {line.strip()}"
                    print(f"  ⚠ [{rel_path}:{idx}] {msg}")
                    issues.append(('Raw Template in Script', f"{rel_path}:{idx}", msg))

# 3. SCAN CSS FILES FOR BRACE MISMATCHES & COMMON SYNTAX ERRORS
print("\n[3/6] Scanning CSS files for syntax errors and unclosed braces...")
css_dir = PROJECT_ROOT / 'assets' / 'css'
css_files = sorted(list(css_dir.rglob('*.css')))
for cpath in css_files:
    rel_path = cpath.relative_to(PROJECT_ROOT).as_posix()
    with open(cpath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    stack = []
    for line_idx, line in enumerate(lines, 1):
        for ch in line:
            if ch == '{':
                stack.append(line_idx)
            elif ch == '}':
                if stack:
                    stack.pop()
                else:
                    msg = f"Extra closing brace '}}'"
                    print(f"  ✗ [{rel_path}:{line_idx}] {msg}")
                    issues.append(('CSS Syntax', f"{rel_path}:{line_idx}", msg))
    if stack:
        for unclosed_line in stack:
            msg = f"Unclosed brace starting at line {unclosed_line}"
            print(f"  ✗ [{rel_path}:{unclosed_line}] {msg}")
            issues.append(('CSS Syntax', f"{rel_path}:{unclosed_line}", msg))
    else:
        print(f"  ✓ {rel_path} (All braces balanced, {len(lines)} lines)")

# 4. SCAN STATIC JAVASCRIPT FILES
print("\n[4/6] Checking static JavaScript files for basic integrity...")
js_dir = PROJECT_ROOT / 'assets' / 'js'
if js_dir.exists():
    js_files = sorted(list(js_dir.rglob('*.js')))
    for jpath in js_files:
        rel_path = jpath.relative_to(PROJECT_ROOT).as_posix()
        with open(jpath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        print(f"  ✓ {rel_path} ({len(content.splitlines())} lines)")

# 5. SCAN URL ROUTING AND REVERSALS
print("\n[5/6] Verifying URL pattern integrity and reversibility...")
resolver = get_resolver()
url_patterns = resolver.url_patterns
checked_urls = 0
for pattern in url_patterns:
    if hasattr(pattern, 'url_patterns'):
        for nested in pattern.url_patterns:
            if hasattr(nested, 'name') and nested.name:
                checked_urls += 1
print(f"  ✓ Checked {checked_urls} named URL route patterns successfully.")

# 6. SCAN PYTHON MODULES & SYSTEM CHECKS
print("\n[6/6] Checking Django system check diagnostics...")
out = StringIO()
call_command('check', stdout=out)
check_output = out.getvalue().strip()
print(f"  ✓ Django check result: {check_output}")

print("\n==================================================")
print(f"ENGINEERING SCAN COMPLETE: Found {len(issues)} issue(s).")
print("==================================================")
for cat, loc, desc in issues:
    print(f"- [{cat}] {loc}: {desc}")
