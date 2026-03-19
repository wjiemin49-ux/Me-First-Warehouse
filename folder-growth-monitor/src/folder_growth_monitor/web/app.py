"""FastAPI Web 应用"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from ..config import Config, load_config
from ..storage import DatabaseManager, HistoryStorage
from ..trend_analyzer import TrendAnalyzer
from ..activity_analyzer import ActivityAnalyzer
from .api import router


def create_app(config: Config | None = None) -> FastAPI:
    """创建 FastAPI 应用实例

    Args:
        config: 配置对象，为 None 时自动从默认路径加载

    Returns:
        FastAPI 应用实例
    """
    if config is None:
        config = load_config()

    db_path = config.database.db_path

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # 启动时初始化数据库连接
        db_manager = DatabaseManager(db_path)
        storage = HistoryStorage(db_manager)
        app.state.storage = storage
        app.state.db_manager = db_manager
        app.state.config = config
        app.state.trend_analyzer = TrendAnalyzer(storage)
        app.state.activity_analyzer = ActivityAnalyzer(storage)
        yield
        # 关闭时无需特殊清理（SQLite 连接按需创建）

    app = FastAPI(
        title="Folder Growth Monitor",
        description="文件夹增长监控 Web 界面",
        version="2.0.0",
        lifespan=lifespan,
    )

    app.include_router(router, prefix="/api")

    # 前端页面路由
    templates_dir = Path(__file__).parent / "templates"

    @app.get("/", response_class=HTMLResponse)
    async def index():
        html_path = templates_dir / "index.html"
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))

    return app
