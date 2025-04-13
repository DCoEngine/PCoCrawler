# PCoCrawler - arXiv论文爬取与处理工具

PCoCrawler是一个用于爬取、处理和管理arXiv论文的工具集，支持论文爬取、翻译、分类、PDF下载（私有化保存）、知识库上传和 dify RAG处理（内部论文增强检索，满足特定任务的需求）。

## 主要功能

- **arXiv论文爬取**：从arXiv获取论文信息，支持按日期、分类和关键词筛选
- **论文数据处理**：管理论文数据库，支持翻译和分类，使用私有化ollama服务进行翻译和分类，大模型采用gemma2:9b模型或者显存足够采用gemma2:27b模型。
- **导出功能**：支持Markdown和CSV格式导出
- **PDF处理**：下载论文PDF并上传到FTP服务器
- **知识库集成**：将处理后的论文上传到知识库系统
- **RAG处理**：为知识库中的论文内容添加关键词和元数据

## 准备要求

### arXiv论文爬取准备

1. **配置设置**:
   - 创建配置文件包含:
     - 默认分类白名单/黑名单 (如 ["cs.CV", "cs.AI", "cs.LG"])
     - 默认关键词过滤
     - 代理设置 (如果需要)
     - 输出目录路径

2. **环境要求**:
   - Python 3.8+ 环境
   - 稳定网络连接
   - 足够的磁盘空间存储论文元数据

### PDF处理准备

1. **FTP服务器配置**:
   - 获取FTP服务器凭据:
     - 主机地址
     - 用户名和密码
     - 基础目录路径
   - 验证FTP连接

2. **知识库集成**:
   - 获取知识库API凭据:
     - API URL
     - 数据集ID
     - API密钥

3. **本地存储**:
   - 创建临时文件目录
   - 确保足够的PDF存储空间

### 通用要求

1. **定时任务配置**:
   - Windows: 配置任务计划程序
   - Linux: 设置cron job
   - 配置日志路径

### Ollama服务配置（搭建私有化翻译服务器，采用gemma2:9b模型或者显存足够采用gemma2:27b模型）

1. **安装Ollama**:
   - Windows: 下载安装包从 https://ollama.com/download
   - Linux/macOS: 
     ```bash
     curl -fsSL https://ollama.com/install.sh | sh
     ```

2. **下载gemma2:9b模型**:
   ```bash
   ollama pull gemma2:9b
   ```

3. **启动Ollama服务**:
   ```bash
   ollama serve
   ```

4. **验证安装**:
   ```bash
   ollama list
   ```
   应显示gemma2:9b模型已下载

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

### 爬取arXiv论文，并上传md文件到dify知识库
```python
python arxiv_crawler.py --date 2025-01-01 --category cs.CL --keyword machine learning
```

### 处理PDF文件。1.下载PDF文件到私有FTP服务器；2.根据论文领域更新知识库文件的关键字
```python
python batch_down_pdf.py
```

### 自动化定时任务

将爬取和处理PDF配置为系统的定时任务，实现自动化抓取和上传知识库。

#### Windows 任务计划程序配置

1. 创建爬取任务：
   - 打开"任务计划程序" -> 创建任务
   - 常规选项卡：命名如"arXiv论文爬取"
   - 触发器：每天凌晨2点
   - 操作：启动程序 `python.exe`，参数 `d:/Codes/DCoEngine/PCoCrawler/arxiv_crawler.py --date yesterday --category cs.CL`
   - 条件：只在网络连接时运行

2. 创建PDF处理任务：
   - 类似配置，但：
   - 命名如"arXiv PDF处理"
   - 触发器：每天凌晨3点（爬取完成后1小时）
   - 操作：启动程序 `python.exe`，参数 `d:/Codes/DCoEngine/PCoCrawler/batch_down_pdf.py`

#### Linux 定时任务

1. 创建shell脚本`run_pipeline.sh`：
```bash
#!/bin/bash
# 运行爬取
/usr/bin/python3 /path/to/PCoCrawler/arxiv_crawler.py --date yesterday --category cs.CL >> /var/log/arxiv_crawler.log 2>&1

# 等待5秒
sleep 5

# 运行PDF处理
/usr/bin/python3 /path/to/PCoCrawler/batch_down_pdf.py >> /var/log/pdf_processor.log 2>&1
```

2. 设置脚本可执行权限：
```bash
chmod +x run_pipeline.sh
```

3. 配置crontab：
```bash
crontab -e
```

4. 添加以下内容：
```
# 每天2:00运行整个处理流程
0 2 * * * /path/to/run_pipeline.sh
```

注意事项：
1. 请根据实际路径调整脚本位置
2. 可以调整`--category`参数选择关注的论文领域
3. 建议监控日志文件确保任务正常运行


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
