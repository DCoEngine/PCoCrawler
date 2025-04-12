# PCoCrawler - arXiv论文爬取与处理工具

PCoCrawler是一个用于爬取、处理和管理arXiv论文的工具集，支持论文爬取、翻译、分类、PDF下载、知识库上传和 dify RAG处理。

## 主要功能

- **arXiv论文爬取**：从arXiv获取论文信息，支持按日期、分类和关键词筛选
- **论文数据处理**：管理论文数据库，支持翻译和分类
- **导出功能**：支持Markdown和CSV格式导出
- **PDF处理**：下载论文PDF并上传到FTP服务器
- **知识库集成**：将处理后的论文上传到知识库系统
- **RAG处理**：为知识库中的论文内容添加关键词和元数据

## 安装指南

1. 克隆仓库：
   ```bash
   git clone https://github.com/DCoEngine/PCoCrawler.git
   cd PCoCrawler
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

## 使用说明

### 爬取arXiv论文
```python
python arxiv_crawler.py --date 2025-01-01 --category cs.CL
```

### 处理PDF文件，下载PDF文件到私有FTP服务器
```python
python batch_down_pdf.py
```

### 上传到知识库
```python
python arxiv_rag.py
```

### RAG处理，根据领域更新dify的关键字
```python
python batch_proc_rag.py
```

## 示例

查看`examples/`目录下的示例文件：
- `example.md`：Markdown格式论文示例
- `example.csv`：CSV格式论文示例

## 贡献指南

欢迎提交Pull Request。请确保：
1. 代码符合PEP8规范
2. 添加适当的单元测试
3. 更新文档

## 许可证

MIT License
