# AI 每日新闻自动化脚本

一个稳定、可维护的 Python 自动化脚本，每天自动抓取 AI 相关新闻，整理成中文日报并发送到 QQ 邮箱。

## 功能特点

- ✅ 自动抓取 6 个稳定的国际 AI 新闻源（RSS）
- ✅ 智能去重和优先级排序
- ✅ 支持 Claude API 翻译成中文（可选）
- ✅ 精美的 HTML 邮件格式
- ✅ SQLite 持久化存储，避免重复推送
- ✅ 完善的错误处理和日志记录
- ✅ 支持 Windows 任务计划程序定时执行

## 新闻来源

本脚本从以下 6 个稳定的 RSS 源抓取新闻：

1. **Google DeepMind** - 官方博客
2. **Google AI Research** - 官方研究博客
3. **Microsoft Azure AI** - 官方 AI 博客
4. **NVIDIA AI** - 生成式 AI 博客
5. **TechCrunch AI** - AI 科技新闻
6. **VentureBeat** - 科技新闻

## 项目结构

```
ai_daily_report/
├── main.py                          # 主程序入口
├── requirements.txt                 # Python 依赖
├── README.md                        # 本文档
├── .env.example                     # 环境变量模板
├── .env                            # 实际配置（已配置）
├── config/
│   └── sources.py                  # 新闻源配置
├── src/
│   ├── fetchers/
│   │   └── rss_fetcher.py         # RSS 抓取器
│   ├── processors/
│   │   ├── cleaner.py             # 内容清洗
│   │   ├── deduper.py             # 去重逻辑
│   │   ├── sorter.py              # 优先级排序
│   │   └── translator.py          # 中文翻译
│   ├── mail/
│   │   └── sender.py              # 邮件发送
│   ├── storage/
│   │   └── store.py               # SQLite 存储
│   ├── utils/
│   │   ├── logger.py              # 日志配置
│   │   └── time_utils.py          # 时间工具
│   └── models/
│       └── news_item.py           # 数据模型
├── data/
│   └── sent_records.db            # SQLite 数据库
├── output/
│   └── latest_report.html         # 最新报告
└── logs/
    └── ai_daily_report_*.log      # 日志文件
```

## 安装步骤

### 1. 确保已安装 Python 3.11+

```bash
python --version
```

### 2. 进入项目目录

```bash
cd d:\me\脚本\ai_daily_report
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

依赖包括：
- `feedparser` - RSS 解析
- `requests` - HTTP 请求
- `beautifulsoup4` - HTML 解析
- `lxml` - XML 解析
- `python-dotenv` - 环境变量管理
- `anthropic` - Claude API 客户端

## 环境变量配置

环境变量已配置在 `.env` 文件中：

```env
# Claude API（用于翻译）
ANTHROPIC_API_KEY=<已配置>
ANTHROPIC_MODEL=claude-sonnet-4-6

# QQ 邮箱配置
SMTP_HOST=smtp.qq.com
SMTP_PORT=587
SMTP_USERNAME=3508887237@qq.com
SMTP_PASSWORD=gufjofzfrraqcijb
EMAIL_FROM=3508887237@qq.com
EMAIL_TO=3964685891@qq.com

# 脚本配置
LOG_LEVEL=INFO
TIME_WINDOW_HOURS=24
MAX_ITEMS_TO_SEND=15
USE_LLM_TRANSLATION=true
```

## 使用方法

### 手动运行

```bash
# 完整运行（抓取、翻译、发送邮件）
python main.py

# Dry-run 模式（仅生成报告，不发送邮件）
python main.py --dry-run

# 不使用 LLM 翻译（保留原文）
python main.py --no-llm

# 自定义时间窗口（抓取最近 12 小时）
python main.py --hours 12

# 自定义最大发送条数
python main.py --max-items 10
```

### 查看日志

```bash
# 查看最新日志
cat logs/ai_daily_report_2026-03-18.log

# 实时查看日志
tail -f logs/ai_daily_report_2026-03-18.log
```

## Windows 任务计划程序设置

### 方法 1：使用图形界面

1. 打开"任务计划程序"（Task Scheduler）
   - 按 `Win + R`，输入 `taskschd.msc`，回车

2. 创建基本任务
   - 点击右侧"创建基本任务"
   - 名称：`AI_Daily_Report_06`
   - 描述：`每天早上 6 点发送 AI 新闻日报`

3. 设置触发器
   - 选择"每天"
   - 开始时间：`06:00:00`
   - 每隔：`1` 天

4. 设置操作
   - 选择"启动程序"
   - 程序或脚本：`python.exe` 的完整路径
     - 例如：`C:\Python311\python.exe`
   - 添加参数：`main.py`
   - 起始于：`d:\me\脚本\ai_daily_report`

5. 完成设置
   - 勾选"当单击完成时，打开此任务属性的对话框"
   - 在"常规"选项卡中，勾选"不管用户是否登录都要运行"
   - 在"条件"选项卡中，取消勾选"只有在计算机使用交流电源时才启动此任务"

6. 重复以上步骤，创建其他时间的任务：
   - `AI_Daily_Report_08` - 每天 8:00
   - `AI_Daily_Report_10` - 每天 10:00
   - `AI_Daily_Report_12` - 每天 12:00
   - `AI_Daily_Report_18` - 每天 18:00

### 方法 2：使用命令行（PowerShell 管理员模式）

```powershell
# 创建 6:00 任务
schtasks /create /tn "AI_Daily_Report_06" /tr "python.exe d:\me\脚本\ai_daily_report\main.py" /sc daily /st 06:00 /ru SYSTEM

# 创建 8:00 任务
schtasks /create /tn "AI_Daily_Report_08" /tr "python.exe d:\me\脚本\ai_daily_report\main.py" /sc daily /st 08:00 /ru SYSTEM

# 创建 10:00 任务
schtasks /create /tn "AI_Daily_Report_10" /tr "python.exe d:\me\脚本\ai_daily_report\main.py" /sc daily /st 10:00 /ru SYSTEM

# 创建 12:00 任务
schtasks /create /tn "AI_Daily_Report_12" /tr "python.exe d:\me\脚本\ai_daily_report\main.py" /sc daily /st 12:00 /ru SYSTEM

# 创建 18:00 任务
schtasks /create /tn "AI_Daily_Report_18" /tr "python.exe d:\me\脚本\ai_daily_report\main.py" /sc daily /st 18:00 /ru SYSTEM
```

### 验证任务

```powershell
# 查看所有任务
schtasks /query | findstr "AI_Daily_Report"

# 手动运行任务测试
schtasks /run /tn "AI_Daily_Report_06"
```

## 工作流程

1. **抓取阶段**：从 6 个 RSS 源抓取最近 24 小时的新闻
2. **清洗阶段**：移除 HTML 标签、清理 URL、过滤非 AI 内容
3. **去重阶段**：基于 URL、标题和相似度去重，检查数据库历史记录
4. **排序阶段**：根据来源权威性、关键词、时间新鲜度计算优先级
5. **翻译阶段**：使用 Claude API 将标题和摘要翻译成中文
6. **生成报告**：生成精美的 HTML 邮件
7. **发送邮件**：通过 QQ 邮箱 SMTP 发送
8. **记录存储**：标记已发送，避免重复推送

## 常见问题

### Q1: 邮件发送失败，提示"535 Login Fail"

**A:** QQ 邮箱需要使用授权码，不是 QQ 密码。请确保 `.env` 中的 `SMTP_PASSWORD` 是 QQ 邮箱的授权码（已配置：`gufjofzfrraqcijb`）。

### Q2: 如何获取 QQ 邮箱授权码？

**A:**
1. 登录 QQ 邮箱网页版
2. 设置 → 账户 → POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务
3. 开启 SMTP 服务
4. 生成授权码（已为您配置好）

### Q3: 没有收到邮件怎么办？

**A:**
1. 检查日志文件：`logs/ai_daily_report_*.log`
2. 检查垃圾邮件文件夹
3. 确认 `.env` 配置正确
4. 手动运行测试：`python main.py`

### Q4: 如何关闭 LLM 翻译？

**A:**
- 临时关闭：`python main.py --no-llm`
- 永久关闭：修改 `.env` 中 `USE_LLM_TRANSLATION=false`

### Q5: 如何添加新的新闻源？

**A:** 编辑 `config/sources.py`，添加新的 RSS 源：

```python
{
    "name": "新源名称",
    "url": "https://example.com/feed.xml",
    "type": "rss",
    "enabled": True,
    "priority_boost": 1,
    "description": "描述"
}
```

### Q6: 任务计划程序中任务不执行？

**A:**
1. 检查任务的"历史记录"选项卡查看错误
2. 确保 Python 路径正确
3. 确保"起始于"目录设置为项目根目录
4. 检查用户权限设置

### Q7: 如何清理旧数据？

**A:** 脚本会自动清理 30 天前的记录。手动清理：

```bash
# 删除数据库
rm data/sent_records.db

# 删除日志
rm logs/*.log
```

## 后续扩展建议

1. **添加更多新闻源**：
   - OpenAI（需要 HTML 抓取）
   - Anthropic（需要 HTML 抓取）
   - Meta AI（需要 HTML 抓取）

2. **增强功能**：
   - 添加 Web 仪表板查看历史报告
   - 支持微信、Telegram 推送
   - 机器学习优先级评分
   - 自动摘要生成

3. **性能优化**：
   - 并发抓取多个源
   - 缓存翻译结果
   - 增量更新机制

## 技术支持

如遇问题，请检查：
1. 日志文件：`logs/ai_daily_report_*.log`
2. 环境变量配置：`.env`
3. Python 版本：`python --version`
4. 依赖安装：`pip list`

## 许可证

MIT License

---

**祝您使用愉快！每天都能收到精彩的 AI 新闻日报！** 🚀
