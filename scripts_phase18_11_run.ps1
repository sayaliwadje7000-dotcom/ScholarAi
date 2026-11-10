$ErrorActionPreference = "Stop"

Write-Host "Phase 18.11 - Focused security regression suite" -ForegroundColor Cyan
python -m pytest `
    tests/auth `
    tests/security `
    tests/api/test_hybrid_recommendations.py `
    tests/api/test_hybrid_recommendation_api_contract.py `
    -v

if ($LASTEXITCODE -ne 0) {
    throw "Focused Phase 18.11 tests failed. Do not commit yet."
}

Write-Host "Focused security tests passed. Running full regression suite..." -ForegroundColor Green
python -m pytest -v

if ($LASTEXITCODE -ne 0) {
    throw "Full regression suite failed. Do not commit yet."
}

Write-Host "Both focused and full regression suites passed." -ForegroundColor Green
