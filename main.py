"""FastAPI 应用入口。

启动流程：
1. lifespan 生命周期中初始化 http 客户端、对话引擎、数据库引擎并建表；
2. 创建 FastAPI 实例并注册聊天路由；
3. main 函数通过 uvicorn 启动服务。
"""
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from consultant.clients.database import init_db_engine, close_db_engine, create_tables
from consultant.clients.http_client import init_http_client, close_http_client
from consultant.conf.config import settings
from consultant.web.chat_router import chat_router
from consultant.web.dependencies import init_dialogue_engine


# 1. FastAPI 生命周期
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动初始化
    init_http_client()
    init_dialogue_engine()
    init_db_engine()
    await create_tables()
    logger.info("项目启动初始化：http 客户端、对话引擎、数据库会话工厂")
    yield
    # 关闭清理
    await close_db_engine()
    await close_http_client()
    logger.info("项目关闭，执行清理资源")


# 2. 创建 FastAPI 实例
app = FastAPI(lifespan=lifespan)

# 3. 注册路由
app.include_router(chat_router)

# 4. 挂载静态聊天页面（访问 / 即可打开演示前端）
_STATIC_DIR = Path(__file__).parent / "static"
if _STATIC_DIR.exists():
    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(_STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


def main():
    """启动 uvicorn 服务"""
    uvicorn.run("main:app", host=settings.app_host, port=settings.app_port, reload=True)


if __name__ == "__main__":
    main()
