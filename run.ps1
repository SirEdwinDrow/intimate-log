# Запуск Intimate Log на Windows без Docker:  powershell -ExecutionPolicy Bypass -File .\run.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Test-GoodPython($ver) {
    # Обычный (не free-threaded) CPython 3.10+
    try {
        & py $ver -c "import sys,sysconfig; ok = sys.version_info >= (3,10) and not sysconfig.get_config_var('Py_GIL_DISABLED'); sys.exit(0 if ok else 1)" 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

# Если venv создан на free-threaded Python (3.13t) — пересоздаём
if (Test-Path $venvPy) {
    & $venvPy -c "import sysconfig,sys; sys.exit(1 if sysconfig.get_config_var('Py_GIL_DISABLED') else 0)"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Найдено окружение на free-threaded Python, пересоздаю..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force .venv
    }
}

if (-not (Test-Path $venvPy)) {
    $chosen = $null
    foreach ($v in @("-3.13", "-3.12", "-3.14", "-3.11", "-3.10")) {
        if (Test-GoodPython $v) { $chosen = $v; break }
    }
    if (-not $chosen) {
        Write-Host "Не найден обычный Python 3.10-3.14." -ForegroundColor Red
        Write-Host "Установи Python 3.13 с https://www.python.org/downloads/ (галочка 'Add python.exe to PATH')." -ForegroundColor Red
        Write-Host "Сейчас установлены:"; py --list
        exit 1
    }
    Write-Host "Создаю окружение на Python $chosen ..." -ForegroundColor Cyan
    & py $chosen -m venv .venv
    & $venvPy -m pip install --upgrade pip
    & $venvPy -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Remove-Item -Recurse -Force .venv
        Write-Host "Не удалось установить зависимости." -ForegroundColor Red
        exit 1
    }
    # HEIC с iPhone — по возможности, без него всё работает
    & $venvPy -m pip install -r requirements-heif.txt 2>$null
    if ($LASTEXITCODE -ne 0) { Write-Host "pillow-heif не установился, HEIC-фото не поддерживаются (не критично)." -ForegroundColor Yellow }
}

# Постоянный секретный ключ, чтобы не разлогинивало после перезапуска
if (-not (Test-Path ".secret_key")) {
    & $venvPy -c "import secrets; print(secrets.token_urlsafe(48))" | Set-Content -NoNewline -Encoding ascii ".secret_key"
}
$env:SECRET_KEY = (Get-Content ".secret_key" -Raw).Trim()
if (-not $env:ALLOW_REGISTRATION) { $env:ALLOW_REGISTRATION = "true" }

Write-Host "Открой http://127.0.0.1:8000  (Ctrl+C - остановить)" -ForegroundColor Green
& $venvPy -m uvicorn app.main:app --host 127.0.0.1 --port 8000
