"""命令行接口"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from .analyzer import GrowthAnalyzer
from .config import Config, ConfigError, load_config
from .models import ScanResult
from .ranker import FolderRanker
from .reporter import Reporter
from .scanner import FileScanner
from .utils import ensure_directory

# 设置 Windows 控制台编码
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

LOGGER = logging.getLogger(__name__)


def setup_logging(config: Config) -> None:
    """设置日志

    Args:
        config: 配置对象
    """
    # 确保日志目录存在
    ensure_directory(config.logging.log_dir)

    # 日志文件路径
    log_file = config.logging.log_dir / config.logging.log_file

    # 配置日志
    logging.basicConfig(
        level=getattr(logging, config.logging.level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def run_scan(config: Config) -> ScanResult:
    """执行扫描流程

    Args:
        config: 配置对象

    Returns:
        扫描结果
    """
    LOGGER.info("开始扫描流程")

    # 1. 扫描文件
    scanner = FileScanner(config)
    file_records = scanner.scan_directories(config.scan.target_directories)

    # 2. 分析增长
    analyzer = GrowthAnalyzer(config)
    folder_growths = analyzer.analyze(file_records)

    # 2.1 分析文件类型（新增）
    file_type_stats = analyzer.analyze_file_types(file_records)

    # 2.2 查找大文件（新增）
    large_files = scanner.find_large_files(file_records)

    # 3. 排序
    ranker = FolderRanker(config)
    ranked_growths = ranker.rank(folder_growths)

    # 4. 构建扫描结果
    scan_time = datetime.now()
    time_range_start, time_range_end = analyzer.time_range

    # 计算总体统计
    total_folders_scanned = len(config.scan.target_directories)
    folders_with_growth = len([g for g in folder_growths if g.new_file_count > 0 or g.modified_file_count > 0])
    total_new_files = sum(g.new_file_count for g in folder_growths)
    total_new_size = sum(g.new_file_size for g in folder_growths)
    total_modified_files = sum(g.modified_file_count for g in folder_growths)

    scan_result = ScanResult(
        scan_time=scan_time,
        time_range_start=time_range_start,
        time_range_end=time_range_end,
        total_folders_scanned=total_folders_scanned,
        folders_with_growth=folders_with_growth,
        total_new_files=total_new_files,
        total_new_size=total_new_size,
        total_modified_files=total_modified_files,
        folder_growths=ranked_growths,
    )

    # 5. 持久化到数据库（新增）
    if config.database.enabled:
        try:
            from .storage import DatabaseManager, HistoryStorage

            db_manager = DatabaseManager(config.database.db_path)
            storage = HistoryStorage(db_manager)
            scan_id = storage.save_scan_result(scan_result, file_type_stats, large_files)
            LOGGER.info(f"扫描结果已保存到数据库，scan_id={scan_id}")

            # 清理旧记录
            deleted_count = db_manager.cleanup_old_records(config.database.retention_days)
            if deleted_count > 0:
                LOGGER.info(f"已清理 {deleted_count} 条旧记录")

            # 6. 趋势分析（新增）
            from .trend_analyzer import TrendAnalyzer
            from .activity_analyzer import ActivityAnalyzer

            trend_analyzer = TrendAnalyzer(storage)
            activity_analyzer = ActivityAnalyzer(storage)

            trends = []
            anomalies_map = {}
            heatmap_map = {}

            for folder_growth in scan_result.folder_growths:
                folder_path = folder_growth.folder_path

                trend = trend_analyzer.analyze_folder_trend(folder_path, days=7)
                if trend:
                    trends.append(trend)
                    anomalies_map[folder_path] = trend_analyzer.detect_anomalies(folder_path, days=14)
                    heatmap_map[folder_path] = activity_analyzer.render_ascii_heatmap(folder_path, days=30)

            # 输出趋势报告到控制台
            if trends:
                reporter = Reporter(config)
                reporter.generate_trend_report(trends, anomalies_map, heatmap_map)

        except Exception as e:
            LOGGER.error(f"数据库操作失败: {e}")

    LOGGER.info("扫描流程完成")
    return scan_result


def cmd_run(args: argparse.Namespace) -> int:
    """运行扫描并生成报告

    Args:
        args: 命令行参数

    Returns:
        退出码
    """
    try:
        # 加载配置
        config_path = Path(args.config) if args.config else None
        config = load_config(config_path)

        # 设置日志
        setup_logging(config)

        # 执行扫描
        scan_result = run_scan(config)

        # 生成报告
        reporter = Reporter(config)
        reporter.generate_report(scan_result)

        LOGGER.info("任务完成")
        return 0

    except ConfigError as e:
        print(f"配置错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        LOGGER.exception(f"执行失败: {e}")
        return 1


def cmd_serve(args: argparse.Namespace) -> int:
    """启动 Web 可视化界面

    Args:
        args: 命令行参数

    Returns:
        退出码
    """
    try:
        import uvicorn
        from .web.app import create_app
    except ImportError:
        print("错误: 请先安装 Web 依赖: pip install fastapi uvicorn", file=sys.stderr)
        return 1

    try:
        config_path = Path(args.config) if args.config else None
        config = load_config(config_path)
        setup_logging(config)

        app = create_app(config)
        host = args.host or "127.0.0.1"
        port = args.port or 8080

        print(f"\n启动 Web 界面: http://{host}:{port}")
        print("按 Ctrl+C 停止服务\n")
        uvicorn.run(app, host=host, port=port)
        return 0

    except ConfigError as e:
        print(f"配置错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        LOGGER.exception(f"Web 服务启动失败: {e}")
        return 1


def cmd_preview(args: argparse.Namespace) -> int:
    """预览配置

    Args:
        args: 命令行参数

    Returns:
        退出码
    """
    try:
        # 加载配置
        config_path = Path(args.config) if args.config else None
        config = load_config(config_path)

        print("\n配置预览", flush=True)
        print("=" * 60, flush=True)
        print(f"\n扫描目录 ({len(config.scan.target_directories)} 个):", flush=True)
        for directory in config.scan.target_directories:
            exists = "[OK]" if directory.exists() else "[X]"
            print(f"  {exists} {directory}", flush=True)

        print(f"\n递归扫描: {'是' if config.scan.recursive else '否'}", flush=True)
        print(f"最大深度: {config.scan.max_depth}", flush=True)

        print(f"\n忽略目录: {', '.join(config.ignore.directories)}", flush=True)
        print(f"忽略扩展名: {', '.join(config.ignore.file_extensions)}", flush=True)
        print(f"忽略隐藏文件: {'是' if config.ignore.hidden_files else '否'}", flush=True)

        print(f"\n时间模式: {config.time.mode}", flush=True)
        print(f"时区: {config.time.timezone}", flush=True)

        print(f"\n排序方式: {config.ranking.sort_by}", flush=True)
        print(f"Top N: {config.ranking.top_n}", flush=True)

        print(f"\n输出格式: {', '.join(config.output.formats)}", flush=True)
        print(f"输出目录: {config.output.output_dir}", flush=True)

        print(f"\n日志级别: {config.logging.level}", flush=True)
        print(f"日志目录: {config.logging.log_dir}", flush=True)

        print("\n" + "=" * 60 + "\n", flush=True)
        return 0

    except ConfigError as e:
        print(f"配置错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"预览失败: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """主函数

    Returns:
        退出码
    """
    parser = argparse.ArgumentParser(
        description="文件夹增长监控工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # run 命令
    run_parser = subparsers.add_parser("run", help="运行扫描并生成报告")
    run_parser.add_argument(
        "--config",
        type=str,
        help="配置文件路径（默认: config/settings.yaml）",
    )

    # preview 命令
    preview_parser = subparsers.add_parser("preview", help="预览配置")
    preview_parser.add_argument(
        "--config",
        type=str,
        help="配置文件路径（默认: config/settings.yaml）",
    )

    # serve 命令
    serve_parser = subparsers.add_parser("serve", help="启动 Web 可视化界面")
    serve_parser.add_argument(
        "--config",
        type=str,
        help="配置文件路径（默认: config/settings.yaml）",
    )
    serve_parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="监听地址（默认: 127.0.0.1）",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="监听端口（默认: 8080）",
    )

    args = parser.parse_args()

    if args.command == "run":
        return cmd_run(args)
    elif args.command == "preview":
        return cmd_preview(args)
    elif args.command == "serve":
        return cmd_serve(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
