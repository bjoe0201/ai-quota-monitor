Set-Location $PSScriptRoot

$python = $null
$candidates = @(
    'py',
    'c:\Python313\python.exe',
    'c:\Python312\python.exe',
    'c:\Python311\python.exe',
    'python'
)
foreach ($c in $candidates) {
    if (Get-Command $c -ErrorAction SilentlyContinue) {
        $python = $c
        break
    }
}

if (-not $python) {
    [System.Windows.MessageBox]::Show('Python not found. Please install Python.', 'AI 額度監控 - 桌面小工具') | Out-Null
    exit 1
}

Start-Process -FilePath $python -ArgumentList "widget_main.py" -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
