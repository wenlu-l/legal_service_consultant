"""大模型客户端。

通过 langchain 的 init_chat_model 初始化一个 OpenAI 兼容的聊天模型实例。
DeepSeek / 千问 DashScope 等均提供 OpenAI 兼容接口，只需配置 base_url + api_key + model。
其它模块通过 `from consultant.clients.llm_client import llm` 使用该全局单例。
"""
from langchain.chat_models import init_chat_model

from consultant.conf.config import settings

# OpenAI 兼容服务，通过 base_url + api_key + model 接入
llm = init_chat_model(
    model_provider="openai",
    model=settings.llm_model,
    base_url=settings.llm_base_url,
    api_key=settings.llm_api_key,
    temperature=0.4,
)
