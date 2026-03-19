# 定时唤醒任务安装脚本
# 原理：将电脑休眠（Hibernate）代替关机，任务计划程序在指定时间通过 RTC 唤醒
# 请以管理员身份运行此脚本

param(
    [string[]]$WakeTimes = @("07:00", "11:45", "18:00")
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  定时唤醒任务安装脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查管理员权限
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "错误: 请以管理员身份运行此脚本！" -ForegroundColor Red
    Write-Host "右键点击 PowerShell，选择'以管理员身份运行'" -ForegroundColor Yellow
    pause
    exit 1
}

# 启用休眠功能
Write-Host "正在启用休眠功能..." -ForegroundColor Cyan
powercfg /hibernate on
Write-Host "休眠功能已启用" -ForegroundColor Green
Write-Host ""

# 为每个时间点创建唤醒任务
foreach ($time in $WakeTimes) {
    # 将时间格式化为任务名称（07:00 -> 0700）
    $timeSafe = $time -replace ":", ""
    $taskName = "ScheduledWake_$timeSafe"

    # 删除已存在的同名任务
    $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "已删除旧任务: $taskName" -ForegroundColor Yellow
    }

    # 任务操作：空操作，仅用于触发唤醒
    $action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c echo wake"

    # 每日触发器
    $trigger = New-ScheduledTaskTrigger -Daily -At $time

    # 关键设置：WakeToRun 让系统从休眠中唤醒
    $settings = New-ScheduledTaskSettingsSet `
        -WakeToRun `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

    # 使用 SYSTEM 账户，确保唤醒权限
    $principal = New-ScheduledTaskPrincipal `
        -UserId "SYSTEM" `
        -LogonType ServiceAccount `
        -RunLevel Highest

    try {
        Register-ScheduledTask `
            -TaskName $taskName `
            -Action $action `
            -Trigger $trigger `
            -Settings $settings `
            -Principal $principal `
            -Description "定时唤醒任务 - 每天 $time 从休眠中唤醒电脑" `
            -ErrorAction Stop | Out-Null

        Write-Host "已创建任务: $taskName (每天 $time)" -ForegroundColor Green
    } catch {
        Write-Host "创建任务失败 [$taskName]: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  安装完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "使用说明:" -ForegroundColor Yellow
Write-Host "  1. 之后需要'关机'时，改用休眠：" -ForegroundColor White
Write-Host "     双击 hibernate_now.bat" -ForegroundColor Cyan
Write-Host "     或在 PowerShell 运行: shutdown /h" -ForegroundColor Cyan
Write-Host ""
Write-Host "  2. 电脑将在以下时间自动唤醒:" -ForegroundColor White
foreach ($time in $WakeTimes) {
    Write-Host "     - 每天 $time" -ForegroundColor Cyan
}
Write-Host ""
Write-Host "  3. 验证任务是否正确:" -ForegroundColor White
Write-Host "     打开任务计划程序: Win+R 输入 taskschd.msc" -ForegroundColor Cyan
Write-Host "     确认各任务'条件'标签中'唤醒计算机'已勾选" -ForegroundColor Cyan
Write-Host ""
Write-Host "  4. 查看当前唤醒计时器:" -ForegroundColor White
Write-Host "     powercfg /waketimers" -ForegroundColor Cyan
Write-Host ""

pause
