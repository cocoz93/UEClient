param(
    [ValidateSet('Baseline', 'Setup', 'Pose', 'Inspect', 'Install', 'Verify', 'Review', 'Restore')][string]$Action = 'Verify',
    [string]$Profile = (Join-Path $PSScriptRoot 'Profiles/countess.json'),
    [string]$Baseline,
    [string]$Destination,
    [string]$Engine = 'C:/Program Files/Epic Games/UE_5.8',
    [string]$Python,
    [ValidateSet(30, 60)][int[]]$Fps = @(30, 60),
    [string[]]$Suites,
    [string]$VisualReview,
    [string]$ResultDirectory
)
$ErrorActionPreference = 'Stop'
$pipelineProject = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$pipelineSaved = Join-Path $pipelineProject 'Saved/QA/CharacterPipeline'
if (-not $Python) {
    $bundledPython = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    if (Test-Path -LiteralPath $bundledPython) { $Python = $bundledPython }
    else { $Python = (Get-Command python -ErrorAction Stop).Source }
}
if ($Action -eq 'Baseline') {
    $captureDirectory = Join-Path $pipelineSaved ('baseline-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    & $Python (Join-Path $PSScriptRoot 'baseline.py') capture $captureDirectory
    exit $LASTEXITCODE
}
if (-not $Baseline) {
    $latestBaseline = Get-ChildItem -LiteralPath $pipelineSaved -Directory -Filter 'baseline-*' |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'baseline.json') } |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $latestBaseline) { throw '먼저 -Action Baseline으로 기준선을 저장해야 한다.' }
    $Baseline = Join-Path $latestBaseline.FullName 'baseline.json'
}
if ($Action -eq 'Restore') {
    if (-not $Destination) { throw 'Restore에는 -Destination 프로젝트 경로가 필요하다.' }
    $baselineData = Get-Content -LiteralPath $Baseline -Raw | ConvertFrom-Json
    $bundle = Join-Path (Split-Path -Parent $Baseline) (Split-Path -Leaf $baselineData.private_bundle)
    & $Python (Join-Path $PSScriptRoot 'content_bundle.py') $bundle $Destination --sha256 $baselineData.bundle_sha256
    exit $LASTEXITCODE
}
if ($Action -eq 'Pose') {
    $poseProfile = Get-Content -LiteralPath $Profile -Raw | ConvertFrom-Json
    if ($poseProfile.character_id -ne 'sparrow') { throw 'Pose는 스패로우의 요청 자세 변형 전용이다.' }
    $poseOutput = Join-Path $pipelineProject ('Saved/QA/Sparrow/pose-install-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    & $Python (Join-Path $PSScriptRoot 'editor_task.py') (Join-Path $PSScriptRoot 'sparrow_pose_install.py') `
        --output $poseOutput --baseline $Baseline --engine $Engine --fps $Fps[0]
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $poseResult = Get-Content -LiteralPath (Join-Path $poseOutput 'pose-installation.json') -Raw | ConvertFrom-Json
    if (-not $poseResult.passed) { throw ('스패로우 자세 구성 실패: ' + $poseResult.error) }
    exit 0
}
if ($Action -eq 'Setup') {
    $setupProfile = Get-Content -LiteralPath $Profile -Raw | ConvertFrom-Json
    if ($setupProfile.character_id -ne 'sparrow') { throw 'Setup은 현재 스패로우 전용 에셋 구성 단계다.' }
    $setupOutput = Join-Path $pipelineProject ('Saved/QA/Sparrow/setup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    & $Python (Join-Path $PSScriptRoot 'editor_task.py') (Join-Path $PSScriptRoot 'sparrow_setup.py') `
        --output $setupOutput --engine $Engine --fps $Fps[0]
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $setupResult = Get-Content -LiteralPath (Join-Path $setupOutput 'sparrow-setup.json') -Raw | ConvertFrom-Json
    if (-not $setupResult.passed) { throw ('스패로우 에셋 구성 실패: ' + $setupResult.error) }
    exit 0
}
$pipelineArguments = @((Join-Path $PSScriptRoot 'pipeline.py'), $Action.ToLowerInvariant(),
    '--profile', $Profile, '--baseline', $Baseline, '--engine', $Engine, '--fps') + @($Fps | ForEach-Object { [string]$_ })
if ($Suites) { $pipelineArguments += @('--suites') + $Suites }
if ($VisualReview) { $pipelineArguments += @('--visual-review', $VisualReview) }
if ($ResultDirectory) { $pipelineArguments += @('--output', $ResultDirectory) }
& $Python @pipelineArguments
exit $LASTEXITCODE
