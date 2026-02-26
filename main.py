#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Article Scraper - 文章爬虫主入口
支持命令行运行多个网站的爬虫

用法:
    # 列出所有可用的爬虫
    python main.py --list

    # 运行单个爬虫
    python main.py --scraper manual_jakarta --limit 10

    # 运行多个爬虫
    python main.py --scraper manual_jakarta now_jakarta --limit 5

    # 运行所有爬虫
    python main.py --all --limit 10

    # 使用代理
    python main.py --scraper flokq_blog --limit 20 --proxy

    # 写入 BigQuery
    python main.py --scraper now_jakarta --limit 10 --bq

    # 增量爬取（只爬指定日期之后的文章）
    python main.py --scraper now_jakarta --since 2025-01-01 --bq

    # 非无头模式（调试用）
    python main.py --scraper culture_trip --limit 5 --no-headless
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import List

# 确保能导入本地模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from base_scraper import Article
from scrapers import get_scraper, list_scrapers, PLAYWRIGHT_SCRAPERS
from config import STORAGE_CONFIG, SITE_CONFIGS


def setup_logging(verbose: bool = False):
    """配置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def print_scraper_list():
    """打印爬虫列表，按国家/地区分组显示"""
    scrapers = list_scrapers()

    # 按 region 分组，保持固定顺序
    region_order = [
        "indonesia", "singapore", "thailand", "malaysia",
        "philippines", "vietnam", "taiwan", "hongkong", "worldwide",
    ]
    region_labels = {
        "indonesia": "📍 Indonesia",
        "singapore": "📍 Singapore",
        "thailand": "📍 Thailand",
        "malaysia": "📍 Malaysia",
        "philippines": "📍 Philippines",
        "vietnam": "📍 Vietnam",
        "taiwan": "📍 Taiwan",
        "hongkong": "📍 Hong Kong",
        "worldwide": "🌏 Worldwide",
    }
    by_region = {}
    for s in scrapers:
        by_region.setdefault(s["region"], []).append(s)

    print("\n" + "═" * 80)
    print("  📡 可用爬虫列表 (共 {} 个)".format(len(scrapers)))
    print("═" * 80)

    for region in region_order:
        group = by_region.get(region, [])
        if not group:
            continue

        label = region_labels.get(region, region)
        print(f"\n{label} ({len(group)}个)")
        print("-" * 80)
        print(f"  {'名称':<24} {'网站':<40}")
        print("-" * 80)

        for s in group:
            name = s["name"]
            url = s["base_url"].replace("https://", "").replace("http://", "").replace("www.", "")
            if len(url) > 37:
                url = url[:34] + "..."

            print(f"  {name:<24} {url:<40}")

            if s["cities"]:
                cities_str = ", ".join(s["cities"][:6])
                if len(s["cities"]) > 6:
                    cities_str += f" +{len(s['cities']) - 6}"
                print(f"    └─ {name}:<city>  可选: {cities_str}")

    print("\n" + "═" * 80)
    print("📌 使用示例:")
    print("   python main.py -s eatbook -l 10             # 爬取，限制10篇")
    print("   python main.py -s honeycombers:singapore    # 多城市爬虫指定城市")
    print("   python main.py -s timeout:jakarta,bangkok   # 同时爬多个城市")
    print("   python main.py -s eater --since 2025-01-01  # 增量爬取")
    print("   python main.py -s renaesworld --bq          # 爬取并写入 BigQuery")
    print("═" * 80 + "\n")


def run_scraper(
        scraper_name: str,
        limit: int = 0,
        use_proxy: bool = False,
        headless: bool = True,
        since: str = None,
        exclude_urls: set = None,
) -> List[Article]:
    """运行单个爬虫"""
    logger = logging.getLogger("main")
    info_parts = [f"启动爬虫: {scraper_name}"]
    if since:
        info_parts.append(f"since={since}")
    if exclude_urls:
        info_parts.append(f"排除{len(exclude_urls)}个已爬URL")
    logger.info(" | ".join(info_parts))

    try:
        scraper_cls = get_scraper(scraper_name)

        # 根据爬虫类型传递不同参数
        if scraper_name in PLAYWRIGHT_SCRAPERS:
            scraper = scraper_cls(use_proxy=use_proxy, headless=headless)
        else:
            scraper = scraper_cls(use_proxy=use_proxy)

        articles = scraper.scrape_all(limit=limit, since=since, exclude_urls=exclude_urls)

        logger.info(f"爬虫 {scraper_name} 完成，获取 {len(articles)} 篇文章")
        return articles

    except Exception as e:
        logger.error(f"爬虫 {scraper_name} 运行失败: {e}")
        return []


def save_all_articles(articles: List[Article], output_file: str = None):
    """保存所有文章到JSON文件"""
    if not articles:
        logging.warning("没有文章可保存")
        return None

    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"articles_{timestamp}.json"

    output_dir = STORAGE_CONFIG["output_dir"]
    os.makedirs(output_dir, exist_ok=True)

    filepath = os.path.join(output_dir, output_file)

    data = [article.to_dict() for article in articles]

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logging.info(f"已保存 {len(articles)} 篇文章到: {filepath}")
    return filepath


def save_to_bigquery(articles: List[Article]) -> int:
    """
    保存文章到 BigQuery

    Args:
        articles: 文章列表

    Returns:
        写入的行数
    """
    if not articles:
        logging.warning("没有文章可写入 BigQuery")
        return 0

    logger = logging.getLogger("main")

    try:
        from utils.html_to_markdown import batch_convert
        from utils.bq_writer import BQWriter

        # 转换为字典列表
        data = [article.to_dict() for article in articles]

        # HTML 转 Markdown
        logger.info("正在转换 HTML 到 Markdown...")
        data = batch_convert(data)

        # 写入 BigQuery
        bq_config = STORAGE_CONFIG.get("bigquery", {})
        writer = BQWriter(
            project_id=bq_config.get("project_id"),
            dataset=bq_config.get("dataset"),
            table=bq_config.get("table"),
        )

        logger.info(f"正在写入 BigQuery: {writer.table_id}")
        count = writer.write(data, use_merge=True)

        return count

    except ImportError as e:
        logger.error(f"缺少依赖: {e}")
        logger.error("请运行: pip install markdownify google-cloud-bigquery")
        return 0
    except Exception as e:
        logger.error(f"写入 BigQuery 失败: {e}")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Jakarta/Indonesia 文章爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --list                          # 列出所有爬虫
  python main.py -s manual_jakarta -l 10         # 爬取 Manual Jakarta，限制10篇
  python main.py -s flokq_blog timeout_jakarta   # 爬取多个网站
  python main.py --all -l 5                      # 爬取所有网站，每个限制5篇
  python main.py -s culture_trip --no-headless   # 有界面模式运行 Playwright
        """,
    )

    parser.add_argument(
        "--list", "-L",
        action="store_true",
        help="列出所有可用的爬虫",
    )

    parser.add_argument(
        "--scraper", "-s",
        nargs="+",
        help="要运行的爬虫名称（可多个）",
    )

    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="运行所有爬虫",
    )

    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=0,
        help="每个爬虫的文章数量限制，0表示不限制（默认: 0）",
    )

    parser.add_argument(
        "--proxy", "-p",
        action="store_true",
        help="启用代理",
    )

    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Playwright 爬虫不使用无头模式（调试用）",
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出文件名（默认自动生成）",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细日志",
    )

    parser.add_argument(
        "--bq",
        action="store_true",
        help="写入 BigQuery（自动转换 HTML 到 Markdown）",
    )

    parser.add_argument(
        "--since",
        type=str,
        help="只爬取该日期之后的文章，格式: YYYY-MM-DD（仅 sitemap 爬虫有效）",
    )

    parser.add_argument(
        "--no-json",
        action="store_true",
        help="不保存 JSON 文件（配合 --bq 使用）",
    )

    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="强制重新爬取，忽略 BQ 中已存在的 URL（配合 --bq 使用）",
    )

    args = parser.parse_args()

    # 配置日志
    setup_logging(args.verbose)
    logger = logging.getLogger("main")

    # 列出爬虫
    if args.list:
        print_scraper_list()
        return

    # 确定要运行的爬虫
    scrapers_to_run = []
    if args.all:
        scrapers_to_run = [s["name"] for s in list_scrapers()]
    elif args.scraper:
        scrapers_to_run = args.scraper
    else:
        parser.print_help()
        return

    # 展开多参数格式（如 chope:jakarta,bali -> chope:jakarta, chope:bali）
    expanded_scrapers = []
    for name in scrapers_to_run:
        if ":" in name and "," in name:
            # 拆分多参数: chope:jakarta,bali -> [chope:jakarta, chope:bali]
            base_name, params = name.split(":", 1)
            for param in params.split(","):
                expanded_scrapers.append(f"{base_name}:{param.strip()}")
        else:
            expanded_scrapers.append(name)
    scrapers_to_run = expanded_scrapers

    # 验证爬虫名称（支持参数化格式如 chope:jakarta）
    available = {s["name"] for s in list_scrapers()}
    for name in scrapers_to_run:
        base_name = name.split(":")[0]  # 提取基础名称
        if base_name not in available:
            logger.error(f"未知爬虫: {name}")
            logger.info(f"可用的爬虫: {', '.join(sorted(available))}")
            return

    # 运行爬虫
    all_articles = []
    headless = not args.no_headless

    # 如果使用 BQ，预先获取 writer 用于查询已存在的 URL
    bq_writer = None
    if args.bq:
        try:
            from utils.bq_writer import BQWriter
            bq_config = STORAGE_CONFIG.get("bigquery", {})
            bq_writer = BQWriter(
                project_id=bq_config.get("project_id"),
                dataset=bq_config.get("dataset"),
                table=bq_config.get("table"),
            )
            if args.force:
                logger.info(f"BQ 强制模式：将重新爬取所有文章（覆盖已有数据）")
            else:
                logger.info(f"BQ 增量模式：将跳过已爬取的 URL")
        except Exception as e:
            logger.warning(f"初始化 BQWriter 失败，无法排除已爬取URL: {e}")

    for scraper_name in scrapers_to_run:
        logger.info(f"=" * 60)
        logger.info(f"正在运行: {scraper_name}")
        logger.info(f"=" * 60)

        # 查询该爬虫已存在的 URL（用于增量爬取），--force 时跳过
        # BQ 的 source 字段存的是 scraper.name（如 "Manual Jakarta"），从配置获取
        # 注意：参数化爬虫如 "whats_new_indonesia:bandung" 需要先提取基础名称
        exclude_urls = None
        if bq_writer and not args.force:
            try:
                base_scraper_name = scraper_name.split(":")[0]  # 提取基础名称
                source_name = SITE_CONFIGS.get(base_scraper_name, {}).get("name", scraper_name)
                exclude_urls = bq_writer.get_existing_urls(source=source_name)
                logger.info(f"从 BQ 查询到 {len(exclude_urls)} 个已爬取URL (source={source_name})")
            except Exception as e:
                logger.warning(f"查询已存在URL失败: {e}")

        articles = run_scraper(
            scraper_name,
            limit=args.limit,
            use_proxy=args.proxy,
            headless=headless,
            since=args.since,
            exclude_urls=exclude_urls,
        )

        all_articles.extend(articles)

    # 保存结果
    if all_articles:
        print(f"\n✅ 爬取完成! 共获取 {len(all_articles)} 篇文章")

        # 保存 JSON（除非指定 --no-json）
        if not args.no_json:
            filepath = save_all_articles(all_articles, args.output)
            print(f"   JSON 保存到: {filepath}")

        # 写入 BigQuery
        if args.bq:
            bq_count = save_to_bigquery(all_articles)
            if bq_count > 0:
                print(f"   BigQuery 写入: {bq_count} 条")
            else:
                print(f"   ⚠️ BigQuery 写入失败")
    else:
        print("\n❌ 没有获取到任何文章")


if __name__ == "__main__":
    main()
