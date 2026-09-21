# azd postprovision hook (Windows). Any failure aborts `azd up`.
$ErrorActionPreference = 'Stop'

Set-Location (Join-Path $PSScriptRoot '..')

Write-Host '──────────────────────────────────────────────────────────────'
Write-Host ' Meridian Foundry Evals — post-provision configuration'
Write-Host '──────────────────────────────────────────────────────────────'

if (-not (Test-Path .venv)) {
    Write-Host '→ Creating virtual environment'
    python -m venv .venv
}

# Call interpreters directly. On locked-down machines the *.ps1 shims that pip and
# npx install are blocked by execution policy, so shim-based invocation fails.
$py = Join-Path (Resolve-Path .venv) 'Scripts\python.exe'

Write-Host '→ Installing dependencies'
& $py -m pip install --quiet --upgrade pip
& $py -m pip install --quiet -e .

Write-Host '→ Waiting 60s for RBAC propagation'
# Role assignments made during provisioning are not always effective immediately.
Start-Sleep -Seconds 60

& $py scripts/index_corpus.py
if ($LASTEXITCODE -ne 0) { throw 'index_corpus.py failed' }

& $py scripts/setup_knowledge.py
if ($LASTEXITCODE -ne 0) { throw 'setup_knowledge.py failed' }

& $py scripts/create_agents.py
if ($LASTEXITCODE -ne 0) { throw 'create_agents.py failed' }

Write-Host ''
Write-Host '✓ Demo environment ready.'
Write-Host "  Portal:  $env:AZURE_AI_PROJECT_ENDPOINT"
Write-Host ''
Write-Host '  Next:'
Write-Host '    python scripts/run_eval.py --agent meridian-advisor-v1   # expect exit 1'
Write-Host '    python scripts/run_eval.py --agent meridian-advisor-v2   # expect exit 0'
Write-Host ''
