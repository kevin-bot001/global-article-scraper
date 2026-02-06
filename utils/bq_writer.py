# -*- coding: utf-8 -*-
"""
BigQuery 写入模块

- 使用 Application Default Credentials (gcloud auth login)
- 批量写入（load job），按 body 大小分批
- MERGE 策略：url + source 去重，存在则覆盖
"""
import json
import logging
import tempfile
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# 延迟导入
_bigquery = None
_bq_client = None

# 单批次最大字节数（8MB，留点余量）
MAX_BATCH_BYTES = 8 * 1024 * 1024


def _get_client():
    """获取 BigQuery 客户端（延迟加载）"""
    global _bigquery, _bq_client
    if _bigquery is None:
        try:
            from google.cloud import bigquery
            _bigquery = bigquery
        except ImportError:
            logger.error("google-cloud-bigquery 未安装，请运行: pip install google-cloud-bigquery")
            raise

    if _bq_client is None:
        # 使用 Application Default Credentials
        _bq_client = _bigquery.Client()
        logger.info(f"BigQuery 客户端初始化成功，项目: {_bq_client.project}")

    return _bq_client, _bigquery


class BQWriter:
    """BigQuery 写入器"""

    def __init__(
        self,
        project_id: str = 'oppo-gcp-prod-digfood-129869',
        dataset: str = "maomao_poi_external_data",
        table: str = "global_articles"
    ):
        """
        初始化写入器

        Args:
            project_id: GCP 项目ID（None则使用默认）
            dataset: 数据集名称
            table: 表名称
        """
        self.client, self.bq = _get_client()
        self.project_id = project_id
        self.dataset = dataset
        self.table = table
        self.table_id = f"{self.project_id}.{self.dataset}.{self.table}"
        self.staging_table_id = f"{self.table_id}_staging"

    def _get_schema(self):
        """获取表 schema"""
        return [
            self.bq.SchemaField("url", "STRING", mode="REQUIRED"),
            self.bq.SchemaField("source", "STRING", mode="REQUIRED"),
            self.bq.SchemaField("country", "STRING"),
            self.bq.SchemaField("city", "STRING"),
            self.bq.SchemaField("title", "STRING"),
            self.bq.SchemaField("content", "STRING"),
            self.bq.SchemaField("raw_html", "STRING"),  # 原始 HTML
            self.bq.SchemaField("content_md", "STRING"),
            self.bq.SchemaField("author", "STRING"),
            self.bq.SchemaField("publish_date", "DATE"),
            self.bq.SchemaField("category", "STRING"),
            self.bq.SchemaField("tags", "STRING", mode="REPEATED"),
            self.bq.SchemaField("images", "STRING", mode="REPEATED"),
            self.bq.SchemaField("language", "STRING"),
            self.bq.SchemaField("create_time", "TIMESTAMP"),
        ]

    def ensure_table_exists(self):
        """确保表存在，不存在则创建"""
        # 确保 dataset 存在
        dataset_ref = self.bq.Dataset(f"{self.project_id}.{self.dataset}")
        try:
            self.client.get_dataset(dataset_ref)
        except Exception:
            logger.info(f"创建 dataset: {self.dataset}")
            self.client.create_dataset(dataset_ref)

        # 确保表存在
        table_ref = self.bq.Table(self.table_id, schema=self._get_schema())
        try:
            self.client.get_table(self.table_id)
            logger.info(f"表已存在: {self.table_id}")
        except Exception:
            logger.info(f"创建表: {self.table_id}")
            # 按 publish_date 分区，按 source, country 聚簇
            table_ref.time_partitioning = self.bq.TimePartitioning(
                type_=self.bq.TimePartitioningType.DAY,
                field="publish_date"
            )
            table_ref.clustering_fields = ["source", "country"]
            self.client.create_table(table_ref)

    def _prepare_row(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """准备单行数据，转换格式"""
        now = datetime.utcnow().isoformat()

        # 处理 publish_date：转换为 YYYY-MM-DD 格式
        publish_date = article.get("publish_date", "")
        if publish_date:
            try:
                if "T" in publish_date:
                    publish_date = publish_date.split("T")[0]
                elif len(publish_date) > 10:
                    publish_date = publish_date[:10]
            except Exception:
                publish_date = None
        else:
            publish_date = None

        return {
            "url": article.get("url", ""),
            "source": article.get("source", ""),
            "country": article.get("country", ""),
            "city": article.get("city", ""),
            "title": article.get("title", ""),
            "content": article.get("content", ""),
            "raw_html": article.get("raw_html", ""),
            "content_md": article.get("content_md"),
            "author": article.get("author", ""),
            "publish_date": publish_date,
            "category": article.get("category", ""),
            "tags": article.get("tags", []) or [],
            "images": article.get("images", []) or [],
            "language": article.get("language", ""),
            "create_time": now,
        }

    def _split_batches(self, articles: List[Dict]) -> List[List[Dict]]:
        """按大小分批"""
        batches = []
        current_batch = []
        current_size = 0

        for article in articles:
            row = self._prepare_row(article)
            row_json = json.dumps(row, ensure_ascii=False)
            row_size = len(row_json.encode('utf-8'))

            # 当前批次加上这条会超限，先保存当前批次
            if current_size + row_size > MAX_BATCH_BYTES and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_size = 0

            current_batch.append(row)
            current_size += row_size

        # 最后一批
        if current_batch:
            batches.append(current_batch)

        return batches

    def write(self, articles: List[Dict], use_merge: bool = True) -> int:
        """
        写入文章到 BigQuery

        Args:
            articles: 文章列表
            use_merge: 是否使用 MERGE（去重覆盖），False则直接追加

        Returns:
            写入的行数
        """
        if not articles:
            logger.warning("没有文章需要写入")
            return 0

        self.ensure_table_exists()

        # 分批
        batches = self._split_batches(articles)
        logger.info(f"共 {len(articles)} 条数据，分为 {len(batches)} 批写入")

        total_written = 0

        for i, batch in enumerate(batches):
            logger.info(f"写入第 {i + 1}/{len(batches)} 批，{len(batch)} 条...")

            if use_merge:
                written = self._write_batch_merge(batch)
            else:
                written = self._write_batch_append(batch)

            total_written += written

        logger.info(f"BigQuery 写入完成，共 {total_written} 条")
        return total_written

    def _write_batch_append(self, rows: List[Dict]) -> int:
        """直接追加写入"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
            temp_file = f.name

        try:
            job_config = self.bq.LoadJobConfig(
                source_format=self.bq.SourceFormat.NEWLINE_DELIMITED_JSON,
                write_disposition=self.bq.WriteDisposition.WRITE_APPEND,
            )

            with open(temp_file, 'rb') as f:
                job = self.client.load_table_from_file(f, self.table_id, job_config=job_config)

            job.result()
            return len(rows)

        finally:
            os.unlink(temp_file)

    def _write_batch_merge(self, rows: List[Dict]) -> int:
        """MERGE 写入（url + source 去重，存在则更新）"""
        # 创建/清空 staging 表
        staging_table = self.bq.Table(self.staging_table_id, schema=self._get_schema())
        try:
            self.client.delete_table(self.staging_table_id, not_found_ok=True)
        except Exception:
            pass
        self.client.create_table(staging_table)

        # 写入 staging
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
            temp_file = f.name

        try:
            job_config = self.bq.LoadJobConfig(
                source_format=self.bq.SourceFormat.NEWLINE_DELIMITED_JSON,
                write_disposition=self.bq.WriteDisposition.WRITE_TRUNCATE,
            )

            with open(temp_file, 'rb') as f:
                job = self.client.load_table_from_file(f, self.staging_table_id, job_config=job_config)
            job.result()

        finally:
            os.unlink(temp_file)

        # MERGE 到目标表
        merge_sql = f"""
        MERGE `{self.table_id}` T
        USING `{self.staging_table_id}` S
        ON T.url = S.url AND T.source = S.source
        WHEN MATCHED THEN
            UPDATE SET
                country = S.country,
                city = S.city,
                title = S.title,
                content = S.content,
                raw_html = S.raw_html,
                content_md = S.content_md,
                author = S.author,
                publish_date = S.publish_date,
                category = S.category,
                tags = S.tags,
                images = S.images,
                language = S.language,
                create_time = S.create_time
        WHEN NOT MATCHED THEN
            INSERT (url, source, country, city, title, content, raw_html, content_md, author, publish_date, category, tags, images, language, create_time)
            VALUES (S.url, S.source, S.country, S.city, S.title, S.content, S.raw_html, S.content_md, S.author, S.publish_date, S.category, S.tags, S.images, S.language, S.create_time)
        """

        job = self.client.query(merge_sql)
        job.result()

        # 清理 staging 表
        self.client.delete_table(self.staging_table_id, not_found_ok=True)

        return len(rows)

    def get_existing_urls(self, source: str = None) -> set:
        """
        获取已存在的 URL 集合（用于增量爬取）

        Args:
            source: 指定来源，None则获取全部

        Returns:
            URL 集合
        """
        # 转义单引号，防止 SQL 注入和语法错误（如 "What's New Indonesia"）
        escaped_source = source.replace("'", "\\'") if source else None
        where_clause = f"WHERE source = '{escaped_source}'" if escaped_source else ""
        query = f"SELECT DISTINCT url FROM `{self.table_id}` {where_clause}"
        logger.info(f"query: {query}")
        try:
            result = self.client.query(query).result()
            return {row.url for row in result}
        except Exception as e:
            logger.warning(f"获取已存在URL失败: {e}")
            return set()

    def get_latest_publish_date(self, source: str) -> Optional[str]:
        """
        获取指定来源最新的发布日期（用于增量爬取）

        Args:
            source: 来源名称

        Returns:
            最新发布日期字符串，格式 YYYY-MM-DD
        """
        query = f"""
        SELECT MAX(publish_date) as latest_date
        FROM `{self.table_id}`
        WHERE source = '{source}'
        """

        try:
            result = list(self.client.query(query).result())
            if result and result[0].latest_date:
                return str(result[0].latest_date)
        except Exception as e:
            logger.warning(f"获取最新发布日期失败: {e}")

        return None
