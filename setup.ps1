<#
.SYNOPSIS
    Prepara o ambiente do PIDlampada e publica o repositorio no GitHub.

.DESCRIPTION
    Verifica a cadeia de ferramentas, instala as extensoes do VS Code,
    compila os ambientes, roda os testes e cria o repositorio remoto.
    Idempotente: pode rodar de novo sem quebrar nada.

.EXAMPLE
    .\setup.ps1 -RepoName PIDlampada -Private

.EXAMPLE
    .\setup.ps1 -SkipGitHub          # so prepara o ambiente local
#>
[CmdletBinding()]
param(
    [string]$RepoName = "PIDlampada",
    [switch]$Private,
    [switch]$SkipGitHub,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    OK  $msg" -ForegroundColor Green }
function Write-Warn2($msg){ Write-Host "    !   $msg" -ForegroundColor Yellow }

function Test-Tool($name, $hint) {
    if (Get-Command $name -ErrorAction SilentlyContinue) {
        Write-Ok "$name encontrado"
        return $true
    }
    Write-Warn2 "$name nao encontrado - $hint"
    return $false
}

# --------------------------------------------------------------------------
Write-Step "Verificando a cadeia de ferramentas"

$okGit = Test-Tool git    "instale com: winget install Git.Git"
$okPy  = Test-Tool python "instale com: winget install Python.Python.3.12"
$okGh  = Test-Tool gh     "instale com: winget install GitHub.cli"
$okCode= Test-Tool code   "instale o VS Code e marque 'Add to PATH'"

if (-not ($okGit -and $okPy)) {
    throw "Git e Python sao obrigatorios. Instale e rode de novo."
}

# --------------------------------------------------------------------------
Write-Step "PlatformIO"

if (-not (Get-Command pio -ErrorAction SilentlyContinue)) {
    Write-Host "    instalando platformio via pip..."
    python -m pip install --upgrade --quiet platformio
    $pioBin = Join-Path $env:USERPROFILE ".platformio\penv\Scripts"
    if (Test-Path $pioBin) { $env:PATH = "$pioBin;$env:PATH" }
}
if (Get-Command pio -ErrorAction SilentlyContinue) {
    Write-Ok ("platformio " + (pio --version))
} else {
    Write-Warn2 "pio nao entrou no PATH desta sessao. Feche e reabra o terminal."
}

# --------------------------------------------------------------------------
Write-Step "Extensoes do VS Code"

if ($okCode) {
    foreach ($ext in @("platformio.platformio-ide", "wokwi.wokwi-vscode", "ms-vscode.cpptools")) {
        code --install-extension $ext --force | Out-Null
        Write-Ok $ext
    }
} else {
    Write-Warn2 "pulando - instale manualmente: PlatformIO IDE, Wokwi Simulator"
}

# --------------------------------------------------------------------------
if (-not $SkipBuild) {
    Write-Step "Compilando e testando"
    pio run -e wokwi
    Write-Ok "firmware do simulador gerado"
    pio run -e esp32dev
    Write-Ok "firmware de hardware gerado"
    pio test -e native
    Write-Ok "testes unitarios passaram"
}

# --------------------------------------------------------------------------
Write-Step "Repositorio Git"

if (-not (Test-Path ".git")) {
    git init -b main | Out-Null
    Write-Ok "repositorio inicializado em main"
} else {
    Write-Ok "repositorio ja existe"
}

if (-not (git config user.name)) {
    Write-Warn2 "git user.name nao configurado. Rode:"
    Write-Host  '        git config --global user.name  "Gabriel Marques"'
    Write-Host  '        git config --global user.email "seu@email"'
}

git add -A
if (git diff --cached --quiet) {
    Write-Ok "nada novo para commitar"
} else {
    git commit -m "feat: scaffold do firmware, simulacao Wokwi e documentacao" | Out-Null
    Write-Ok "commit criado"
}

# --------------------------------------------------------------------------
if (-not $SkipGitHub) {
    Write-Step "GitHub"

    if (-not $okGh) {
        Write-Warn2 "gh CLI ausente - crie o repo pelo site e rode:"
        Write-Host  "        git remote add origin https://github.com/<usuario>/$RepoName.git"
        Write-Host  "        git push -u origin main"
    }
    elseif (git remote | Select-String -Quiet "origin") {
        Write-Ok "remote 'origin' ja configurado - apenas enviando"
        git push -u origin main
    }
    else {
        gh auth status 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "    autenticando no GitHub..."
            gh auth login
        }
        $vis = if ($Private) { "--private" } else { "--public" }
        gh repo create $RepoName $vis --source=. --remote=origin --push `
            --description "Camara termica compacta com controle PI em ESP32 - Projeto Integrador UNIP 2026"
        Write-Ok "repositorio publicado"
    }
}

# --------------------------------------------------------------------------
Write-Step "Proximos passos"
Write-Host @"
    1. Abra o projeto:            code .
    2. Licenca do Wokwi:          F1 -> "Wokwi: Request a New License"
    3. Compile:                   pio run -e wokwi
    4. Simule:                    F1 -> "Wokwi: Start Simulator"
    5. No monitor serial, digite  r   para rodar o ensaio de degrau

    Capturar um ensaio em CSV:
        pio device monitor -e wokwi | Tee-Object -FilePath docs\ensaios\degrau_sim.csv
"@ -ForegroundColor Gray
