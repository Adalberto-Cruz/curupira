param([ValidateRange(1, 65535)][int]$Port = 8766, [switch]$CheckConfig)
$ErrorActionPreference = 'Stop'
$pythonExe = Join-Path (Split-Path -Parent $PSScriptRoot) '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Crie o .venv e instale requirements.txt conforme o LEIA-ME.' }
$serverArgs = @("$PSScriptRoot/servidor_earth_engine.py", '--port', $Port)
if ($CheckConfig) { $serverArgs += '--check-config' }
& $pythonExe @serverArgs
if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel iniciar ou validar o Hibama. Confira a mensagem acima.' }
