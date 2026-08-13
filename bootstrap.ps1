param(
    [switch]$DryRun,
    [switch]$WithHealthMcp
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Installer = Join-Path $Root 'scripts\install_codex_plugin.py'
$PythonCommand = $null
$PythonPrefix = @()

if (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCommand = 'py'
    $PythonPrefix = @('-3')
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCommand = 'python'
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PythonCommand = 'python3'
} else {
    throw 'Python 3 is required to install Codex Brain Starter.'
}

$InstallerArgs = @($Installer)
if ($DryRun) { $InstallerArgs += '--dry-run' }
if ($WithHealthMcp) { $InstallerArgs += '--with-health-mcp' }

& $PythonCommand @PythonPrefix @InstallerArgs
exit $LASTEXITCODE
