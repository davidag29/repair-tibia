# Backward-compatible entry point; the graphical edition is now the default build.
param([string]$Python = 'python')
& (Join-Path $PSScriptRoot 'build.ps1') -Python $Python
