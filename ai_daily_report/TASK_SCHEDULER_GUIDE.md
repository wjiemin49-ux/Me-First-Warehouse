# Windows 任务计划程序设置说明

## 已创建的定时任务

以下 5 个定时任务已成功创建并处于就绪状态：

| 任务名称 | 执行时间 | 下次运行 | 状态 |
|---------|---------|---------|------|
| AI_Daily_Report_06 | 每天 6:00 AM | 2026/3/19 6:00:00 | ✅ Ready |
| AI_Daily_Report_08 | 每天 8:00 AM | 2026/3/19 8:00:00 | ✅ Ready |
| AI_Daily_Report_10 | 每天 10:00 AM | 2026/3/19 10:00:00 | ✅ Ready |
| AI_Daily_Report_12 | 每天 12:00 PM | 2026/3/19 12:00:00 | ✅ Ready |
| AI_Daily_Report_18 | 每天 6:00 PM | 2026/3/19 18:00:00 | ✅ Ready |

## 查看任务

### 使用 PowerShell

```powershell
# 查看所有 AI 日报任务
Get-ScheduledTask | Where-Object {$_.TaskName -like "AI_Daily_Report*"}

# 查看任务详情
Get-ScheduledTaskInfo -TaskName "AI_Daily_Report_06"
```

### 使用任务计划程序 GUI

1. 按 `Win + R`，输入 `taskschd.msc`，回车
2. 在任务列表中找到 `AI_Daily_Report_*` 任务
3. 双击查看详细配置

## 手动测试任务

### 使用 PowerShell

```powershell
# 手动运行 6:00 AM 任务
Start-ScheduledTask -TaskName "AI_Daily_Report_06"

# 查看任务运行历史
Get-ScheduledTask -TaskName "AI_Daily_Report_06" | Get-ScheduledTaskInfo
```

### 使用任务计划程序 GUI

1. 右键点击任务
2. 选择"运行"
3. 查看"历史记录"选项卡查看执行结果

## 修改任务

### 修改执行时间

```powershell
# 修改为 7:00 AM
$trigger = New-ScheduledTaskTrigger -Daily -At 7:00AM
Set-ScheduledTask -TaskName "AI_Daily_Report_06" -Trigger $trigger
```

### 禁用任务

```powershell
Disable-ScheduledTask -TaskName "AI_Daily_Report_06"
```

### 启用任务

```powershell
Enable-ScheduledTask -TaskName "AI_Daily_Report_06"
```

## 删除任务

### 删除单个任务

```powershell
Unregister-ScheduledTask -TaskName "AI_Daily_Report_06" -Confirm:$false
```

### 删除所有任务

```powershell
Unregister-ScheduledTask -TaskName "AI_Daily_Report_06" -Confirm:$false
Unregister-ScheduledTask -TaskName "AI_Daily_Report_08" -Confirm:$false
Unregister-ScheduledTask -TaskName "AI_Daily_Report_10" -Confirm:$false
Unregister-ScheduledTask -TaskName "AI_Daily_Report_12" -Confirm:$false
Unregister-ScheduledTask -TaskName "AI_Daily_Report_18" -Confirm:$false
```

## 故障排查

### 任务未执行

1. **检查任务历史记录**
   - 打开任务计划程序
   - 右键任务 → 属性 → 历史记录
   - 查看错误代码和消息

2. **检查 Python 路径**
   ```powershell
   where.exe python
   ```
   确保路径与任务中配置的一致

3. **检查工作目录**
   - 任务的"起始于"应设置为：`d:\me\脚本\ai_daily_report`

4. **检查权限**
   - 任务应以当前用户身份运行
   - 不需要管理员权限

### 任务执行但无邮件

1. **查看日志文件**
   ```bash
   cat d:/me/脚本/ai_daily_report/logs/ai_daily_report_*.log
   ```

2. **检查环境变量**
   - 确认 `.env` 文件存在且配置正确

3. **手动运行测试**
   ```bash
   cd d:/me/脚本/ai_daily_report
   python main.py
   ```

### 查看最近执行结果

```powershell
Get-ScheduledTask -TaskName "AI_Daily_Report_*" | ForEach-Object {
    $info = Get-ScheduledTaskInfo $_
    [PSCustomObject]@{
        TaskName = $_.TaskName
        LastRunTime = $info.LastRunTime
        LastResult = $info.LastTaskResult
        NextRunTime = $info.NextRunTime
    }
} | Format-Table
```

## 重新安装任务

如果需要重新创建所有任务，运行：

```powershell
# 以管理员身份运行 PowerShell
cd d:\me\脚本\ai_daily_report
.\setup_tasks.ps1
```

或者使用批处理脚本：

```cmd
cd d:\me\脚本\ai_daily_report
setup_tasks.bat
```

## 注意事项

1. **电源管理**：确保任务的"条件"选项卡中，取消勾选"只有在计算机使用交流电源时才启动此任务"
2. **用户登录**：任务配置为"不管用户是否登录都要运行"
3. **网络连接**：确保执行时有网络连接
4. **日志监控**：定期检查 `logs/` 目录下的日志文件

---

**所有定时任务已成功配置！** 🎉
