# Windows PowerShell 5.1 / PowerShell 7 entry point. Keep this file ASCII.
# Pass all arguments unchanged to the existing cross-platform installer.
function Get-ExpertPythonCandidates {
    if ($env:EXPERT_PYTHON) {
        [pscustomobject]@{ Path = $env:EXPERT_PYTHON; Prefix = @() }
        return
    }
    foreach ($name in @('py.exe', 'python.exe', 'python3.exe')) {
        foreach ($command in @(Get-Command $name -CommandType Application -All -ErrorAction SilentlyContinue)) {
            # The WindowsApps stub may open the Store instead of running Python.
            if ($command.Source -match '[\\/]Microsoft[\\/]WindowsApps[\\/]python3?\.exe$') { continue }
            $prefix = @()
            if ($name -eq 'py.exe') { $prefix = @('-3') }
            [pscustomobject]@{ Path = $command.Source; Prefix = $prefix }
        }
    }
    # Python may be installed while this terminal still has the old PATH.
    foreach ($root in @('HKCU:\Software\Python\PythonCore',
                        'HKLM:\Software\Python\PythonCore',
                        'HKLM:\Software\WOW6432Node\Python\PythonCore')) {
        foreach ($version in @(Get-ChildItem -LiteralPath $root -ErrorAction SilentlyContinue)) {
            $key = Get-Item -LiteralPath ($version.PSPath + '\InstallPath') -ErrorAction SilentlyContinue
            if ($null -ne $key) {
                $exe = $key.GetValue('ExecutablePath')
                if (-not $exe -and $key.GetValue('')) { $exe = Join-Path $key.GetValue('') 'python.exe' }
                if ($exe) { [pscustomobject]@{ Path = $exe; Prefix = @() } }
            }
        }
    }
    # Also cover per-user portable runtimes with no registry entry.
    if ($env:LOCALAPPDATA) {
        foreach ($folder in @('Programs\Python', 'Python')) {
            $root = Join-Path $env:LOCALAPPDATA $folder
            foreach ($directory in @(Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue)) {
                $exe = Join-Path $directory.FullName 'python.exe'
                if (Test-Path -LiteralPath $exe -PathType Leaf) {
                    [pscustomobject]@{ Path = $exe; Prefix = @() }
                }
            }
        }
    }
}

function Find-ExpertPython {
    # Probing must never trigger an automatic download by a Python launcher.
    $managerSetting = $env:PYTHON_MANAGER_AUTOMATIC_INSTALL
    $launcherSetting = $env:PYLAUNCHER_ALLOW_INSTALL
    try {
        $env:PYTHON_MANAGER_AUTOMATIC_INSTALL = 'false'
        Remove-Item Env:PYLAUNCHER_ALLOW_INSTALL -ErrorAction SilentlyContinue
        foreach ($candidate in Get-ExpertPythonCandidates) {
            try {
                $prefix = @($candidate.Prefix)
                $probe = @(& $candidate.Path @prefix -X utf8 -c 'import sys; print(sys.executable); sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>$null)
                if ($LASTEXITCODE -eq 0 -and $probe.Count -eq 1 -and
                    (Test-Path -LiteralPath ([string]$probe[0]) -PathType Leaf)) {
                    return [string]$probe[0]
                }
            } catch {
                # Missing/broken executables must not prevent the next fallback.
            }
        }
    } finally {
        $env:PYTHON_MANAGER_AUTOMATIC_INSTALL = $managerSetting
        $env:PYLAUNCHER_ALLOW_INSTALL = $launcherSetting
    }
    throw @'
Python 3.11+ was not found. No expert-team files were changed.
Install Python for Windows from https://www.python.org/downloads/windows/
Select "Add python.exe to PATH", then open a new PowerShell and retry.
If Python is already installed, set its full executable path, for example:
  $env:EXPERT_PYTHON = 'D:\Tools\Python\python.exe'
Then run this install.ps1 again. A missing "py" launcher is OK.
'@
}

# Dot-sourcing exposes discovery for Windows regression tests without installing.
if ($MyInvocation.InvocationName -eq '.') { return }
try {
    $expertPython = Find-ExpertPython
    Write-Host "Python: $expertPython"
    & $expertPython -X utf8 (Join-Path $PSScriptRoot 'install.py') @args
    exit $LASTEXITCODE
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
