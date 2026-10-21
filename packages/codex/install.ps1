# Windows PowerShell 5.1 / PowerShell 7 entry point. Keep this file ASCII.
# Without arguments: preview, install, then verify. Explicit arguments are forwarded.
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
    param([switch]$Bootstrap)
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
    if ($Bootstrap -and -not $env:EXPERT_PYTHON) { return Install-ExpertPython }
    throw @'
Python 3.11+ was not found. No expert-team files were changed.
Install Python for Windows from https://www.python.org/downloads/windows/
Select "Add python.exe to PATH", then open a new PowerShell and retry.
If Python is already installed, set its full executable path, for example:
  $env:EXPERT_PYTHON = 'D:\Tools\Python\python.exe'
Then run this install.ps1 again. A missing "py" launcher is OK.
'@
}

function Get-ExpertPythonRelease {
    $architecture = $env:PROCESSOR_ARCHITEW6432
    if (-not $architecture) { $architecture = $env:PROCESSOR_ARCHITECTURE }
    # Pinned official release checksums; update version, filenames and hashes together.
    # https://www.python.org/downloads/release/python-3148/
    $hashes = @{
        AMD64 = @('amd64', 'a93abe456ab01bd96d7a085b3cdb6566b3063f4241360d114142fbdb07f0a310')
        x86 = @('win32', 'ff153f0044abf190d6483c02d5ade7d9666d6220fc0e2828a5e90e99be047c4c')
        ARM64 = @('arm64', '155be84ccb57c6331cf0e39001c78a1dfac3be62f403f3ff5f2e29b80dda7ebe')
    }
    if (-not $architecture -or -not $hashes.ContainsKey($architecture)) {
        throw "Unsupported Windows architecture: $architecture. Install Python 3.11+ manually."
    }
    $entry = $hashes[$architecture]
    [pscustomobject]@{
        Name = "ExpertTeam-3.14.8-$($entry[0])"
        Url = "https://www.python.org/ftp/python/3.14.8/python-3.14.8-embed-$($entry[0]).zip"
        Sha256 = $entry[1]
    }
}

function Save-ExpertPythonArchive($Url, $Destination) {
    $oldProtocol = [Net.ServicePointManager]::SecurityProtocol
    $oldProgress = $ProgressPreference
    try {
        [Net.ServicePointManager]::SecurityProtocol = $oldProtocol -bor [Net.SecurityProtocolType]::Tls12
        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $Destination -TimeoutSec 180 -ErrorAction Stop
    } finally {
        [Net.ServicePointManager]::SecurityProtocol = $oldProtocol
        $ProgressPreference = $oldProgress
    }
}

function Test-ExpertRuntime($Executable) {
    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) { return $false }
    try {
        & $Executable -X utf8 -c 'import sys, ssl, tomllib; sys.exit(0 if sys.version_info >= (3, 11) else 1)' *> $null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

function Install-ExpertPython {
    if (-not $env:LOCALAPPDATA) { throw 'LOCALAPPDATA is unavailable. Install Python 3.11+ manually.' }
    $release = Get-ExpertPythonRelease
    $root = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'Programs\Python'))
    # Do not redirect runtime writes through a directory junction or symlink.
    $ancestor = $root
    while ($ancestor) {
        if (Test-Path -LiteralPath $ancestor) {
            $item = Get-Item -LiteralPath $ancestor -Force -ErrorAction Stop
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw "Python runtime path contains a reparse point: $ancestor. Set EXPERT_PYTHON to an existing Python."
            }
        }
        $ancestor = [IO.Path]::GetDirectoryName($ancestor)
    }
    $target = Join-Path $root $release.Name
    $exe = Join-Path $target 'python.exe'
    if (Test-Path -LiteralPath $target) {
        if (Test-ExpertRuntime $exe) { return $exe }
        throw "Existing runtime is unusable: $target. Move it aside or set EXPERT_PYTHON to a working Python."
    }
    $null = New-Item -ItemType Directory -Path $root -Force -ErrorAction Stop
    # A unique staging directory prevents incomplete downloads becoming discoverable.
    $stage = Join-Path $root ('.expert-download-' + [guid]::NewGuid().ToString('N'))
    $null = New-Item -ItemType Directory -Path $stage -ErrorAction Stop
    try {
        $archive = Join-Path $stage 'python.zip'
        Write-Host "Python 3.11+ not found. Downloading official Python: $($release.Url)"
        Save-ExpertPythonArchive $release.Url $archive
        if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256 -ErrorAction Stop).Hash -ne $release.Sha256) {
            throw 'Python download SHA-256 mismatch. Nothing from the download was executed; retry the installer.'
        }
        $payload = Join-Path $stage 'runtime'
        Expand-Archive -LiteralPath $archive -DestinationPath $payload -ErrorAction Stop
        if (-not (Test-ExpertRuntime (Join-Path $payload 'python.exe'))) {
            throw 'Downloaded Python could not run on this Windows version. Install Python 3.11+ manually.'
        }
        # Directory.Move refuses to replace an existing installation.
        [IO.Directory]::Move($payload, $target)
        Write-Host "Python installed: $exe"
        return $exe
    } catch {
        throw "Python setup failed: $($_.Exception.Message) Check access to https://www.python.org or set EXPERT_PYTHON to an existing Python 3.11+."
    } finally {
        # Delete only this invocation's staging directory, never an existing runtime.
        $resolvedStage = [IO.Path]::GetFullPath($stage)
        if ([IO.Path]::GetDirectoryName($resolvedStage) -eq $root -and
            [IO.Path]::GetFileName($resolvedStage) -like '.expert-download-*') {
            Remove-Item -LiteralPath $resolvedStage -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}


# Dot-sourcing exposes discovery for Windows regression tests without installing.
if ($MyInvocation.InvocationName -eq '.') { return }
try {
    $expertPython = Find-ExpertPython -Bootstrap:($args.Count -eq 0)
    Write-Host "Python: $expertPython"
    $installer = Join-Path $PSScriptRoot 'install.py'
    if ($args.Count -eq 0) {
        Write-Host '[1/3] Preview installation'
        & $expertPython -X utf8 $installer install --dry-run
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Write-Host '[2/3] Install Codex expert team'
        & $expertPython -X utf8 $installer install
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Write-Host '[3/3] Verify installed files'
        & $expertPython -X utf8 $installer check
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Write-Host 'Installation verified. Open a new Codex chat to load the expert team.'
        exit 0
    }
    & $expertPython -X utf8 $installer @args
    exit $LASTEXITCODE
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
