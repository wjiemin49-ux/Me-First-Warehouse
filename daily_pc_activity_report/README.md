# 每日电脑活动简报

> 自动生成每日电脑活动简报的 Python 工具

## 📋 项目简介

这是一个运行在 Windows 本地的 Python 自动化脚本，通过扫描文件系统的变化，自动生成每日电脑活动简报，帮助您回顾每天在电脑上做了什么。

**核心特点：**
- ✅ 轻量稳定，无重型依赖
- ✅ 基于文件系统活动分析
- ✅ 生成易读的 Markdown 报告
- ✅ 支持手动运行和定时任务
- ✅ 完全本地运行，保护隐私

## 🎯 功能列表

### 第一版功能（当前版本 v1.0.0）

本版本专注于**文件系统活动分析**，确保稳定可靠：

1. **文件活动统计**
   - 今日新增文件数量
   - 今日修改文件数量
   - 文件大小统计

2. **目录活动分析**
   - 最活跃目录排行
   - 按类别统计（下载、截图、项目、学习等）
   - 目录活动分数计算

3. **文件类型分布**
   - 按扩展名统计文件数量
   - 识别主要文件类型

4. **智能总结**
   - 基于规则生成今日活动总结
   - 判断主要活动类型（开发、学习、信息收集等）

5. **多种输出格式**
   - Markdown 格式（主要）
   - 纯文本格式
   - 控制台输出

6. **灵活配置**
   - YAML 配置文件
   - 自定义扫描目录
   - 排除模式配置
   - 递归深度控制

## 📦 安装步骤

### 1. 环境要求

- Windows 10/11
- Python 3.10 或更高版本

### 2. 克隆或下载项目

```bash
cd d:\me\脚本
# 项目已在此目录：daily_pc_activity_report
```

### 3. 安装依赖

```bash
cd daily_pc_activity_report
pip install -r requirements.txt
```

依赖非常少，只需要：
- PyYAML（用于配置文件解析）

## ⚙️ 配置方法

### 1. 编辑配置文件

配置文件位于 `config/settings.yaml`，已包含默认配置。

**重要配置项：**

```yaml
scan_directories:
  downloads:
    path: "C:\\Users\\{username}\\Downloads"
    recursive: false

  screenshots:
    path: "C:\\Users\\{username}\\Pictures\\Screenshots"
    recursive: false

  projects:
    path: "D:\\projects"  # 修改为您的项目目录
    recursive: true
    max_depth: 3
```

**配置说明：**
- `{username}` 会自动替换为当前用户名
- `recursive: true` 表示递归扫描子目录
- `max_depth` 限制递归深度，避免扫描过深

### 2. 自定义扫描目录

根据您的实际情况添加或修改扫描目录：

```yaml
scan_directories:
  my_notes:
    path: "D:\\notes"
    recursive: true
    max_depth: 2

  my_downloads:
    path: "E:\\Downloads"
    recursive: false
```

### 3. 配置排除模式

避免扫描不必要的文件和目录：

```yaml
exclude_patterns:
  directories:
    - ".git"
    - "node_modules"
    - "__pycache__"
  files:
    - "*.tmp"
    - "*.log"
    - "*.cache"
```

## 🚀 使用方法

### 手动运行

#### 方式 1：使用 Python 模块（推荐）

```bash
cd daily_pc_activity_report
python -m daily_pc_activity_report
```

#### 方式 2：使用入口脚本

```bash
cd daily_pc_activity_report
python main.py
```

### 命令行选项

```bash
# 生成今天的报告
python -m daily_pc_activity_report

# 生成指定日期的报告
python -m daily_pc_activity_report --date 2026-03-17

# 使用自定义配置文件
python -m daily_pc_activity_report --config custom.yaml

# 生成文本格式报告
python -m daily_pc_activity_report --format text

# 仅在控制台显示
python -m daily_pc_activity_report --format console

# 启用详细日志
python -m daily_pc_activity_report --verbose

# 查看帮助
python -m daily_pc_activity_report --help
```

## 📊 输出示例

### Markdown 报告示例

报告会生成在 `output/daily_report_2026-03-18.md`：

```markdown
# 每日电脑活动简报

**日期：** 2026年03月18日

## 📊 今日总览

- **新增文件：** 45 个
- **修改文件：** 23 个
- **总文件数：** 68 个
- **总大小：** 125.3 MB

## 💡 今日总结

今天主要在进行项目开发，编写了不少 Python 代码。今天创建了 45 个新文件，活动量适中，修改了 23 个文件。

## 🔥 活跃目录排行

### 1. D:\projects\my_project
- **类别：** projects
- **新增：** 15 个文件
- **修改：** 8 个文件
- **大小：** 45.2 MB
- **活动分数：** 38

...
```

### 控制台输出示例

```
============================================================
                    每日电脑活动简报
============================================================

日期: 2026年03月18日

------------------------------------------------------------
今日总览
------------------------------------------------------------
新增文件: 45 个
修改文件: 23 个
总文件数: 68 个
总大小: 125.3 MB

------------------------------------------------------------
今日总结
------------------------------------------------------------
今天主要在进行项目开发，编写了不少 Python 代码。
```

## ⏰ Windows 任务计划程序设置

### 自动安装（推荐）

1. 以**管理员身份**运行 PowerShell
2. 执行安装脚本：

```powershell
cd d:\me\脚本\daily_pc_activity_report\scripts
.\install_task.ps1
```

3. 脚本会自动创建每天 23:00 运行的任务
4. 可以选择立即测试运行

### 手动设置

1. 按 `Win + R`，输入 `taskschd.msc`，打开任务计划程序
2. 点击"创建基本任务"
3. 填写任务信息：
   - **名称：** DailyPCActivityReport
   - **描述：** 每日电脑活动简报自动生成

4. 触发器设置：
   - **触发器：** 每天
   - **时间：** 23:00（或您希望的时间）

5. 操作设置：
   - **操作：** 启动程序
   - **程序/脚本：** `python`
   - **参数：** `-m daily_pc_activity_report`
   - **起始于：** `d:\me\脚本\daily_pc_activity_report`

6. 完成创建

### 验证任务

- 在任务计划程序中找到任务
- 右键点击，选择"运行"
- 检查 `logs/` 目录中的日志文件
- 检查 `output/` 目录中的报告文件

## 📁 项目结构

```
daily_pc_activity_report/
├── config/
│   ├── settings.yaml              # 主配置文件
│   └── settings.example.yaml      # 配置示例
├── src/daily_pc_activity_report/
│   ├── __init__.py                # 包初始化
│   ├── __main__.py                # CLI 入口
│   ├── config.py                  # 配置加载
│   ├── models.py                  # 数据模型
│   ├── scanner.py                 # 文件系统扫描
│   ├── analyzer.py                # 活动分析
│   ├── reporter.py                # 报告生成
│   └── utils.py                   # 工具函数
├── scripts/
│   ├── install_task.ps1           # 任务计划程序安装脚本
│   └── run_report.bat             # 批处理运行脚本
├── output/                        # 生成的报告
├── logs/                          # 日志文件
├── main.py                        # 入口脚本
├── requirements.txt               # 依赖列表
├── pyproject.toml                 # 项目配置
├── .gitignore                     # Git 忽略文件
└── README.md                      # 本文档
```

## 🔧 常见问题

### 1. 报告显示"未找到任何文件活动"

**原因：**
- 配置的目录路径不正确
- 今天确实没有文件活动
- 目录权限问题

**解决方法：**
- 检查 `config/settings.yaml` 中的路径是否正确
- 使用 `--verbose` 查看详细日志
- 确保有权限访问配置的目录

### 2. 任务计划程序执行失败

**原因：**
- Python 未添加到系统 PATH
- 工作目录设置不正确
- 权限不足

**解决方法：**
- 确保 Python 在系统 PATH 中
- 检查任务的"起始于"路径是否正确
- 查看 `logs/task_scheduler.log` 了解错误信息

### 3. 扫描速度很慢

**原因：**
- 扫描目录文件太多
- 递归深度太深
- 网络驱动器响应慢

**解决方法：**
- 减少 `max_depth` 限制递归深度
- 添加更多排除模式
- 避免扫描网络驱动器

### 4. 中文乱码问题

**原因：**
- 控制台编码设置问题

**解决方法：**
```bash
# 在运行前设置控制台编码
chcp 65001
python -m daily_pc_activity_report
```

### 5. 配置文件找不到

**原因：**
- 工作目录不正确

**解决方法：**
```bash
# 确保在项目根目录运行
cd d:\me\脚本\daily_pc_activity_report
python -m daily_pc_activity_report
```

## 🚀 未来增强计划

### 第二阶段功能（计划中）

1. **浏览器历史分析**
   - Chrome/Edge 浏览历史
   - 访问网站统计
   - 搜索关键词分析

2. **应用程序使用跟踪**
   - 通过 Windows 事件日志
   - 应用使用时长统计
   - 最常用应用排行

3. **Git 活动统计**
   - 提交次数统计
   - 代码行数变化
   - 活跃仓库排行

4. **LLM 驱动的总结**
   - 接入 OpenAI/Claude API
   - 生成更智能的总结
   - 个性化建议

5. **趋势分析**
   - 与前几天对比
   - 活动趋势图表
   - 周报、月报生成

6. **Web 仪表板**
   - 可视化报告查看
   - 历史报告浏览
   - 交互式图表

## 🔌 扩展开发

### 添加新的数据源

1. 在 `src/daily_pc_activity_report/` 创建新的扫描器模块
2. 实现扫描逻辑，返回 `FileActivity` 列表
3. 在 `scanner.py` 中集成新扫描器
4. 更新配置文件支持新数据源

### 自定义报告格式

1. 在 `reporter.py` 中添加新的生成函数
2. 实现自定义格式逻辑
3. 在 CLI 中添加新格式选项

### 自定义分析规则

1. 修改 `analyzer.py` 中的 `generate_summary()` 函数
2. 添加新的规则判断逻辑
3. 根据您的使用习惯定制总结

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题或建议，请通过 Issue 反馈。

---

**祝您使用愉快！** 🎉
