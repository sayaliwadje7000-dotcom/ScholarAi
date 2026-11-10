$ErrorActionPreference = "Stop"

Write-Host "`nScholarAI Phase 18.8 - API Route Protection" -ForegroundColor Cyan

$projectRoot = (Get-Location).Path
$mainFile = Join-Path $projectRoot "app\main.py"
$permissionsFile = Join-Path $projectRoot "app\security\permissions.py"
$testFile = Join-Path $projectRoot "tests\auth\test_route_protection.py"
$docsFile = Join-Path $projectRoot "docs\phase-18-8-api-route-protection.md"

foreach ($required in @($mainFile, $permissionsFile)) {
    if (-not (Test-Path $required)) {
        throw "Required project file not found: $required. Run this script from the ScholarAi project root."
    }
}

New-Item -ItemType Directory -Force -Path (Split-Path $testFile), (Split-Path $docsFile) | Out-Null

# Preserve one-time backups before changing existing source.
foreach ($file in @($mainFile, $permissionsFile)) {
    $backup = "$file.phase18_8.bak"
    if (-not (Test-Path $backup)) {
        Copy-Item $file $backup
    }
}

# Add an explicit student-or-admin policy without changing existing policies.
$permissions = Get-Content $permissionsFile -Raw
if ($permissions -notmatch '(?m)^require_student_or_admin\s*=') {
    if ($permissions -notmatch '(?m)^def require_roles\(') {
        throw "Could not find require_roles in app/security/permissions.py. No permission changes were made."
    }
    $permissions += "`r`n`r`n# Phase 18.8: general student-facing routes; administrators retain operational access.`r`nrequire_student_or_admin = require_roles(`"student`", `"admin`")`r`n"
    Set-Content -Path $permissionsFile -Value $permissions -Encoding UTF8
}

# Use Python for balanced-parenthesis editing of app.include_router calls.
$patcher = @'
from pathlib import Path
import re
import sys

path = Path("app/main.py")
source = path.read_text(encoding="utf-8-sig")

# Ensure Depends is imported from FastAPI.
if re.search(r"(?m)^from fastapi import FastAPI\s*$", source):
    source = re.sub(
        r"(?m)^from fastapi import FastAPI\s*$",
        "from fastapi import Depends, FastAPI",
        source,
        count=1,
    )
elif re.search(r"(?m)^from fastapi import \(", source):
    # Existing multiline import: add Depends only if absent.
    m = re.search(r"(?m)^from fastapi import \(\s*\n", source)
    if m and not re.search(r"\bDepends\b", source[m.start():source.find(")", m.start())]):
        pos = m.end()
        source = source[:pos] + "    Depends,\n" + source[pos:]
elif not re.search(r"(?m)^from fastapi import .*?\bDepends\b", source):
    source = "from fastapi import Depends\n" + source

# Add the policy import once.
policy_import = "from app.security.permissions import require_student_or_admin"
if policy_import not in source:
    # Put it with imports, before the application lifecycle section.
    marker = "# ============================================================\n# APPLICATION LIFECYCLE"
    if marker in source:
        source = source.replace(marker, policy_import + "\n\n\n" + marker, 1)
    else:
        # Safe fallback: add after FastAPI imports.
        lines = source.splitlines()
        insert_at = 0
        for i, line in enumerate(lines):
            if line.startswith("from fastapi import"):
                insert_at = i + 1
        lines.insert(insert_at, policy_import)
        source = "\n".join(lines) + "\n"

protected_routers = {
    "chat_router",
    "documents_router",
    "retrieval_router",
    "rag_router",
    "recommendations_router",
    "content_recommendations_router",
    "resource_recommendations_router",
    "opportunities_router",
    "ml_recommendations_router",
    "hybrid_recommendations_router",
    "learning_profile_router",
    "learning_activities_router",
    "personalization_controls_router",
}

def find_call_end(text: str, open_paren: int) -> int:
    depth = 0
    quote = None
    triple = False
    escaped = False
    i = open_paren
    while i < len(text):
        ch = text[i]
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif triple and text.startswith(quote * 3, i):
                quote = None
                triple = False
                i += 2
            elif not triple and ch == quote:
                quote = None
        else:
            if ch in ("'", '"'):
                if text.startswith(ch * 3, i):
                    quote = ch
                    triple = True
                    i += 2
                else:
                    quote = ch
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    raise RuntimeError("Unbalanced parentheses in app.include_router call.")

# Work from the end so earlier offsets remain valid.
matches = list(re.finditer(r"app\.include_router\s*\(", source))
patched = []
for match in reversed(matches):
    open_paren = source.find("(", match.start())
    end = find_call_end(source, open_paren)
    block = source[open_paren + 1:end]
    first_arg = re.match(r"\s*([A-Za-z_]\w*)", block)
    if not first_arg:
        continue
    router_name = first_arg.group(1)
    if router_name not in protected_routers:
        continue
    if "dependencies=" in block:
        continue
    insertion = "\n    dependencies=[Depends(require_student_or_admin)],"
    source = source[:end] + insertion + source[end:]
    patched.append(router_name)

missing = protected_routers - set(patched)
# A router already containing a dependency is also considered handled.
for name in list(missing):
    if re.search(
        rf"app\.include_router\s*\(\s*{re.escape(name)}\b[\s\S]*?dependencies\s*=",
        source,
    ):
        missing.remove(name)

if missing:
    raise RuntimeError(
        "Could not locate expected router registrations in app/main.py: "
        + ", ".join(sorted(missing))
        + ". No Phase 18.8 completion claim should be made; inspect main.py."
    )

path.write_text(source, encoding="utf-8")
print("Protected student-facing routers:", ", ".join(sorted(protected_routers)))
print("Newly patched router registrations:", ", ".join(sorted(patched)) or "(already patched)")
'@

$patcher | python -
if ($LASTEXITCODE -ne 0) {
    throw "Failed to update app/main.py. Restore from app/main.py.phase18_8.bak if necessary."
}

# Add focused tests for the role dependency itself.
@'
import os
import secrets
import uuid
from types import SimpleNamespace

os.environ.setdefault("SCHOLARAI_JWT_SECRET_KEY", secrets.token_urlsafe(48))

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.database.session import get_db
from app.security.permissions import require_student_or_admin
from app.services.role_service import role_service


def build_client(monkeypatch, roles):
    app = FastAPI()
    user = SimpleNamespace(id=uuid.uuid4())

    def fake_current_user():
        return user

    def fake_db():
        return object()

    monkeypatch.setattr(
        role_service,
        "get_user_roles",
        lambda db, user_id: set(roles),
    )

    app.dependency_overrides[get_current_user] = fake_current_user
    app.dependency_overrides[get_db] = fake_db

    @app.get("/protected")
    def protected_route(_user=Depends(require_student_or_admin)):
        return {"allowed": True}

    return TestClient(app)


def test_student_can_access_student_route(monkeypatch):
    client = build_client(monkeypatch, {"student"})
    response = client.get("/protected")
    assert response.status_code == 200
    assert response.json() == {"allowed": True}


def test_admin_can_access_student_route(monkeypatch):
    client = build_client(monkeypatch, {"admin"})
    response = client.get("/protected")
    assert response.status_code == 200


def test_educator_without_student_role_is_denied(monkeypatch):
    client = build_client(monkeypatch, {"educator"})
    response = client.get("/protected")
    assert response.status_code == 403


def test_user_without_roles_is_denied(monkeypatch):
    client = build_client(monkeypatch, set())
    response = client.get("/protected")
    assert response.status_code == 403
'@ | Set-Content -Path $testFile -Encoding UTF8

@'
# ScholarAI Phase 18.8 — API Route Protection

## Objective
Apply database-backed role authorization to student-facing API routers while preserving existing authentication and ownership checks.

## Policy
- Student role: allowed to access student-facing routes.
- Administrator role: allowed to access student-facing routes for operational administration.
- Educator role alone: not implicitly treated as student. Educators requiring student-facing functionality must also have the student role.
- Administrative role-management endpoints remain governed by `require_admin`.
- Authentication registration/login and health endpoints are not placed behind student-role checks.

## Protected routers
- Chat
- Documents
- Retrieval
- RAG
- Recommendations
- Content recommendations
- Educational resource recommendations
- Opportunities
- ML recommendations
- Hybrid recommendations
- Learning profile
- Learning activities
- Personalization controls

The policy is applied at `app.include_router(...)` registration in `app/main.py`, so every endpoint in each listed router inherits the role check. Existing endpoint-level `get_current_user` dependencies and resource ownership checks are retained.

## Important boundary
Role authorization is not a replacement for resource ownership. Each document, learning activity, profile, recommendation, or personalization record must still be scoped to the authenticated user's ID. Cross-user ownership enforcement is reviewed separately in Phase 18.9.

## Tests
Run:
```powershell
python -m pytest tests/auth/test_route_protection.py -v
python -m pytest tests/auth/ -v
python -m pytest -v
```

The route dependency tests verify student/admin access and denial for educator-only or role-less users. Full API integration tests must additionally verify unauthenticated requests, role denial, and ownership isolation.

## Status
Implementation generated. Do not mark Phase 18.8 complete until imports, route registration, targeted tests, authentication tests, full regression tests, and Swagger authorization checks pass.
'@ | Set-Content -Path $docsFile -Encoding UTF8

Write-Host "`nPhase 18.8 files updated." -ForegroundColor Green
Write-Host "Created: tests\auth\test_route_protection.py" -ForegroundColor Green
Write-Host "Created: docs\phase-18-8-api-route-protection.md" -ForegroundColor Green

Write-Host "`nChecking imports and application route registration..." -ForegroundColor Cyan
python -c "from app.security.permissions import require_student_or_admin; print('Role dependency import: OK')"
if ($LASTEXITCODE -ne 0) { throw "Role dependency import failed." }

python -c "from app.main import app; print('Application import: OK'); print('\n'.join(sorted({r.path for r in app.routes if r.path.startswith('/api/v1')})))"
if ($LASTEXITCODE -ne 0) { throw "Application import/route registration failed." }

Write-Host "`nPhase 18.8 source generation and import checks completed. Tests remain to be run." -ForegroundColor Green
