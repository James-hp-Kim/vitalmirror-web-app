$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$logDir = Join-Path $root 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stdout = Join-Path $logDir 'server_stdout.log'
$stderr = Join-Path $logDir 'server_stderr.log'

$pythonExe = 'C:\Users\USER\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    $pythonExe = 'python'
}

$env:PORT = '8765'
$env:HOST = '127.0.0.1'
Set-Location $root
& $pythonExe 'server.py' 1>> $stdout 2>> $stderr
