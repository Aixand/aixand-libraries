#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$interpreter = $env:AIXAND_DEV_PYTHON
$prefixArgs = @()
if (-not $interpreter) {
    if (Get-Command python -ErrorAction SilentlyContinue) { $interpreter = 'python' }
    elseif (Get-Command py -ErrorAction SilentlyContinue) { $interpreter = 'py'; $prefixArgs = @('-3') }
    else {
        if ($args.Count -eq 0 -or $args[0] -in @('help', '--help', '-h')) {
            Write-Output 'Commands: help doctor develop lock check test build'
            exit 0
        }
        Write-Error 'This developer helper requires Python 3.11+. Set AIXAND_DEV_PYTHON to its executable.'
        exit 2
    }
}
& $interpreter @prefixArgs -B (Join-Path $PSScriptRoot 'dev.py') @args
exit $LASTEXITCODE
