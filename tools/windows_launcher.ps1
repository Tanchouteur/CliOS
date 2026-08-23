[CmdletBinding()]
param(
    [switch]$SetupOnly,
    [switch]$SmokeTest,
    [switch]$ResetEnvironment,
    [ValidateRange(0.1, 4.0)]
    [double]$Scale = 0.65,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ApplicationArguments
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvRoot = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvRoot "Scripts\python.exe"
$Requirements = Join-Path $ProjectRoot "requirements.txt"
$LogDirectory = Join-Path $ProjectRoot "logs\windows-launcher"
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$LogPath = Join-Path $LogDirectory "launcher-$Timestamp.log"
$TranscriptStarted = $false

function Write-Step([string]$Message) {
    Write-Host "[CliOS] $Message" -ForegroundColor Cyan
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$Arguments = @()
    )
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "La commande '$FilePath' a echoue (code $LASTEXITCODE)."
    }
}

function Test-Python312X64 {
    param([string]$Command, [string[]]$Prefix = @())
    try {
        $Probe = & $Command @Prefix -c "import platform,sys; print(f'{sys.version_info.major}.{sys.version_info.minor}|{platform.machine().lower()}')" 2>$null
        if ($LASTEXITCODE -ne 0) { return $false }
        return ($Probe | Select-Object -Last 1) -match '^3\.12\|(amd64|x86_64)$'
    } catch {
        return $false
    }
}

function Find-Python312 {
    $Candidates = New-Object System.Collections.Generic.List[object]
    $PyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($PyLauncher) {
        $Candidates.Add([pscustomobject]@{ Command = $PyLauncher.Source; Prefix = @("-3.12") })
    }

    foreach ($Name in @("python.exe", "python3.exe")) {
        $Command = Get-Command $Name -ErrorAction SilentlyContinue
        if ($Command) {
            $Candidates.Add([pscustomobject]@{ Command = $Command.Source; Prefix = @() })
        }
    }

    $SearchRoots = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"),
        (Join-Path $env:LOCALAPPDATA "Python\pythoncore-3.12-64\python.exe")
    )
    foreach ($CandidatePath in $SearchRoots) {
        if (Test-Path $CandidatePath) {
            $Candidates.Add([pscustomobject]@{ Command = $CandidatePath; Prefix = @() })
        }
    }

    foreach ($Candidate in $Candidates) {
        if (Test-Python312X64 -Command $Candidate.Command -Prefix $Candidate.Prefix) {
            return $Candidate
        }
    }
    return $null
}

try {
    New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null
    Start-Transcript -Path $LogPath -Force | Out-Null
    $TranscriptStarted = $true
    Write-Step "Journal : $LogPath"

    if ($ResetEnvironment -and (Test-Path $VenvRoot)) {
        Write-Step "Suppression de l'environnement virtuel existant..."
        Remove-Item -LiteralPath $VenvRoot -Recurse -Force
    }

    $Python = Find-Python312
    if (-not $Python) {
        $Winget = Get-Command winget.exe -ErrorAction SilentlyContinue
        if (-not $Winget) {
            throw "Python 3.12 x64 est absent et winget est indisponible. Installez Python 3.12 x64 depuis https://www.python.org/downloads/windows/ puis relancez ce fichier."
        }
        Write-Step "Installation de Python 3.12 x64 pour l'utilisateur courant..."
        $WingetArguments = @(
            "install", "--id", "Python.Python.3.12", "--exact", "--scope", "user",
            "--architecture", "x64", "--silent", "--accept-package-agreements",
            "--accept-source-agreements"
        )
        Invoke-Checked -FilePath $Winget.Source -Arguments $WingetArguments
        $Python = Find-Python312
        if (-not $Python) {
            throw "Python 3.12 x64 a ete installe mais reste introuvable. Fermez cette fenetre, puis relancez clios-windows.cmd."
        }
    }

    if (-not (Test-Path $VenvPython)) {
        Write-Step "Creation de .venv avec Python 3.12 x64..."
        $PythonPrefix = @($Python.Prefix)
        $PythonCommand = $Python.Command
        & $PythonCommand @PythonPrefix -m venv $VenvRoot
        if ($LASTEXITCODE -ne 0) { throw "La creation de .venv a echoue (code $LASTEXITCODE)." }
    }

    if (-not (Test-Python312X64 -Command $VenvPython)) {
        throw ".venv n'utilise pas Python 3.12 x64. Relancez avec -ResetEnvironment."
    }

    $RequirementsHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Requirements).Hash
    $HashFile = Join-Path $VenvRoot ".clios-requirements.sha256"
    $InstalledHash = if (Test-Path $HashFile) { (Get-Content -LiteralPath $HashFile -Raw).Trim() } else { "" }
    if ($InstalledHash -ne $RequirementsHash) {
        Write-Step "Installation ou mise a jour des dependances..."
        Invoke-Checked -FilePath $VenvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel")
        Invoke-Checked -FilePath $VenvPython -Arguments @("-m", "pip", "install", "--requirement", $Requirements)
        Invoke-Checked -FilePath $VenvPython -Arguments @("-m", "pip", "check")
        Set-Content -LiteralPath $HashFile -Value $RequirementsHash -Encoding ASCII
    } else {
        Write-Step "Dependances deja a jour (empreinte requirements inchangee)."
    }

    if ($SetupOnly) {
        Write-Step "Installation terminee."
        exit 0
    }

    $env:QT_SCALE_FACTOR = $Scale.ToString([Globalization.CultureInfo]::InvariantCulture)
    $MainScript = Join-Path $ProjectRoot "main.py"
    $MainArguments = @("-u", $MainScript, "--mock", "--show-cursor") + $ApplicationArguments

    if ($SmokeTest) {
        Write-Step "Smoke test Qt hors ecran..."
        $env:QT_QPA_PLATFORM = "offscreen"
        $env:CLIOS_SMOKE_TEST = "1"
        Invoke-Checked -FilePath $VenvPython -Arguments $MainArguments
        Write-Step "Smoke test termine avec succes."
        exit 0
    }

    Write-Step "Demarrage de CliOS en mode mock (echelle $Scale)..."
    & $VenvPython @MainArguments
    if ($LASTEXITCODE -ne 0) { throw "CliOS s'est arrete avec le code $LASTEXITCODE." }
} catch {
    Write-Host "[ERREUR] $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Journal complet : $LogPath" -ForegroundColor Yellow
    exit 1
} finally {
    if ($TranscriptStarted) { Stop-Transcript | Out-Null }
}
