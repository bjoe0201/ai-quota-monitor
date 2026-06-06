$processName = "AI額度監控-桌面小工具"
$procs = Get-Process -Name $processName -ErrorAction SilentlyContinue

if ($procs) {
    $procs | Stop-Process -Force
    Write-Host "已終止 $($procs.Count) 個程序：$processName"
} else {
    Write-Host "找不到執行中的程序：$processName"
}
