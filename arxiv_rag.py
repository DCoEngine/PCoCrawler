import os
import requests
import json
import logging

class ArxivRAG(object):
    """
    ArxivRAG 类用于处理arXiv论文的检索和上传到知识库
    主要功能包括：
    - 文本分割处理
    - 文件预处理和上传到知识库API
    """
    @staticmethod
    def split_text(content_text, separator, overlap):
        """
        将文本按指定分隔符分割成多个部分
        
        参数:
            content_text (str): 要分割的文本内容
            separator (str): 分隔符字符串
            overlap (int): 重叠字符数
            
        返回:
            list: 分割后的文本片段列表
        """
        parts = []
        start = 0
        
        while start < len(content_text):
            # 找到下一个分隔符的位置
            end = content_text.find(separator, start)
            
            if end == -1:
                # 如果没有找到分隔符，将剩余部分添加到结果中
                parts.append(content_text[start:])
                break
            
            # 添加当前部分（包括重叠部分）
            parts.append(content_text[start:end + overlap])
            
            # 更新起始位置，跳过分隔符
            start = end + len(separator)
        
        return parts

    @staticmethod
    def upload_to_knowledge_base(file_path, dataset_id, api_key, original_document_id, api_base_url, separator, max_tokens, chunk_overlap):
        """
        上传处理后的文件到知识库
        
        参数:
            file_path (str): 原始文件路径
            dataset_id (str): 知识库数据集ID
            api_key (str): API认证密钥
            original_document_id (str): 原始文档ID(用于更新)
            api_base_url (str): 知识库API基础URL
            separator (str): 文本分割符
            max_tokens (int): 最大token数
            chunk_overlap (int): 块重叠数
            
        返回:
            None
        """
        url = f"{api_base_url}/v1/datasets/{dataset_id}/document/create-by-file"
        headers = {
            'Authorization': f'Bearer {api_key}'
        }
        
        # 构建process_rule
        process_rule = {
            "indexing_technique": "high_quality",
            "process_rule": {
                "mode": "custom",
                "rules": {
                    "pre_processing_rules": [
                        {"id": "remove_extra_spaces", "enabled": False},
                        {"id": "remove_urls_emails", "enabled": False}
                    ],
                    "segmentation": {
                        "separator": separator,
                        "max_tokens": max_tokens,
                        "chunk_overlap": chunk_overlap
                    }
                }
            }
        }
        
        # 如果有original_document_id，则添加到process_rule
        if original_document_id:
            process_rule["original_document_id"] = original_document_id
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            # 跳过前7行，从第8行开始读取
            file_content = ''.join(lines[7:])
        
        # 分割文本内容
        split_contents = ArxivRAG.split_text(
            content_text=file_content,
            separator=")\n\n",
            overlap=2
        )
        
        # 创建一个列表来存储处理后的内容
        processed_contents = []

        for content in split_contents:
            # 跳过包含 ## 的内容
            if "##" in content:
                logging.debug(f"Skipping content due to '##': {content[:50]}...")  # 记录前50个字符以便调试
                continue
            # 在内容加入#####
            processed_content = content + "#####"
            processed_contents.append(processed_content)

        # 将处理后的内容写入一个新的文件
        processed_file_path = f"Processed_{os.path.basename(file_path)}"
        with open(processed_file_path, 'w', encoding='utf-8') as processed_file:
            processed_file.write(''.join(processed_contents))

        # 准备文件上传
        with open(processed_file_path, 'rb') as processed_file:
            files = {
                'file': (os.path.basename(processed_file_path), processed_file, 'text/markdown')
            }

            # 发送POST请求
            response = requests.post(url, headers=headers, files=files, data={'data': json.dumps(process_rule)})

            # 检查响应
            if response.status_code == 200:
                logging.info(f"Successfully uploaded {processed_file_path}")
            else:
                logging.error(f"Failed to upload {processed_file_path}: {response.status_code} - {response.text}")

        # 删除处理后的文件
        try:
            os.remove(processed_file_path)
        except PermissionError:
            logging.warning(f"Failed to delete {processed_file_path}: PermissionError - File is still in use.")

    def main():
        """
        主函数，配置并执行文件上传到知识库
        
        参数:
            无(从命令行参数获取)
        """
        # 配置参数
        file_path = "./output_llms/2025-01-03.md"
        dataset_id = ""
        api_key = ""
        original_document_id = ""  # 留空表示新文档
        api_base_url = "http://x.x.x.x"  # 知识库API基础URL
        separator = "#####"  # 文本分割符
        max_tokens = 1800  # 最大token数
        chunk_overlap = 50  # 块重叠数

        ArxivRAG.upload_to_knowledge_base(
            file_path=file_path,
            dataset_id=dataset_id,
            api_key=api_key,
            original_document_id=original_document_id,
            api_base_url=api_base_url,
            separator=separator,
            max_tokens=max_tokens,
            chunk_overlap=chunk_overlap
        )

    if __name__ == "__main__":
        main()
