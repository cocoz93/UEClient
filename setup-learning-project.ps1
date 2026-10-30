<#
  LearnTopDown: 설치된 UE Top Down Blueprint 템플릿으로 학습용 프로젝트를 생성한다.
  Content는 기존 저장소 규칙에 따라 Git에서 제외되므로 설치본에서 재구성한다.
  기존 프로젝트가 있으면 중단하며, 삭제하거나 덮어쓰지 않는다.
#>
param(
    [string]$EnginePath = 'C:\Program Files\Epic Games\UE_5.8'
)

$ErrorActionPreference = 'Stop'
$ProjectName = 'LearnTopDown'
$TemplateName = 'TP_TopDownBP'
$ProjectDir = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot $ProjectName))
$TemplateDir = Join-Path $EnginePath "Templates\$TemplateName"
$SharedDir = Join-Path $EnginePath 'Templates\TemplateResources'
$Packs = @(
    @{ Name = 'LevelPrototyping'; Detail = 'High' },
    @{ Name = 'Characters'; Detail = 'High' },
    @{ Name = 'Cursor'; Detail = 'Standard' }
)
$Utf8 = New-Object System.Text.UTF8Encoding($false)

if (Test-Path -LiteralPath $ProjectDir) {
    throw "대상 폴더가 이미 있다. 기존 파일을 보존하기 위해 중단한다: $ProjectDir"
}
if (-not (Test-Path -LiteralPath (Join-Path $TemplateDir "$TemplateName.uproject"))) {
    throw "Top Down Blueprint 템플릿을 찾을 수 없다: $TemplateDir"
}
foreach ($Pack in $Packs) {
    $PackDir = Join-Path $SharedDir ($Pack.Detail + '\' + $Pack.Name + '\Content')
    if (-not (Test-Path -LiteralPath $PackDir)) {
        throw "필수 공유 콘텐츠가 없다: $PackDir"
    }
}

# TemplateDefs.ini의 None 변형과 제외 목록을 적용한다.
$SkipDirs = @('Binaries', 'Build', 'Intermediate', 'Saved', 'Media')
$SkipFiles = @("$TemplateName.uproject", "$TemplateName.png", 'TemplateDefs.ini',
    'config.ini', 'Manifest.json', 'contents.txt')
New-Item -ItemType Directory -Path $ProjectDir | Out-Null
foreach ($File in Get-ChildItem -LiteralPath $TemplateDir -Recurse -File) {
    $Relative = $File.FullName.Substring($TemplateDir.Length + 1)
    $Parts = $Relative -split '\\'
    if (@($Parts | Where-Object { $SkipDirs -contains $_ }).Count -gt 0) { continue }
    if ($SkipFiles -contains $File.Name) { continue }
    $Destination = Join-Path $ProjectDir $Relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $Destination) -Force | Out-Null
    Copy-Item -LiteralPath $File.FullName -Destination $Destination
}

foreach ($Pack in $Packs) {
    $PackDir = Join-Path $SharedDir ($Pack.Detail + '\' + $Pack.Name + '\Content')
    $DestinationRoot = Join-Path $ProjectDir ('Content\' + $Pack.Name)
    foreach ($File in Get-ChildItem -LiteralPath $PackDir -Recurse -File) {
        $Relative = $File.FullName.Substring($PackDir.Length + 1)
        $Destination = Join-Path $DestinationRoot $Relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $Destination) -Force | Out-Null
        Copy-Item -LiteralPath $File.FullName -Destination $Destination
    }
}

# 바이너리 에셋은 변경하지 않고 설정 파일의 이름만 치환한다.
foreach ($File in Get-ChildItem -LiteralPath (Join-Path $ProjectDir 'Config') -File -Filter '*.ini') {
    $Text = [IO.File]::ReadAllText($File.FullName)
    $Text = $Text.Replace($TemplateName.ToUpperInvariant(), $ProjectName.ToUpperInvariant())
    $Text = $Text.Replace($TemplateName.ToLowerInvariant(), $ProjectName.ToLowerInvariant())
    $Text = [regex]::Replace($Text, [regex]::Escape($TemplateName), $ProjectName, 'IgnoreCase')
    [IO.File]::WriteAllText($File.FullName, $Text, $Utf8)
}

$Project = Get-Content -LiteralPath (Join-Path $TemplateDir "$TemplateName.uproject") -Raw | ConvertFrom-Json
$Project.EngineAssociation = '5.8'
$Project.Description = 'Top Down Blueprint 학습용 프로젝트'
[IO.File]::WriteAllText((Join-Path $ProjectDir "$ProjectName.uproject"),
    ($Project | ConvertTo-Json -Depth 8), $Utf8)

$GameIni = Join-Path $ProjectDir 'Config\DefaultGame.ini'
$Text = [IO.File]::ReadAllText($GameIni)
$Text = [regex]::Replace($Text, '(?m)^ProjectID=.*$', 'ProjectID=' + [guid]::NewGuid().ToString('N').ToUpperInvariant())
$Text = [regex]::Replace($Text, '(?m)^ProjectName=.*$', 'ProjectName=' + $ProjectName)
[IO.File]::WriteAllText($GameIni, $Text, $Utf8)

$EngineIni = Join-Path $ProjectDir 'Config\DefaultEngine.ini'
$Text = [IO.File]::ReadAllText($EngineIni)
$Settings = @'

[/Script/HardwareTargeting.HardwareTargetingSettings]
TargetedHardwareClass=Desktop
DefaultGraphicsPerformance=Scalable
'@
[IO.File]::WriteAllText($EngineIni, $Text.TrimEnd() + [Environment]::NewLine + $Settings + [Environment]::NewLine, $Utf8)

# 템플릿에 남은 이전 예제 맵과 콘텐츠 브라우저 경로를 현재 맵으로 맞춘다.
$EditorIni = Join-Path $ProjectDir 'Config\DefaultEditor.ini'
$Text = [IO.File]::ReadAllText($EditorIni)
$Text = [regex]::Replace($Text, '(?m)^SimpleMapName=.*$', 'SimpleMapName=/Game/TopDown/Lvl_TopDown')
[IO.File]::WriteAllText($EditorIni, $Text, $Utf8)
$UserIni = Join-Path $ProjectDir 'Config\DefaultEditorPerProjectUserSettings.ini'
$Text = [IO.File]::ReadAllText($UserIni).Replace('/Game/TopDownBP', '/Game/TopDown')
[IO.File]::WriteAllText($UserIni, $Text, $Utf8)

Write-Output "학습용 프로젝트 생성 완료: $ProjectDir\$ProjectName.uproject"
