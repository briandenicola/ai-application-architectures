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

# Kept deliberately in lockstep with postprovision.sh. The two hooks are the
# same contract for two shells; a step present in one and missing from the
# other produces an environment that works on the presenter's laptop and fails
# on a colleague's. tests/test_postprovision_parity.py enforces this.
$steps = @(
    @('scripts/index_corpus.py',    @()),
    @('scripts/setup_knowledge.py', @()),
    @('scripts/create_agents.py',   @()),
    @('scripts/seed_evaluator.py',  @()),
    @('scripts/seed_dataset.py',    @()),
    @('scripts/index_corpus.py',    @('--corpus', 'finops')),
    @('scripts/create_agents.py',   @('--corpus', 'finops')),
    @('scripts/seed_evaluator.py',  @('--corpus', 'finops')),
    @('scripts/seed_dataset.py',    @('--corpus', 'finops'))
)

foreach ($step in $steps) {
    $script = $step[0]
    $stepArgs = $step[1]
    Write-Host "→ $script $($stepArgs -join ' ')"
    & $py $script @stepArgs
    if ($LASTEXITCODE -ne 0) { throw "$script $($stepArgs -join ' ') failed" }
}

Write-Host ''
Write-Host '✓ Demo environment ready.'
Write-Host "  Portal:  $env:AZURE_AI_PROJECT_ENDPOINT"
Write-Host ''
Write-Host '  Next:'
Write-Host '    python scripts/run_eval.py --agent meridian-advisor-v1   # expect exit 1'
Write-Host '    python scripts/run_eval.py --agent meridian-advisor-v2   # expect exit 0'
Write-Host '    python scripts/run_eval.py --corpus finops --agent meridian-finops-v1  # expect exit 1'
Write-Host '    python scripts/run_eval.py --corpus finops --agent meridian-finops-v2  # expect exit 0'
Write-Host ''
Write-Host '  Portal walkthrough: docs/finops-run-of-show.md'
Write-Host ''
