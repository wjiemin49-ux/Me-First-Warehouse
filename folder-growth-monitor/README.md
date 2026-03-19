# Folder Growth Monitor

文件夹增长监控工具 - 自动检测哪个文件夹今天增长最快

## 项目简介

这是一个运行在 Windows 本地的 Python 自动化脚本，用于监控指定目录的文件增长情况。它可以：

- 自动扫描指定的文件夹列表
- 统计"今天"每个文件夹的新增文件数量、新增文件体积、修改文件数量
- 按增长程度排序，生成清晰的报告
- 支持通过 Windows 任务计划程序定时执行
- 未来可扩展为更大的"电脑活动观察系统"

## 功能列表

- ✅ 扫描指定目录列表
- ✅ 统计今日新增文件数量和体积
- ✅ 统计今日修改文件数量
- ✅ 多种排序方式（新增文件数、新增体积、修改文件数、综合评分）
- ✅ 综合评分算法（可配置权重）
- ✅ 控制台输出
- ✅ Markdown 报告生成
- ✅ 灵活的忽略规则（目录、扩展名、隐藏文件）
- ✅ 完善的日志记录
- ✅ 异常处理（单个目录失败不影响整体）
- ✅ YAML 配置文件
- ✅ 环境变量支持

## 项目结构

```
folder-growth-monitor/
├── src/
│   └── folder_growth_monitor/
│       ├── __init__.py          # 包初始化
│       ├── __main__.py          # 入口点
│       ├── cli.py               # 命令行接口
│       ├── config.py            # 配置加载与验证
│       ├── models.py            # 数据模型
│       ├── scanner.py           # 文件扫描器
│       ├── analyzer.py          # 增长分析器
│       ├── ranker.py            # 排序逻辑
│       ├── reporter.py          # 报告生成器
│       └── utils.py             # 工具函数
├── config/
│   └── settings.yaml            # 主配置文件
├── output/                      # 报告输出目录（自动创建）
├── logs/                        # 日志目录（自动创建）
├── .env.example                 # 环境变量示例
├── pyproject.toml               # 项目配置
├── requirements.txt             # 依赖列表
└── README.md                    # 本文档
```

## 安装步骤

### 1. 环境要求

- Windows 10/11
- Python 3.11 或更高版本

### 2. 克隆或下载项目

将项目放置到你的本地目录，例如：`D:\me\脚本\folder-growth-monitor`

### 3. 安装依赖

打开命令行，进入项目目录：

```bash
cd D:\me\脚本\folder-growth-monitor
pip install -r requirements.txt
```

或者使用开发模式安装（推荐）：

```bash
pip install -e .
```

## 配置方法

### 1. 编辑配置文件

打开 `config/settings.yaml`，修改以下关键配置：

```yaml
scan:
  target_directories:
    - "D:\\Projects"      # 修改为你要监控的目录
    - "D:\\Downloads"
    - "D:\\Study"
```

**重要提示：** Windows 路径需要使用双反斜杠 `\\` 或单正斜杠 `/`

### 2. 配置忽略规则

根据需要调整忽略规则：

```yaml
ignore:
  directories:
    - ".git"
    - "node_modules"
    - "__pycache__"
  file_extensions:
    - ".tmp"
    - ".log"
  hidden_files: true
```

### 3. 配置排序方式

选择排序方式：

```yaml
ranking:
  sort_by: "composite"  # 可选: new_file_count | new_file_size | modified_file_count | composite
  top_n: 10             # 显示前 10 个文件夹
```

如果使用综合评分，可以调整权重：

```yaml
ranking:
  composite_weights:
    new_file_count: 0.5       # 新增文件数权重
    new_file_size: 0.3        # 新增文件体积权重
    modified_file_count: 0.2  # 修改文件数权重
```

### 4. 配置输出格式

```yaml
output:
  formats:
    - "console"    # 控制台输出
    - "markdown"   # Markdown 文件
  output_dir: "./output"
```

## 手动运行方法

### 运行扫描

```bash
cd D:\me\脚本\folder-growth-monitor
python -m folder_growth_monitor run
```

### 预览配置

在实际运行前，可以先预览配置是否正确：

```bash
python -m folder_growth_monitor preview
```

这会显示：
- 扫描目录列表（标记哪些存在、哪些不存在）
- 忽略规则
- 排序方式
- 输出配置

### 使用自定义配置文件

```bash
python -m folder_growth_monitor run --config path/to/custom_settings.yaml
```

## 输出结果说明

### 控制台输出

运行后会在控制台显示：

```
================================================================================
                              文件夹增长报告
================================================================================

生成时间: 2026-03-18 21:30:00
统计范围: 2026-03-18 00:00:00 至 2026-03-18 21:30:00

--------------------------------------------------------------------------------
                                总体统计
--------------------------------------------------------------------------------
扫描目录数: 3
有增长的目录: 2
总新增文件数: 45
总新增体积: 1.23 GB
总修改文件数: 12

--------------------------------------------------------------------------------
                          增长排行榜 (Top 10)
--------------------------------------------------------------------------------

1. Projects
   路径: D:\Projects
   新增文件: 38 个
   新增体积: 1.10 GB
   修改文件: 10 个
   最后活跃: 2026-03-18 20:15:32
   综合评分: 8.75

2. Downloads
   路径: D:\Downloads
   新增文件: 7 个
   新增体积: 135.50 MB
   修改文件: 2 个
   最后活跃: 2026-03-18 18:42:10
   综合评分: 3.21
```

### Markdown 报告

报告会保存到 `output/folder_growth_YYYY-MM-DD.md`，包含：

- 总体统计
- 排行榜表格
- 每个文件夹的详细信息

### 日志文件

日志保存在 `logs/folder_monitor.log`，包含：

- 扫描过程详细信息
- 警告和错误信息
- 调试信息（如果启用 DEBUG 级别）

## Windows 任务计划程序设置

### 方法一：通过图形界面

1. **打开任务计划程序**
   - 按 `Win + R`，输入 `taskschd.msc`，回车

2. **创建基本任务**
   - 点击右侧"创建基本任务"
   - 名称：`文件夹增长监控`
   - 描述：`每天自动扫描文件夹增长情况`

3. **设置触发器**
   - 选择"每天"
   - 开始时间：例如 `23:00:00`（每天晚上 11 点）
   - 每隔：`1` 天

4. **设置操作**
   - 选择"启动程序"
   - 程序或脚本：`C:\Python311\python.exe`（根据你的 Python 安装路径调整）
   - 添加参数：`-m folder_growth_monitor run`
   - 起始于：`D:\me\脚本\folder-growth-monitor`

5. **完成设置**
   - 勾选"当单击'完成'时，打开此任务属性的对话框"
   - 点击"完成"

6. **高级设置（可选）**
   - 在属性对话框中：
     - "条件"选项卡：取消勾选"只有在计算机使用交流电源时才启动此任务"（如果是笔记本）
     - "设置"选项卡：勾选"如果任务失败，重新启动"，间隔 `10 分钟`

### 方法二：通过命令行

创建一个 `create_task.bat` 文件：

```batch
@echo off
schtasks /create /tn "文件夹增长监控" /tr "C:\Python311\python.exe -m folder_growth_monitor run" /sc daily /st 23:00 /sd %date:~0,10% /f
echo 任务创建完成
pause
```

右键以管理员身份运行此批处理文件。

### 验证任务

1. 在任务计划程序中找到"文件夹增长监控"任务
2. 右键点击，选择"运行"
3. 检查 `logs/folder_monitor.log` 确认执行成功
4. 检查 `output/` 目录是否生成了报告

### 查看任务历史

1. 在任务计划程序中选择任务
2. 点击下方"历史记录"选项卡
3. 查看任务执行记录和结果

## 时间判断说明

### Windows 文件时间戳

Windows 文件系统（NTFS）提供三个时间戳：

- **创建时间 (st_ctime)** - 文件首次创建的时间
- **修改时间 (st_mtime)** - 文件内容最后修改的时间
- **访问时间 (st_atime)** - 文件最后被访问的时间（可能被禁用）

### 本工具的时间判断策略

**新增文件判断：**
- 使用 `st_ctime`（创建时间）
- 如果创建时间在"今天 00:00:00 到当前时间"范围内，则认为是今天新增

**修改文件判断：**
- 使用 `st_mtime`（修改时间）
- 如果修改时间在"今天 00:00:00 到当前时间"范围内，且不是今天新增的文件，则认为是今天修改

**注意事项：**
- 文件复制操作会更新创建时间（被识别为新增）
- 文件移动操作可能保留原创建时间（取决于是否跨分区）
- FAT32 文件系统的时间精度较低（2 秒），NTFS 精度更高（100 纳秒）

### 时间模式

配置文件支持两种时间模式：

1. **today 模式（默认）**
   - 统计范围：本地时间今天 00:00:00 到当前时间
   - 适合每天固定时间运行

2. **last_24h 模式**
   - 统计范围：当前时间往前推 24 小时
   - 适合不定时运行

## 常见问题

### Q1: 某些目录扫描失败怎么办？

**A:** 脚本会自动跳过失败的目录并记录警告日志。常见原因：
- 目录不存在
- 权限不足
- 路径包含特殊字符

检查 `logs/folder_monitor.log` 查看详细错误信息。

### Q2: 如何排除某些不想监控的目录？

**A:** 在 `config/settings.yaml` 中配置忽略规则：

```yaml
ignore:
  directories:
    - "node_modules"
    - ".git"
    - "你要排除的目录名"
```

### Q3: 扫描速度慢怎么办？

**A:** 优化建议：
1. 减少扫描目录数量
2. 设置 `recursive: false`（不递归扫描）
3. 增加更多忽略规则
4. 避免扫描网络驱动器

### Q4: 如何只监控特定类型的文件？

**A:** 当前版本通过忽略规则排除不需要的文件。未来版本可以添加"仅包含"规则。

### Q5: 报告中的"综合评分"是如何计算的？

**A:** 综合评分使用 Min-Max 归一化 + 加权求和：

1. 对所有文件夹的各项指标进行归一化（0-1）
2. 按配置的权重加权求和
3. 缩放到 0-10 分

默认权重：
- 新增文件数：50%
- 新增文件体积：30%
- 修改文件数：20%

### Q6: 如何修改日志级别？

**A:** 两种方式：

1. 修改 `config/settings.yaml`：
```yaml
logging:
  level: "DEBUG"  # DEBUG | INFO | WARNING | ERROR
```

2. 设置环境变量：
```bash
set LOG_LEVEL=DEBUG
python -m folder_growth_monitor run
```

### Q7: Windows 任务计划程序中任务执行失败？

**A:** 排查步骤：

1. **检查 Python 路径**
   - 在命令行运行 `where python` 确认路径
   - 任务中使用完整路径，如 `C:\Python311\python.exe`

2. **检查工作目录**
   - 确保"起始于"设置为项目根目录
   - 例如：`D:\me\脚本\folder-growth-monitor`

3. **检查权限**
   - 任务属性 → "常规"选项卡
   - 选择"不管用户是否登录都要运行"
   - 勾选"使用最高权限运行"

4. **查看日志**
   - 检查 `logs/folder_monitor.log`
   - 检查任务计划程序的历史记录

### Q8: 如何测试配置是否正确？

**A:** 使用 preview 命令：

```bash
python -m folder_growth_monitor preview
```

这会显示所有配置项，并标记哪些目录存在、哪些不存在。

## 后续扩展建议

### 1. 存储历史数据

使用 SQLite 数据库记录每日扫描结果：

```python
# 新增 storage.py 模块
class HistoryStorage:
    def save_scan_result(self, scan_result: ScanResult):
        # 保存到数据库

    def get_trend(self, folder_path: Path, days: int):
        # 获取趋势数据
```

### 2. 趋势分析

基于历史数据生成趋势图表：
- 最近 7 天增长趋势
- 最近 30 天增长趋势
- 同比、环比分析

### 3. 邮件通知

每日自动发送报告到邮箱：

```python
# 新增 notifier.py 模块
class EmailNotifier:
    def send_report(self, scan_result: ScanResult):
        # 发送邮件
```

### 4. Web 界面

使用 Flask 或 FastAPI 提供可视化界面：
- 实时查看扫描结果
- 历史数据查询
- 趋势图表展示
- 配置管理界面

### 5. 更多统计维度

- 文件类型分布（按扩展名统计）
- 大文件 Top 10
- 活跃时段分析（按小时统计）
- 文件夹深度分析

### 6. 智能过滤

- 基于文件大小的智能忽略（例如忽略小于 1KB 的文件）
- 基于文件类型的分类统计
- 自动识别临时文件和缓存文件

### 7. 性能优化

- 并发扫描多个目录
- 增量扫描（仅扫描变化的目录）
- 缓存机制（缓存文件元数据）
- 进度条显示

### 8. 多平台支持

- 支持 Linux 和 macOS
- 适配不同文件系统的时间戳特性

## 使用示例

### 示例 1：监控项目目录

```yaml
scan:
  target_directories:
    - "D:\\Projects\\ProjectA"
    - "D:\\Projects\\ProjectB"
    - "D:\\Projects\\ProjectC"
  recursive: false
```

运行后会显示哪个项目今天最活跃。

### 示例 2：监控下载目录

```yaml
scan:
  target_directories:
    - "D:\\Downloads"
  recursive: false

ranking:
  sort_by: "new_file_size"  # 按新增体积排序
```

查看今天下载了多少文件和总大小。

### 示例 3：监控学习资料

```yaml
scan:
  target_directories:
    - "D:\\Study\\课程A"
    - "D:\\Study\\课程B"
    - "D:\\Study\\笔记"
  recursive: false

ranking:
  sort_by: "modified_file_count"  # 按修改文件数排序
```

查看今天在哪个课程上花的时间最多。

## 故障排查

### 问题：配置文件加载失败

**错误信息：** `配置文件不存在: config/settings.yaml`

**解决方法：**
1. 确认当前工作目录是项目根目录
2. 确认 `config/settings.yaml` 文件存在
3. 使用 `--config` 参数指定完整路径

### 问题：目录扫描失败

**错误信息：** `权限不足，无法访问目录`

**解决方法：**
1. 以管理员身份运行
2. 检查目录权限设置
3. 从扫描列表中移除无权限的目录

### 问题：报告生成失败

**错误信息：** `无法创建输出目录`

**解决方法：**
1. 确认输出目录路径正确
2. 确认有写入权限
3. 手动创建 `output` 目录

### 问题：Python 模块找不到

**错误信息：** `No module named 'folder_growth_monitor'`

**解决方法：**
1. 确认已安装依赖：`pip install -r requirements.txt`
2. 或使用开发模式安装：`pip install -e .`
3. 确认当前工作目录正确

## 技术细节

### 综合评分算法

```python
# 1. 归一化（Min-Max Normalization）
norm_value = (value - min_value) / (max_value - min_value)

# 2. 加权求和
score = (
    0.5 * norm(new_file_count) +
    0.3 * norm(new_file_size) +
    0.2 * norm(modified_file_count)
)

# 3. 缩放到 0-10 分
final_score = score * 10
```

### 扫描逻辑

```python
# 非递归模式
for item in directory.glob("*"):
    if item.is_file():
        process_file(item)

# 递归模式
for item in directory.glob("**/*"):
    if item.is_file():
        process_file(item)
```

### 忽略规则优先级

1. 隐藏文件检查（文件名以 `.` 开头）
2. 目录名检查（路径中包含忽略的目录名）
3. 扩展名检查（文件扩展名在忽略列表中）

## 许可证

MIT License

## 作者

Created with Claude Code

## 更新日志

### v1.0.0 (2026-03-18)

- ✅ 初始版本发布
- ✅ 支持扫描指定目录
- ✅ 统计新增和修改文件
- ✅ 多种排序方式
- ✅ 控制台和 Markdown 输出
- ✅ 完善的配置和日志系统
