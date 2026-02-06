# -*- coding: utf-8 -*-
"""
HTML 转 Markdown 工具

将文章的 HTML content 转换为干净的 Markdown 格式
- 保留文本结构（标题、段落、列表、链接、粗体/斜体）
- 忽略图片、iframe、脚本等非文本元素
- 转换失败返回 None，不抛异常
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 延迟导入，避免启动时报错
_markdownify = None


def _get_markdownify():
    """延迟加载 markdownify"""
    global _markdownify
    if _markdownify is None:
        try:
            import markdownify
            _markdownify = markdownify
        except ImportError:
            logger.error("markdownify 未安装，请运行: pip install markdownify")
            raise
    return _markdownify


def html_to_markdown(html: str, strip_images: bool = True) -> Optional[str]:
    """
    将 HTML 转换为 Markdown

    Args:
        html: HTML 内容
        strip_images: 是否移除图片（默认True）

    Returns:
        Markdown 字符串，转换失败返回 None
    """
    if not html or not html.strip():
        return None

    try:
        markdownify = _get_markdownify()

        # 需要移除的标签
        strip_tags = ['script', 'style', 'iframe', 'noscript', 'svg', 'canvas']
        if strip_images:
            strip_tags.extend(['img', 'figure', 'figcaption', 'picture', 'source'])

        # 预处理：<br> 转成占位符，避免被 markdownify 吃掉空格
        BR_PLACEHOLDER = '\u200b\u200b\u200b'  # 零宽空格x3，不会被转义
        html = re.sub(r'<br\s*/?>', BR_PLACEHOLDER, html, flags=re.IGNORECASE)

        # 转换
        md = markdownify.markdownify(
            html,
            strip=strip_tags,
            heading_style='ATX',  # 使用 # 风格标题
            bullets='-',  # 使用 - 作为列表符号
            strong_em_symbol='*',  # 使用 * 作为强调符号
        )

        # 还原 <br> 为 Markdown 换行（两个空格+换行）
        md = md.replace(BR_PLACEHOLDER, '  \n')

        # 清理转换结果
        md = _clean_markdown(md)

        return md if md else None

    except Exception as e:
        logger.warning(f"HTML转Markdown失败: {e}")
        return None


def _clean_markdown(md: str) -> str:
    """
    清理 Markdown 内容

    - 移除多余空行
    - 移除行首尾空白
    - 移除空链接
    """
    if not md:
        return ""

    # 移除空链接 [](url) 或 [text]()
    md = re.sub(r'\[([^\]]*)\]\(\s*\)', r'\1', md)
    md = re.sub(r'\[\s*\]\([^\)]+\)', '', md)

    # 移除多余空行（3个以上换行变2个）
    md = re.sub(r'\n{3,}', '\n\n', md)

    # 移除行首空白，但保留行尾的两个空格（Markdown换行符）
    lines = []
    for line in md.split('\n'):
        stripped = line.lstrip()  # 只去行首空白
        # 保留行尾两个空格（Markdown换行），其他尾部空白去掉
        if stripped.endswith('  '):
            stripped = stripped.rstrip() + '  '
        else:
            stripped = stripped.rstrip()
        lines.append(stripped)
    md = '\n'.join(lines)

    # 移除首尾空白
    md = md.strip()

    return md


def batch_convert(articles: list, content_field: str = 'content') -> list:
    """
    批量转换文章内容

    Args:
        articles: 文章列表（dict列表）
        content_field: HTML内容字段名

    Returns:
        添加了 content_md 字段的文章列表
    """
    converted = 0
    failed = 0

    for article in articles:
        html_content = article.get(content_field, '')
        md = html_to_markdown(html_content)

        if md:
            article['content_md'] = md
            converted += 1
        else:
            article['content_md'] = None
            failed += 1

    logger.info(f"Markdown转换完成: 成功 {converted}, 失败 {failed}")
    return articles
