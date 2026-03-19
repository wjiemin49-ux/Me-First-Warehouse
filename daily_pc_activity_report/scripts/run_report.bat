@echo off
REM 每日电脑活动简报运行脚本
REM 用于 Windows 任务计划程序

cd /d "d:\me\脚本\daily_pc_activity_report"
python -m daily_pc_activity_report >> logs\task_scheduler.log 2>&1
