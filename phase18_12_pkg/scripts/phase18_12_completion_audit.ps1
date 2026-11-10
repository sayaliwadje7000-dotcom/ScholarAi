[CmdletBinding()]
param(
    [switch]$RunTests
)

$ErrorActionPreference = 'Continue'
$ProjectRoot = (Get-Location).Path

Write-Host "ScholarAI Phase 18.12 completion audit" -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot"
Write-Host "This script checks presence/status only; it does not modify source files."

$required = @(
    'app/models/user.py',
    'app/models/user_session.py',
    'app/security/password.py',
    'app/security/token.py',
    'app/security/permissions.py',
    'app/api/dependencies.py',
    'app/api/auth.py',
    'app/api/sessions.py',
    'app/core/security_config.py',
    'app/security/rate_limiter.py',
    'app/security/security_middleware.py',
    'tests/auth',
    'tests/security',
    'docs/phase-18-12-documentation-and-phase-completion.md',
    'docs/phase-18-security-verification-record.md'
)

$missing = @()
foreach ($relative in $required) {
    $path = Join-Path $ProjectRoot $relative
    if (Test-Path $path) {
        Write-Host "[FOUND]   $relative" -ForegroundColor Green
    }
    else {
        Write-Host "[MISSING] $relative" -ForegroundColor Yellow
        $missing += $relative
    }
}

Write-Host "`n--- Git status ---" -ForegroundColor Cyan
git status --short

Write-Host "`n--- Latest commit ---" -ForegroundColor Cyan
git log -1 --oneline

Write-Host "`n--- Alembic current ---" -ForegroundColor Cyan
alembic current

if ($RunTests) {
    Write-Host "`n--- Focused security regression tests ---" -ForegroundColor Cyan
    python -m pytest tests/auth tests/security tests/api/test_hybrid_recommendations.py tests/api/test_hybrid_recommendation_api_contract.py -v
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Focused security tests failed. Full suite will not be run."
        exit $LASTEXITCODE
    }

    Write-Host "`n--- Full regression suite ---" -ForegroundColor Cyan
    python -m pytest -v
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Full regression suite failed."
        exit $LASTEXITCODE
    }
}

Write-Host "`nAudit summary" -ForegroundColor Cyan
Write-Host "Missing expected paths: $($missing.Count)"
if ($missing.Count -gt 0) {
    Write-Host "This is not a completion pass. Review missing paths against the actual project structure."
}
else {
    Write-Host "All expected paths exist. This does NOT prove security correctness or Phase 18 completion."
}
Write-Host "Record fresh test results and manually verify the gates in docs/phase-18-12-documentation-and-phase-completion.md."
