# Windows 任务计划程序设置脚本
# 请以管理员身份运行 PowerShell，然后执行此脚本

$pythonPath = "C:\Users\MACHENIKE\AppData\Local\Programs\Python\Python312\python.exe"
$scriptPath = "d:\me\脚本\ai_daily_report\main.py"

Write-Host "Creating Windows Scheduled Tasks for AI Daily Report..." -ForegroundColor Green
Write-Host ""

# 创建 6:00 AM 任务
Write-Host "Creating 6:00 AM task..." -ForegroundColor Yellow
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument $scriptPath -WorkingDirectory "d:\me\脚本\ai_daily_report"
$trigger = New-ScheduledTaskTrigger -Daily -At 6:00AM
Register-ScheduledTask -TaskName "AI_Daily_Report_06" -Action $action -Trigger $trigger -Force
Write-Host "[OK] 6:00 AM task created" -ForegroundColor Green
Write-Host ""

# 创建 8:00 AM 任务
Write-Host "Creating 8:00 AM task..." -ForegroundColor Yellow
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument $scriptPath -WorkingDirectory "d:\me\脚本\ai_daily_report"
$trigger = New-ScheduledTaskTrigger -Daily -At 8:00AM
Register-ScheduledTask -TaskName "AI_Daily_Report_08" -Action $action -Trigger $trigger -Force
Write-Host "[OK] 8:00 AM task created" -ForegroundColor Green
Write-Host ""

# 创建 10:00 AM 任务
Write-Host "Creating 10:00 AM task..." -ForegroundColor Yellow
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument $scriptPath -WorkingDirectory "d:\me\脚本\ai_daily_report"
$trigger = New-ScheduledTaskTrigger -Daily -At 10:00AM
Register-ScheduledTask -TaskName "AI_Daily_Report_10" -Action $action -Trigger $trigger -Force
Write-Host "[OK] 10:00 AM task created" -ForegroundColor Green
Write-Host ""

# 创建 12:00 PM 任务
Write-Host "Creating 12:00 PM task..." -ForegroundColor Yellow
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument $scriptPath -WorkingDirectory "d:\me\脚本\ai_daily_report"
$trigger = New-ScheduledTaskTrigger -Daily -At 12:00PM
Register-ScheduledTask -TaskName "AI_Daily_Report_12" -Action $action -Trigger $trigger -Force
Write-Host "[OK] 12:00 PM task created" -ForegroundColor Green
Write-Host ""

# 创建 6:00 PM 任务
Write-Host "Creating 6:00 PM task..." -ForegroundColor Yellow
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument $scriptPath -WorkingDirectory "d:\me\脚本\ai_daily_report"
$trigger = New-ScheduledTaskTrigger -Daily -At 6:00PM
Register-ScheduledTask -TaskName "AI_Daily_Report_18" -Action $action -Trigger $trigger -Force
Write-Host "[OK] 6:00 PM task created" -ForegroundColor Green
Write-Host ""

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "All tasks created! Verifying..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Get-ScheduledTask | Where-Object {$_.TaskName -like "AI_Daily_Report*"} | Format-Table TaskName, State, @{Label="Next Run Time"; Expression={(Get-ScheduledTaskInfo $_).NextRunTime}}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "To test a task manually, run:" -ForegroundColor Yellow
Write-Host "  Start-ScheduledTask -TaskName 'AI_Daily_Report_06'" -ForegroundColor White
Write-Host ""
Write-Host "To delete all tasks, run:" -ForegroundColor Yellow
Write-Host "  Unregister-ScheduledTask -TaskName 'AI_Daily_Report_06' -Confirm:`$false" -ForegroundColor White
Write-Host "  Unregister-ScheduledTask -TaskName 'AI_Daily_Report_08' -Confirm:`$false" -ForegroundColor White
Write-Host "  Unregister-ScheduledTask -TaskName 'AI_Daily_Report_10' -Confirm:`$false" -ForegroundColor White
Write-Host "  Unregister-ScheduledTask -TaskName 'AI_Daily_Report_12' -Confirm:`$false" -ForegroundColor White
Write-Host "  Unregister-ScheduledTask -TaskName 'AI_Daily_Report_18' -Confirm:`$false" -ForegroundColor White
Write-Host ""
