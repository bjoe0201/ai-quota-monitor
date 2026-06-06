Set-Location $PSScriptRoot

# 找 Python
$python = $null
foreach ($c in @('py', 'python')) {
    if (Get-Command $c -ErrorAction SilentlyContinue) { $python = $c; break }
}
if (-not $python) { Write-Error "Python not found."; exit 1 }

# 清理舊的 build / dist
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

# 執行 PyInstaller
& $python -m PyInstaller widget_build.spec -y
if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller failed."; exit 1 }

$out = "dist\AI額度監控-桌面小工具"
if (Test-Path $out) {
    Write-Host "Build OK -> $out"
    explorer $out
} else {
    Write-Error "Output folder not found: $out"
    exit 1
}
