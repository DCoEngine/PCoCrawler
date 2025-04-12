import asyncio
import csv
import shutil
import sqlite3
import os
import ollama
import subprocess

from collections import defaultdict
from dataclasses import dataclass, fields
from datetime import datetime, timedelta, UTC
from pathlib import Path
from ollama import Client

from rich.console import Console
from typing_extensions import Iterable

from async_translator import async_translate
from ftp_client import FTPClient
from proc_md_files import ProcFiles
from categories import parse_categories

@dataclass
class Paper:
    first_submitted_date: datetime
    title: str
    categories: list
    url: str
    authors: str
    abstract: str
    comments: str
    title_translated: str | None = None
    abstract_translated: str | None = None
    first_announced_date: datetime | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row):
        return cls(
            first_submitted_date=datetime.strptime(row["first_submitted_date"], "%Y-%m-%d"),
            title=row["title"],
            categories=row["categories"].split(","),
            url=row["url"],
            authors=row["authors"],
            abstract=row["abstract"],
            comments=row["comments"],
            title_translated=row["title_translated"],
            abstract_translated=row["abstract_translated"],
            first_announced_date=datetime.strptime(row["first_announced_date"], "%Y-%m-%d"),
        )
    @property
    def papers_cool_url(self):
        return self.url.replace("https://arxiv.org/abs", "https://papers.cool/arxiv")
    
    @property
    def pdf_url(self):
        return self.url.replace("https://arxiv.org/abs", "https://arxiv.org/pdf")
    
    def download_file_with_curl(self, url, output_file_path):
        try:
            # 构建 curl 命令
            command = ['curl', '-o', output_file_path, url]

            # 执行 curl 命令
            subprocess.run(command, check=True)

            print(f"文件已成功下载到 {output_file_path}")
        except subprocess.CalledProcessError as e:
            print(f"下载失败: {e}")

    def save_text_to_file(self, text, file_path):
        # 获取文件所在的目录
        directory = os.path.dirname(file_path)

        # 如果目录不存在，则创建它
        if not os.path.exists(directory):
            os.makedirs(directory)

        # 再次尝试保存文本到文件
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(text)      

    def exec_pdf_trans(self, filePath, fileName, pdf_trans_config: dict):
        """执行PDF翻译命令
        
        参数:
            filePath: 输入文件路径
            fileName: 文件名
            pdf_trans_config: PDF翻译配置字典，包含:
                - path: pdf2zh路径
                - threads: 线程数
                - output_dir: 输出目录
        """
        try:
            command = [
                pdf_trans_config['path'],
                filePath,
                "-t", str(pdf_trans_config.get('threads', 4)),
                "-li", "en",
                "-lo", "zh",
                "-s", "ollama:gemma2:9b",
                "-o", os.path.join(pdf_trans_config['output_dir'], fileName)
            ]
            print("Executing command:", " ".join(command))
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Comm exec failed:{e.stderr}")

    def call_ollama_chat(self, input_text, ollama_config: dict):
        """
        使用Ollama API的chat功能进行对话。

        参数:
        input_text (str): 输入的文本消息。
        ollama_config (dict): Ollama配置，包含host和model参数

        返回:
        str: Ollama API返回的文本响应。
        """
        try:
            client = Client(host=ollama_config['host'])   
            response = client.generate(model=ollama_config['model'], prompt="请总结所有**摘要**的内容，提取最重要的10条，以所属的领域关键字和项目列表1,2,3,4返回。"+ input_text, stream=False)
            generated_text = response['response']
            print(f"总结结果: {generated_text}")
            return generated_text
        except Exception as e:
            print(f"调用Ollama API时出错: {e}")
            return None

    def call_ollama_generate(self, input_text, ollama_config: dict):
        """
        使用Ollama API生成文本

        参数:
        input_text (str): 输入的文本消息
        ollama_config (dict): Ollama配置，包含host和model参数

        返回:
        str: Ollama API返回的文本响应
        """
        try:
            client = Client(host=ollama_config['host'])
            response = client.generate(model=ollama_config['model'], prompt="Please translate the following English content into Chinese.Return only the"+
                                       "translated content.Return only the translated content."+ input_text, stream=False)
            generated_text = response['response']
            print(f"Trans: {generated_text}")
            return generated_text
        except Exception as e:
            print(f"Ollama API Error: {e}")
            return None

    def to_markdown(self, ftp_config: dict, ollama_config: dict, file_path_config: dict):
        """生成Markdown格式的论文信息
        
        参数:
            ftp_config: FTP配置字典
            ollama_config: Ollama配置字典
            file_path_config: 文件路径配置字典，包含:
                - tmp_dir: 临时文件目录
                - graph_dir: Graph文件目录
        """
        categories = ",".join(parse_categories(self.categories))
        summary_str = self.call_ollama_generate(self.abstract, ollama_config).replace(" ","").replace("\r\n", "").replace("\n", "")
        abstract = (
            f"> **摘要**: {summary_str}"
            if summary_str
            else f"- **Abstract**: {self.abstract}"
        )
        fileName = self.pdf_url.split("/")[-1]
        savePath = file_path_config['tmp_dir']
        summaryFile = os.path.join(savePath, fileName, "摘要.md")
        pdfFile = os.path.join(savePath, fileName, f"{fileName}.pdf")
        dirPrefix = os.path.join(file_path_config['graph_dir'], self.first_announced_date.strftime("%Y-%m-%d"), fileName)
        monoPdfFile = os.path.join(savePath, fileName, f"{fileName}-mono.pdf")
        dualPdfFile = os.path.join(savePath, fileName, f"{fileName}-dual.pdf")
        self.save_text_to_file(self.abstract.replace("\r\n", "").replace("\n", "") + "\n\n" + summary_str, summaryFile)    
        if not os.path.exists(pdfFile):
            self.download_file_with_curl(self.pdf_url, pdfFile)
        if not os.path.exists(monoPdfFile):
            self.exec_pdf_trans(pdfFile, fileName, pdf_trans_config)
        ftp_client = FTPClient()
        ftp_client.connect(
            host=ftp_config['host'],
            user=ftp_config['user'],
            password=ftp_config['password']
        )
        if os.path.exists(summaryFile):
            ftp_client.upload_file(summaryFile, dirPrefix +"/摘要.md")
        if os.path.exists(pdfFile):
            ftp_client.upload_file(pdfFile, dirPrefix +"/"+ fileName +".pdf")
        if os.path.exists(monoPdfFile):
            ftp_client.upload_file(monoPdfFile, dirPrefix +"/"+ fileName +"-mono.pdf")
        if os.path.exists(dualPdfFile):
            ftp_client.upload_file(dualPdfFile, dirPrefix +"/"+ fileName +"-dual.pdf")
        ftp_client.disconnect()
        
        dateStr = self.first_announced_date.strftime("%Y-%m-%d")
        fileCatelog = self.pdf_url.split("/")[-1]
        zhTitle = self.call_ollama_generate(self.title, ollama_config).replace(" ","").replace("\r\n", "").replace("\n", "")
        return f"""> **英文标题**: {self.title} 
> **中文标题**: {zhTitle}
> **作者**: {self.authors}
> **首次提交**: {self.first_submitted_date.strftime("%Y-%m-%d")}
> **首次公告**: {dateStr}
> **原文链接**: {self.url}
> **原文PDF链接**: {self.pdf_url}
> **comment**: {self.comments}
> **领域**: {categories}
{abstract}

"""
    
    async def translate(self, langto="zh-CN"):
        self.title_translated = await async_translate(self.title, langto=langto)
        self.abstract_translated = await async_translate(self.abstract, langto=langto)


@dataclass
class PaperRecord:
    paper: Paper
    comment: str

    def to_markdown(self, ftp_config: dict, ollama_config: dict, file_path_config: dict):
        """生成Markdown格式的论文记录信息
        
        参数:
            ftp_config: FTP配置字典
            ollama_config: Ollama配置字典
            file_path_config: 文件路径配置字典
        """
        if self.comment != "-":
            return f"""- [{self.paper.title}]({self.paper.url})
  - **标题**: {self.paper.title_translated}
  - **Filtered Reason**: {self.comment}
"""
        else:
            return self.paper.to_markdown(ftp_config, ollama_config, file_path_config)


class PaperDatabase:
    def __init__(self, db_path="papers.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = self._row_factory
        self._create_table()

    @staticmethod
    def _row_factory(cursor, row):
        row = sqlite3.Row(cursor, row)
        # all fields in Paper, plus `update_time`
        if len(row.keys()) == len(fields(Paper)) + 1:
            return Paper.from_row(row)
        else:
            return row

    def _create_table(self):
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS papers (
                    url TEXT PRIMARY KEY,
                    authors TEXT NOT NULL,
                    title_translated TEXT,
                    first_submitted_date DATE NOT NULL,
                    first_announced_date DATE NOT NULL,
                    update_time DATETIME NOT NULL,
                    categories TEXT NOT NULL,
                    title TEXT NOT NULL,
                    comments TEXT NOT NULL,
                    abstract TEXT NOT NULL,
                    abstract_translated TEXT
                )
            """
            )

    def add_papers(self, papers: Iterable[Paper]):
        assert all([paper.first_announced_date is not None for paper in papers])
        with self.conn:
            data_to_insert = [
                (
                    paper.url,
                    paper.authors,
                    paper.abstract,
                    paper.title,
                    ",".join(paper.categories),
                    paper.first_submitted_date.strftime("%Y-%m-%d"),
                    paper.first_announced_date.strftime("%Y-%m-%d"),
                    paper.title_translated,
                    paper.abstract_translated,
                    paper.comments,
                    datetime.now(UTC).replace(tzinfo=None)
                )
                for paper in papers
            ]
            self.conn.executemany(
                """
                INSERT OR REPLACE INTO papers 
                (url, authors, abstract, title, categories, first_submitted_date, first_announced_date, title_translated, abstract_translated, comments, update_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                data_to_insert,
            )

    def count_new_papers(self, papers: Iterable[Paper]) -> int:
        cnt = 0
        for paper in papers:
            with self.conn:
                cursor = self.conn.execute(
                    """
                    SELECT * FROM papers WHERE url = ?
                    """,
                    (paper.url,),
                )
                if cursor.fetchone():
                    break
                else:
                    cnt += 1
        return cnt

    def fetch_papers_on_date(self, date: datetime) -> list[Paper]:
        with self.conn:
            cursor = self.conn.execute(
                """
                SELECT * FROM papers WHERE first_announced_date = ?
                """,
                (date.strftime("%Y-%m-%d"),),
            )
            return cursor.fetchall()

    def fetch_all(self) -> list[Paper]:
        with self.conn:
            cursor = self.conn.execute(
                """
                SELECT * FROM papers ORDER BY url DESC
                """
            )
            return cursor.fetchall()

    def newest_update_time(self) -> datetime:
        """
        最新更新时间是“上一次爬取最新论文的时间”
        由于数据库可能补充爬取过去的论文，所以先选最新论文，再从其中选最新的爬取时间
        """
        with self.conn:
            cursor = self.conn.execute(
                """
                SELECT MAX(update_time) as max_updated_time
                FROM papers
                WHERE first_announced_date = (SELECT MAX(first_announced_date) FROM papers)
                """
            )
        time = cursor.fetchone()["max_updated_time"].split(".")[0]
        return datetime.strptime(time, "%Y-%m-%d %H:%M:%S")

    async def translate_missing(self, langto="zh-CN"):
        with self.conn:
            cursor = self.conn.execute(
                "SELECT url, title, abstract FROM papers WHERE title_translated IS NULL OR abstract_translated IS NULL"
            )
            papers = cursor.fetchall()

        async def worker(url, title, abstract):
            title_translated = await async_translate(title, langto=langto) if title else None
            abstract_translated = await async_translate(abstract, langto=langto) if abstract else None
            with self.conn:
                self.conn.execute(
                    "UPDATE papers SET title_translated = ?, abstract_translated = ? WHERE url = ?",
                    (title_translated, abstract_translated, url),
                )

        await asyncio.gather(*[worker(url, title, abstract) for url, title, abstract in papers])


class PaperExporter:
    def __init__(
        self,
        date_from: str,
        date_until: str,
        categories_blacklist: list[str],
        categories_whitelist: list[str],
        database_path: str,
        ftp_config: dict,
        dify_config: dict,
        ollama_config: dict,
        pdf_trans_config: dict,
        file_path_config: dict
    ):
        """初始化PaperExporter
        
        参数:
            date_from: 开始日期
            date_until: 结束日期
            categories_blacklist: 类别黑名单
            categories_whitelist: 类别白名单
            database_path: 数据库路径
            ftp_config: FTP配置字典
            dify_config: Dify知识库配置字典
            ollama_config: Ollama配置字典
            pdf_trans_config: PDF翻译配置字典
            file_path_config: 文件路径配置字典
        """
        self.db = PaperDatabase(database_path)
        self.date_from = datetime.strptime(date_from, "%Y-%m-%d")
        self.date_until = datetime.strptime(date_until, "%Y-%m-%d")
        self.date_range_days = (self.date_until - self.date_from).days + 1
        self.categories_blacklist = set(categories_blacklist)
        self.categories_whitelist = set(categories_whitelist)
        self.console = Console()
        self.ftp_config = ftp_config
        self.dify_config = dify_config
        self.ollama_config = ollama_config

    def filter_papers(self, papers: list[Paper]) -> tuple[list[PaperRecord], list[PaperRecord]]:
        filtered_paper_records = []
        chosen_paper_records = []
        for paper in papers:
            categories = set(paper.categories)
            if not (self.categories_whitelist & categories):
                categories_str = ",".join(categories)
                filtered_paper_records.append(PaperRecord(paper, f"none of {categories_str} in whitelist"))
            elif black := self.categories_blacklist & categories:
                black_str = ",".join(black)
                filtered_paper_records.append(PaperRecord(paper, f"cat:{black_str} in blacklist"))
            else:
                chosen_paper_records.append(PaperRecord(paper, "-"))
        return chosen_paper_records, filtered_paper_records

    def to_markdown(self, output_dir="./output_llms", filename_format="%Y-%m-%d", metadata=None):
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)

        if metadata:
            repo_url = metadata["repo_url"]
            categories = ",".join(metadata["category_whitelist"])
            optional_keywords = ", ".join(metadata["optional_keywords"])
            preface_str = f"""
>
> 领域白名单：{categories}
> 关键词： {optional_keywords}

""".lstrip()
        else:
            preface_str = ""

        for i in range(self.date_range_days):
            current = self.date_from + timedelta(days=i)
            current_filename = current.strftime(filename_format)

            with open(output_dir / f"{current_filename}.md", "w", encoding="utf-8") as file:
                papers = self.db.fetch_papers_on_date(current)
                chosen_records, filtered_records = self.filter_papers(papers)
                papers_str = f"# 论文全览：{current_filename}\n\n共有{len(chosen_records)}篇相关领域论文\n\n"

                chosen_dict = defaultdict(list)
                for record in chosen_records:
                    chosen_dict[record.paper.categories[0]].append(record)
                for category in sorted(chosen_dict.keys()):
                    category_en = parse_categories([category], lang="en")[0]
                    category_zh = parse_categories([category], lang="zh-CN")[0]
                    papers_str += f"## {category_zh}({category}:{category_en})\n\n"
                    for record in chosen_dict[category]:
                        papers_str += record.paper.to_markdown(self.ftp_config, self.ollama_config, self.file_path_config)

                file.write(preface_str + papers_str)
            
            if len(chosen_records) > 0:
                ftp_client = FTPClient()
                ftp_client.connect(
                    host=self.ftp_config['host'],
                    user=self.ftp_config['user'],
                    password=self.ftp_config['password']
                )
                local_file_path = os.path.join("./output_llms/", current_filename + ".md")
                ftp_client.upload_file(
                    local_file_path,
                    f"{self.ftp_config['base_path']}/{current_filename}/{current_filename}.md"
                )
                ftp_client.disconnect()
                
                graph_file_path = os.path.join(
                    "./output_llms/", 
                    f"{self.dify_config['file_prefix']}{current_filename}.md"
                )
                shutil.copy(local_file_path, graph_file_path)
                ProcFiles.upload_to_knowledge_base(
                    graph_file_path, 
                    self.dify_config['dataset_id'], 
                    self.dify_config['api_key'], 
                    original_document_id=None
                )

                      
            self.console.log(
                f"[bold green]Output {current_filename}.md completed. {len(chosen_records)} papers chosen, {len(filtered_records)} papers filtered"
            )
           

    def to_csv(self, output_dir="./output_llms", filename_format="%Y-%m-%d", header=True, csv_config={}):
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)

        csv_table = {
            "Title": lambda record: record.paper.title,
            "Interest": lambda record: ("chosen" if record.comment == "-" else "filtered"),
            "Title Translated": lambda record: (
                record.paper.title_translated if record.paper.title_translated else "-"
            ),
            "Categories": lambda record: ",".join(record.paper.categories),
            "Authors": lambda record: record.paper.authors,
            "URL": lambda record: record.paper.url,
            "PapersCool": lambda record: record.paper.url.replace("https://arxiv.org/abs", "https://papers.cool/arxiv"),
            "First Submitted Date": lambda record: record.paper.first_submitted_date.strftime("%Y-%m-%d"),
            "First Announced Date": lambda record: record.paper.first_announced_date.strftime("%Y-%m-%d"),
            "Abstract": lambda record: record.paper.abstract,
            "Abstract Translated": lambda record: (
                record.paper.abstract_translated if record.paper.abstract_translated else "-"
            ),
            "Comments": lambda record: record.paper.comments,
            "Note": lambda record: record.comment,
        }

        headers = list(csv_table.keys())

        for i in range(self.date_range_days):
            current = self.date_from + timedelta(days=i)
            current_filename = current.strftime(filename_format)

            with open(output_dir / f"{current_filename}.csv", "w", encoding="utf-8") as file:
                if "lineterminator" not in csv_config:
                    csv_config["lineterminator"] = "\n"
                writer = csv.writer(file, **csv_config)
                if header:
                    writer.writerow(headers)

                papers = self.db.fetch_papers_on_date(current)
                chosen_records, filtered_records = self.filter_papers(papers)
                for record in chosen_records + filtered_records:
                    writer.writerow([fn(record) for fn in csv_table.values()])

                self.console.log(
                    f"[bold green]Output {current_filename}.csv completed. {len(chosen_records)} papers chosen, {len(filtered_records)} papers filtered"
                )


if __name__ == "__main__":
    from datetime import date, timedelta

    today = date.today()
    
    # 配置参数
    ftp_config = {
        'host': 'your_ftp_host',  # FTP服务器地址
        'user': 'your_username',  # FTP用户名
        'password': 'your_password',  # FTP密码
        'base_path': '/AI/paper/Graph'  # FTP基础路径
    }
    
    dify_config = {
        'dataset_id': 'your_dataset_id',  # Dify知识库数据集ID
        'api_key': 'your_api_key',  # Dify API密钥
        'file_prefix': 'Graph_'  # 文件前缀
    }
    
    ollama_config = {
        'host': 'http://x.x.x.x:11434',  # Ollama服务地址
        'model': 'gemma2:9b'  # Ollama模型名称
    }
    
    categories_whitelist = ["cs.CV", "cs.AI", "cs.LG", "cs.CL", "cs.IR", "cs.MA"]

    # 文件路径配置
    file_path_config = {
        'tmp_dir': '/data/tmp',  # 临时文件目录
        'graph_dir': '/AI/paper/Graph'  # Graph文件目录
    }
    
    # PDF翻译配置
    pdf_trans_config = {
        'path': '/path/to/pdf2zh',  # pdf2zh路径
        'threads': 4,  # 线程数
        'output_dir': '/data/tmp'  # 输出目录
    }

    exporter = PaperExporter(
        date_from=today.strftime("%Y-%m-%d"),
        date_until=today.strftime("%Y-%m-%d"),
        categories_blacklist=[],
        categories_whitelist=categories_whitelist,
        database_path="papers.db",
        ftp_config=ftp_config,
        dify_config=dify_config,
        ollama_config=ollama_config,
        pdf_trans_config=pdf_trans_config,
        file_path_config=file_path_config
    )
    exporter.to_markdown()  # 调用导出Markdown方法，使用初始化时传入的配置参数
