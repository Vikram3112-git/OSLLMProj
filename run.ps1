$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
function Stop-WithHelp($Message) { Write-Host "`nERROR: $Message" -ForegroundColor Red; exit 1 }
$Mode = if ($args.Count -gt 0) { [string]$args[0] } else { '' }
$BaseModel = if ($env:OSLLM_BASE) { $env:OSLLM_BASE } elseif ($Mode -eq 'fast') { 'qwen3:4b' } elseif ($Mode -eq 'quality') { 'qwen3:8b' } else { '' }
if (-not $BaseModel) { if ((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory -ge 12GB) { $BaseModel = 'qwen3:8b' } else { $BaseModel = 'qwen3:4b' } }
$Python = Get-Command py -ErrorAction SilentlyContinue
if ($Python) { $PyArgs = @('-3.11') ; & py -3.11 --version *> $null; if ($LASTEXITCODE -ne 0) { $PyArgs = @('-3') }; $Py = 'py' } else { $Python = Get-Command python -ErrorAction SilentlyContinue; if (-not $Python) { Stop-WithHelp 'Python 3.10+ not found. Install Python from https://www.python.org/downloads/windows/ and tick “Add Python to PATH”.' }; $PyArgs = @(); $Py = 'python' }
try { & $Py @PyArgs -c "import sys; assert sys.version_info >= (3,10)" } catch { Stop-WithHelp 'Python 3.10 or newer is required.' }
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) { Stop-WithHelp 'Ollama is not installed. Install it from https://ollama.com/download/windows, open it once, then run run.bat again.' }
& ollama list *> $null
if ($LASTEXITCODE -ne 0) { Start-Process "$env:LOCALAPPDATA\Programs\Ollama\ollama app.exe" -ErrorAction SilentlyContinue; Start-Sleep -Seconds 4; & ollama list *> $null }
if ($LASTEXITCODE -ne 0) { Stop-WithHelp 'Ollama is not running. Start the Ollama app from the Start menu and retry.' }
$Models = (& ollama list | Out-String)
if ($Models -notmatch [regex]::Escape($BaseModel)) { Write-Host "`nDownloading $BaseModel (first run only; several GB)..." -ForegroundColor Cyan; & ollama pull $BaseModel; if ($LASTEXITCODE -ne 0) { Stop-WithHelp 'Model download failed. Check internet and disk space, then retry.' } }
$ActiveModelfile = (Get-Content Modelfile -Raw) -replace '(?m)^FROM .*$', "FROM $BaseModel"
[System.IO.File]::WriteAllText((Join-Path $PSScriptRoot 'data/Modelfile.active'), $ActiveModelfile, [System.Text.UTF8Encoding]::new($false))
& ollama create osllm -f data.Modelfile.active
if ($LASTEXITCODE -ne 0) { Stop-WithHelp 'Could not create OSLLM model.' }
Remove-Item data.Modelfile.active -ErrorAction SilentlyContinue
if (-not (Test-Path venv)) { Write-Host "`nCreating Python environment..." -ForegroundColor Cyan; & $Py @PyArgs -m venv venv; if ($LASTEXITCODE -ne 0) { Stop-WithHelp 'Could not create Python environment.' } }
$Vpy = Join-Path $PSScriptRoot 'venv\Scripts\python.exe'
if (-not (Test-Path venv/.installed) -or (Get-Item requirements.txt).LastWriteTime -gt (Get-Item venv/.installed -ErrorAction SilentlyContinue).LastWriteTime) {
  Write-Host "`nInstalling Python packages (first run only)..." -ForegroundColor Cyan
  & $Vpy -m pip install --upgrade pip; if ($LASTEXITCODE -ne 0) { Stop-WithHelp 'pip upgrade failed.' }
  & $Vpy -m pip install torch; if ($LASTEXITCODE -ne 0) { Stop-WithHelp 'PyTorch installation failed.' }
  & $Vpy -m pip install -r requirements.txt; if ($LASTEXITCODE -ne 0) { Stop-WithHelp 'Dependency installation failed. Check README troubleshooting.' }
  New-Item -ItemType File -Path venv/.installed -Force | Out-Null
}
$env:PSLLM_MODEL = if ($env:PSLLM_MODEL) { $env:PSLLM_MODEL } else { 'osllm' }
$SourcesVersion = '2'
if ($Mode -eq 'sources' -or -not (Test-Path knowledge_base/universal/book_*) -or -not (Test-Path knowledge_base/universal/.version) -or (Get-Content knowledge_base/universal/.version -Raw).Trim() -ne $SourcesVersion) {
  Write-Host "`nDownloading reference sources (first run)..." -ForegroundColor Cyan
  & $Vpy fetch_sources.py
  if ($LASTEXITCODE -ne 0) { Write-Warning 'Some sources may not have downloaded. Continuing.' }
  Set-Content knowledge_base/universal/.version $SourcesVersion
}
New-Item -ItemType Directory -Force knowledge_base/my_files | Out-Null
$Index = 'data/faiss.index'
$NeedsIndex = $Mode -eq 'ingest' -or $Mode -eq 'sources' -or -not (Test-Path $Index)
if (-not $NeedsIndex -and (Get-ChildItem knowledge_base -Recurse -File | Where-Object { $_.LastWriteTime -gt (Get-Item $Index).LastWriteTime } | Select-Object -First 1)) { $NeedsIndex = $true }
if ($NeedsIndex) { Write-Host "`nBuilding search index (first run downloads an embedding model)..." -ForegroundColor Cyan; & $Vpy ingest.py; if ($LASTEXITCODE -ne 0) { Stop-WithHelp 'Knowledge indexing failed. Read the error and retry.' } }
if ($Mode -eq 'ingest' -or $Mode -eq 'sources') { exit 0 }
if ($Mode -eq 'test') { $TestArgs = @($args | Select-Object -Skip 1); & $Vpy test_osllm.py @TestArgs; exit $LASTEXITCODE }
Write-Host "`nStarting OSLLM at http://localhost:8501. Press Ctrl+C to stop." -ForegroundColor Cyan
Start-Process 'http://localhost:8501'
& $Vpy server.py
exit $LASTEXITCODE
