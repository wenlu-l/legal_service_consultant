"""HTTP 客户端。

维护全局异步 HTTP 客户端（httpx.AsyncClient），预留用于后续接入真实后端接口。
当前业务动作返回演示数据，尚未使用该客户端。
"""
from httpx import AsyncClient

# 全局异步 HTTP 客户端，初始值为 None
http_client: AsyncClient | None = None


def init_http_client():
    """项目启动时初始化 HTTP 客户端"""
    global http_client
    http_client = AsyncClient()


async def close_http_client():
    """项目关闭时关闭 HTTP 客户端"""
    if http_client:
        await http_client.aclose()
