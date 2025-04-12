import os
import ftplib
import requests
import json

class ProcFiles:
    """
    文件处理工具类，包含文本分割、FTP操作和上传到知识库的功能。
    """
    
    @staticmethod
    def split_text(text, separator=")\n\r", overlap=2):
        """
        使用指定的分隔符和重叠量将文本分割成块。
        
        参数:
            text (str): 要分割的文本
            separator (str): 用于分割的分隔符模式
            overlap (int): 块之间的重叠字符数
            
        返回:
            list: 文本块列表
        """
        text_chunks = []
        start = 0
        
        while start < len(text):
            # 查找下一个分隔符位置
            end = text.find(separator, start)
            
            if end == -1:
            # 如果没有找到更多分隔符，添加剩余文本
                text_chunks.append(text[start:])
                break
            
            # 添加当前块（带重叠）
            text_chunks.append(text[start:end + overlap])
            
            # 将起始位置移动到分隔符之后
            start = end + len(separator)
        
        return text_chunks

    @staticmethod
    def upload_to_knowledge_base(file_path, knowledge_base_url, dataset_id, api_key, 
                               original_document_id=None, separator="#####", 
                               max_tokens=2000, chunk_overlap=0):
        """
        通过API将处理后的文件上传到知识库。
        
        参数:
            file_path (str): 要上传的文件路径
            knowledge_base_url (str): 知识库API的基础URL
            dataset_id (str): 目标数据集ID
            api_key (str): API认证密钥
            original_document_id (str, optional): 用于文档更新的ID
            separator (str): 文本分割的分隔符
            max_tokens (int): 每个块的最大token数
            chunk_overlap (int): 块之间的重叠token数
            
        返回:
            None
        """
        url = f"{knowledge_base_url}/v1/datasets/{dataset_id}/document/create-by-file"
        headers = {
            'Authorization': f'Bearer {api_key}'
        }
        
        # 配置知识库的处理规则
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
        
        # 如果提供了原始文档ID（用于更新）
        if original_document_id:
            process_rule["original_document_id"] = original_document_id
        
        # 读取文件内容，跳过前7行（头部）
        with open(file_path, 'r', encoding='utf-8') as file_handler:
            lines = file_handler.readlines()
            file_content = ''.join(lines[7:])  # Skip first 7 lines
        
        # 将文本内容分割成块
        split_contents = ProcFiles.split_text(
            file_content.replace("> **","").replace("- **","").replace("**",""), 
            separator="\n\n", 
            overlap=2
        )
        
        # 处理每个内容块
        processed_contents = []
        for chunk in split_contents:
            if "##" in chunk:  # Skip sections with headers
                print(f"Skipping header section: {chunk[:50]}...")
                continue
            processed_contents.append(chunk + "#####")  # Add separator

        # 将处理后的内容写入临时文件
        processed_file_path = f"Processed_{os.path.basename(file_path)}"
        with open(processed_file_path, 'w', encoding='utf-8') as processed_file:
            processed_file.write(''.join(processed_contents))

        # 将临时文件上传到知识库
        with open(processed_file_path, 'rb') as processed_file:
            files = {
                'file': (os.path.basename(processed_file_path), processed_file, 'text/markdown')
            }
            response = requests.post(
                url, 
                headers=headers, 
                files=files, 
                data={'data': json.dumps(process_rule)}
            )

            if response.status_code == 200:
                print(f"Successfully uploaded {processed_file_path}")
            else:
                print(f"Upload failed ({response.status_code}): {response.text}")

        # 清理临时文件
        try:
            os.remove(processed_file_path)
        except PermissionError:
            print(f"Failed to delete temp file: {processed_file_path}")


    @staticmethod
    def download_files_with_extension(ftp, remote_dir, local_dir, file_prefix, 
                                    knowledge_base_url, dataset_id, api_key,
                                    separator="#####", max_tokens=2000, chunk_overlap=0):
        """
        从FTP服务器下载文件并上传到知识库。
        
        参数:
            ftp: FTP连接对象
            remote_dir: 远程目录路径
            local_dir: 本地下载目录
            file_prefix: 下载文件的前缀
            knowledge_base_url: 知识库API URL
            dataset_id: 目标数据集ID
            api_key: API认证密钥
            separator (str): 文本分割的分隔符
            max_tokens (int): 每个块的最大token数
            chunk_overlap (int): 块之间的重叠token数
        """
        
        try:
            ftp.cwd(remote_dir)  # 切换到远程目录
            print(f"Changed to directory: {remote_dir}")
        except ftplib.error_perm:
            print(f"Failed to access directory: {remote_dir}")
            return

        try:
            files = ftp.nlst()  # 列出文件
            print(f"Found files: {files}")
        except ftplib.error_perm:
            print(f"Failed to list files in: {remote_dir}")
            return
        
        # 设置文件传输的二进制模式
        ftp.sendcmd('TYPE I')    

        for filename in files:
            remote_path = os.path.join(remote_dir, filename)
            local_path = os.path.join(local_dir, filename)
            
            print(f"Processing file: {remote_path}")

            # 验证文件存在并获取大小
            try:
                file_size = ftp.size(remote_path)
                print(f"File size: {file_size} bytes")
            except ftplib.error_perm as perm_error:
                print(f"Access error: {perm_error}")
                continue
            except ftplib.all_errors as error:
                print(f"Error checking file: {error}")
                continue  
            
            # 如果需要，创建本地目录
            local_file_dir = os.path.dirname(local_path)
            if not os.path.exists(local_file_dir):
                os.makedirs(local_file_dir)
                
            # 下载文件
            with open(local_path, 'wb') as local_file:
                ftp.retrbinary(f'RETR {remote_path}', local_file.write)
            print(f"Downloaded: {remote_path} to {local_path}")

            # 上传到知识库
            ProcFiles.upload_to_knowledge_base(
                local_path, 
                knowledge_base_url,
                dataset_id, 
                api_key,
                separator=separator,
                max_tokens=max_tokens,
                chunk_overlap=chunk_overlap
            )

    @staticmethod
    def main(ftp_host, ftp_user, ftp_pass, remote_dir, local_dir, file_prefix,
             knowledge_base_url, dataset_id, api_key, separator="#####", 
             max_tokens=2000, chunk_overlap=0):
        """
        主函数，用于连接FTP并处理文件。
        
        参数:
            ftp_host: FTP服务器地址
            ftp_user: FTP用户名
            ftp_pass: FTP密码
            remote_dir: 远程目录路径
            local_dir: 本地下载目录
            file_prefix: 下载文件的前缀
            knowledge_base_url: 知识库API URL
            dataset_id: 目标数据集ID
            api_key: API认证密钥
            separator (str): 文本分割的分隔符
            max_tokens (int): 每个块的最大token数
            chunk_overlap (int): 块之间的重叠token数
        """
        try:
            with ftplib.FTP(ftp_host) as ftp:
                ftp.login(user=ftp_user, passwd=ftp_pass)
                print(f"Connected to {ftp_host} as {ftp_user}")
                ftp.set_pasv(True)  # 使用被动模式
                ftp.encoding = 'utf-8'             
                ProcFiles.download_files_with_extension(
                    ftp, remote_dir, local_dir, file_prefix,
                    knowledge_base_url, dataset_id, api_key,
                    separator=separator, max_tokens=max_tokens, chunk_overlap=chunk_overlap
                )
        except ftplib.all_errors as ftp_error:
            print(f"FTP error: {ftp_error}")
