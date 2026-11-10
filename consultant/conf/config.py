"""应用配置。

使用 pydantic-settings 管理配置，开发环境从项目根目录的 .env 文件读取，
生产环境可通过环境变量覆盖（环境变量优先级更高）。其它模块通过
`from consultant.conf.config import settings` 获取全局单例，再以 settings.属性名 取值。
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# 项目根目录下的 .env 文件
ENV_FILE = Path(__file__).parents[2] / '.env'


class Settings(BaseSettings):
    # 大模型（DeepSeek / 千问等 OpenAI 兼容服务）
    llm_api_key: str  # 大模型 API Key
    llm_model: str  # 模型名称
    llm_base_url: str  # 大模型接口地址

    # MySQL 数据库
    database_url: str  # 数据库连接串

    # 服务器
    app_host: str  # 监听地址
    app_port: int  # 监听端口

    # 加载项目根目录下的 .env 文件
    model_config = SettingsConfigDict(env_file=ENV_FILE)


# 全局配置单例
settings = Settings()


if __name__ == '__main__':
    print(settings.database_url)
