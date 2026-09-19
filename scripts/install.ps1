# Wrapper referencing root install.ps1
$rootInstall = Join-Path (Split-Path -Parent $PSScriptRoot) "install.ps1"
if (Test-Path $rootInstall) {
    & $rootInstall @args
} else {
    throw "Root install.ps1 not found at $rootInstall"
}
