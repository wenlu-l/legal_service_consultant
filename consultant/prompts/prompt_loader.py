"""提示词加载器。

从 prompts/jinja2 目录按名称加载 jinja2 提示词模板文件内容。
"""
from pathlib import Path


def load_prompt(name: str) -> str:
    """加载指定名称的提示词模板文本"""
    prompt_path = Path(__file__).parent / "jinja2" / f"{name}.jinja2"
    return prompt_path.read_text(encoding="utf-8")
