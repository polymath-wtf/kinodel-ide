$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv313\Scripts\python.exe'
Push-Location -LiteralPath $root
try {
    & $python -c "import pathlib, platform, sqlite3, sys; print(sys.executable); print(sys.version); print('SQLite', sqlite3.sqlite_version); assert platform.python_implementation() == 'CPython' and sys.version_info[:2] == (3, 13); assert pathlib.Path(sys.prefix).resolve() == pathlib.Path('.venv313').resolve()"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $python -m unittest discover -s tests -v
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
