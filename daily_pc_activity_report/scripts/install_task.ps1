# Windows 任务计划程序安装脚本
# 请以管理员身份运行此脚本

param(
    [string]$TaskName = "DailyPCActivityReport",
    [string]$ProjectPath = "d:\me\脚本\daily_pc_activity_report",
    [string]$Time = "23:00"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "每日电脑活动简报 - 任务计划程序安装" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查是否以管理员身份运行
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "错误: 请以管理员身份运行此脚本！" -ForegroundColor Red
    Write-Host "右键点击 PowerShell，选择'以管理员身份运行'" -ForegroundColor Yellow
    pause
    exit 1
}

# 检查项目路径是否存在
if (-not (Test-Path $ProjectPath)) {
    Write-Host "错误: 项目路径不存在: $ProjectPath" -ForegroundColor Red
    Write-Host "请修改脚本中的 ProjectPath 参数" -ForegroundColor Yellow
    pause
    exit 1
}

# 检查 Python 是否安装
try {
    $pythonVersion = python --version 2>&1
    Write-Host "检测到 Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "错误: 未检测到 Python，请先安装 Python 3.10+" -ForegroundColor Red
    pause
    exit 1
}

# 删除已存在的任务（如果有）
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "检测到已存在的任务，正在删除..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "已删除旧任务" -ForegroundColor Green
}

# 创建任务操作
$action = New-ScheduledTaskAction `
    -Execute "python" `
    -Argument "-m daily_pc_activity_report" `
    -WorkingDirectory $ProjectPath

# 创建任务触发器（每天指定时间）
$trigger = New-ScheduledTaskTrigger -Daily -At $Time

# 创建任务设置
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable:$false `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

# 创建任务主体（使用当前用户）
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

# 注册任务
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description "每日电脑活动简报自动生成任务" `
        -ErrorAction Stop

    Write-Host ""
    Write-Host "✅ 任务创建成功！" -ForegroundColor Green
    Write-Host ""
    Write-Host "任务信息:" -ForegroundColor Cyan
    Write-Host "  任务名称: $TaskName"
    Write-Host "  执行时间: 每天 $Time"
    Write-Host "  工作目录: $ProjectPath"
    Write-Host "  执行命令: python -m daily_pc_activity_report"
    Write-Host ""
    Write-Host "您可以在'任务计划程序'中查看和管理此任务" -ForegroundColor Yellow
    Write-Host "打开方式: Win+R 输入 taskschd.msc" -ForegroundColor Yellow
    Write-Host ""

    # 询问是否立即测试运行
    $test = Read-Host "是否立即测试运行任务？(Y/N)"
    if ($test -eq "Y" -or $test -eq "y") {
        Write-Host "正在运行任务..." -ForegroundColor Cyan
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "任务已启动，请查看日志文件确认执行结果" -ForegroundColor Green
        Write-Host "日志位置: $ProjectPath\logs\" -ForegroundColor Yellow
    }

} catch {
    Write-Host ""
    Write-Host "❌ 任务创建失败: $_" -ForegroundColor Red
    pause
    exit 1
}

Write-Host ""
Write-Host "按任意键退出..." -ForegroundColor Gray
pause
