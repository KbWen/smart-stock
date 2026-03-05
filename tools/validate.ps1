Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Normalize-PathString {
    param([Parameter(Mandatory = $true)][string]$Path)
    if ($Path.StartsWith('\\?\')) { return $Path.Substring(4) }
    return $Path
}

function Join-NormalPath {
    param(
        [Parameter(Mandatory = $true)][string]$Base,
        [Parameter(Mandatory = $true)][string]$Child
    )
    return [System.IO.Path]::Combine((Normalize-PathString $Base), $Child)
}

$cwd = Normalize-PathString ((Get-Location).Path)
$candidateRoots = New-Object System.Collections.Generic.List[string]

$candidateRoots.Add($cwd)

if ((Split-Path -Leaf $cwd) -eq 'tools') {
    $candidateRoots.Add((Split-Path -Parent $cwd))
}

if ($PSScriptRoot) {
    $scriptDir = Normalize-PathString $PSScriptRoot
    $candidateRoots.Add($scriptDir)
    if ((Split-Path -Leaf $scriptDir) -eq 'tools') {
        $candidateRoots.Add((Split-Path -Parent $scriptDir))
    }
}

if ($PSCommandPath) {
    $scriptDir2 = Normalize-PathString (Split-Path -Parent $PSCommandPath)
    $candidateRoots.Add($scriptDir2)
    if ((Split-Path -Leaf $scriptDir2) -eq 'tools') {
        $candidateRoots.Add((Split-Path -Parent $scriptDir2))
    }
}

$root = $null
foreach ($cand in $candidateRoots) {
    if (-not $cand) { continue }
    $agentsPath = Join-NormalPath $cand 'AGENTS.md'
    if (Test-Path -Path $agentsPath -PathType Leaf) {
        $root = $cand
        break
    }
}

if (-not $root) {
    Write-Error "cannot locate repository root (AGENTS.md not found from current/script paths)"
    exit 1
}

$platformDoc = Join-NormalPath $root 'docs/CODEX_PLATFORM_GUIDE.md'
$claudePlatformDoc = Join-NormalPath $root 'docs/CLAUDE_PLATFORM_GUIDE.md'
$examplesDoc = Join-NormalPath $root 'docs/PROJECT_EXAMPLES.md'
$projectAgentsFile = Join-NormalPath $root 'AGENTS.md'
$projectClaudeFile = Join-NormalPath $root 'CLAUDE.md'
$workflowsDir = Join-NormalPath $root '.agent/workflows'
$claudeCommandsDir = Join-NormalPath $root '.claude/commands'
$codexInstall = Join-NormalPath $root '.codex/INSTALL.md'
$codexRules = Join-NormalPath $root '.codex/rules/default.rules'

function Assert-PathExists {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Message,
        [switch]$Directory
    )
    $ok = if ($Directory) { Test-Path -Path $Path -PathType Container } else { Test-Path -Path $Path -PathType Leaf }
    if (-not $ok) {
        Write-Error $Message
        exit 1
    }
}

function Assert-FileContains {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Pattern,
        [Parameter(Mandatory = $true)][string]$Message
    )
    $content = Get-Content -Raw -Path $Path
    if ($content -notmatch $Pattern) {
        Write-Error $Message
        exit 1
    }
}

$requiredFiles = @(
    (Join-NormalPath $workflowsDir 'hotfix.md'),
    (Join-NormalPath $workflowsDir 'worktree-first.md'),
    (Join-NormalPath $workflowsDir 'new-feature.md'),
    (Join-NormalPath $workflowsDir 'medium-feature.md'),
    (Join-NormalPath $workflowsDir 'small-fix.md'),
    (Join-NormalPath $workflowsDir 'govern-docs.md'),
    (Join-NormalPath $workflowsDir 'handoff.md'),
    (Join-NormalPath $workflowsDir 'bootstrap.md'),
    (Join-NormalPath $workflowsDir 'plan.md'),
    (Join-NormalPath $workflowsDir 'implement.md'),
    (Join-NormalPath $workflowsDir 'review.md'),
    (Join-NormalPath $workflowsDir 'help.md'),
    (Join-NormalPath $workflowsDir 'test-skeleton.md'),
    (Join-NormalPath $workflowsDir 'commands.md')
)

$claudeRequiredFiles = @(
    (Join-NormalPath $claudeCommandsDir 'bootstrap.md'),
    (Join-NormalPath $claudeCommandsDir 'plan.md'),
    (Join-NormalPath $claudeCommandsDir 'implement.md'),
    (Join-NormalPath $claudeCommandsDir 'review.md'),
    (Join-NormalPath $claudeCommandsDir 'test.md'),
    (Join-NormalPath $claudeCommandsDir 'handoff.md'),
    (Join-NormalPath $claudeCommandsDir 'ship.md')
)

foreach ($file in $requiredFiles) {
    Assert-PathExists -Path $file -Message "missing required file: $file"
}

foreach ($file in $claudeRequiredFiles) {
    Assert-PathExists -Path $file -Message "missing claude adapter file: $file"
}

Assert-PathExists -Path $platformDoc -Message "missing platform guide: $platformDoc"
Assert-PathExists -Path $claudePlatformDoc -Message "missing claude platform guide: $claudePlatformDoc"
Assert-PathExists -Path $examplesDoc -Message "missing examples doc: $examplesDoc"
Assert-PathExists -Path $projectAgentsFile -Message "missing project AGENTS.md: $projectAgentsFile"
Assert-PathExists -Path $projectClaudeFile -Message "missing project CLAUDE.md: $projectClaudeFile"
Assert-PathExists -Path $workflowsDir -Message "missing workflows dir: $workflowsDir" -Directory
Assert-PathExists -Path $claudeCommandsDir -Message "missing claude commands dir: $claudeCommandsDir" -Directory

$codexSkillsDir = Join-NormalPath $root '.agents/skills'
$agentSkillsDir = Join-NormalPath $root '.agent/skills'
Assert-PathExists -Path $codexSkillsDir -Message "missing codex skills dir: $codexSkillsDir" -Directory
Assert-PathExists -Path $agentSkillsDir -Message "missing agent skills canonical dir: $agentSkillsDir" -Directory

Get-ChildItem -Path $agentSkillsDir -File | ForEach-Object {
    $skillName = $_.Name
    if ($skillName -eq '.gitkeep') { return }
    if ($_.Length -le 0) {
        Write-Error "empty skill metadata: $($_.FullName)"
        exit 1
    }
    $codexSkillPath = Join-NormalPath $codexSkillsDir $skillName
    Assert-PathExists -Path $codexSkillPath -Message "missing codex skill dir: $codexSkillPath" -Directory
    Assert-PathExists -Path (Join-NormalPath $codexSkillPath 'SKILL.md') -Message "missing skill definition: $(Join-NormalPath $codexSkillPath 'SKILL.md')"
}

$antigravityRules = Join-NormalPath $root '.antigravity/rules.md'
$legacyRules = Join-NormalPath $root '.agent/rules/rules.md'
Assert-PathExists -Path $antigravityRules -Message "missing antigravity rules: $antigravityRules"
Assert-PathExists -Path $legacyRules -Message "missing legacy rules copy: $legacyRules"
Assert-PathExists -Path $codexInstall -Message "missing codex install doc: $codexInstall"

Assert-FileContains -Path $legacyRules -Pattern '\.antigravity/rules\.md' -Message "legacy rules missing canonical redirect: $legacyRules"
Assert-FileContains -Path $legacyRules -Pattern 'legacy compatibility' -Message "legacy rules missing compatibility marker: $legacyRules"

Assert-FileContains -Path $antigravityRules -Pattern 'docker system prune -a' -Message "rules missing dangerous command: docker system prune -a in $antigravityRules"
Assert-FileContains -Path $antigravityRules -Pattern 'chown -R' -Message "rules missing dangerous command: chown -R in $antigravityRules"
Assert-FileContains -Path $antigravityRules -Pattern 'rollback' -Message "rules missing rollback reminder in $antigravityRules"

$activeCodexRules = Join-NormalPath $root 'codex/rules/default.rules'
if (-not (Test-Path -Path $activeCodexRules -PathType Leaf)) {
    $activeCodexRules = $codexRules
}
if (Test-Path -Path $activeCodexRules -PathType Leaf) {
    Assert-FileContains -Path $activeCodexRules -Pattern 'prefix_rule\("' -Message "codex rules missing prefix_rule(): $activeCodexRules"
    Assert-FileContains -Path $activeCodexRules -Pattern 'docker system prune -a' -Message 'codex rules missing dangerous command: docker system prune -a'
    Assert-FileContains -Path $activeCodexRules -Pattern 'chown -R' -Message 'codex rules missing dangerous command: chown -R'
}

Write-Output 'AgentCortex integrity check passed'

