import requests
import re
import os

from ftp_client import FTPClient 

def get_documents(api_url, dataset_id, api_key, page, limit):
    """
    获取指定知识库 ID 下的所有文档。

    :param api_url: API 的基础 URL
    :param dataset_id: 知识库 ID
    :param api_key: API 密钥
    :param limit: 返回的文档数量，默认 20，范围 1-100
    :return: 文档 ID 列表
    """
    url = f"{api_url}/v1/datasets/{dataset_id}/documents"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    params = {
        "limit": limit,
        "page": page
    }
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        documents = response.json().get('data', [])
        # 提取文档 ID 列表
        document_ids = [doc.get('id') for doc in documents if doc.get('id')]
        document_names = [doc.get('name') for doc in documents if doc.get('name')]
        return document_ids, document_names
    else:
        print(f"Failed to get documents. Status code: {response.status_code}, Response: {response.text}")
        return []

def delete_document(api_url, dataset_id, document_id, api_key):
    """
    删除指定知识库 ID 下的单个文档。

    :param api_url: API 的基础 URL
    :param dataset_id: 知识库 ID
    :param document_id: 文档 ID
    :param api_key: API 密钥
    :return: 删除结果
    """
    url = f"{api_url}/v1/datasets/{dataset_id}/documents/{document_id}"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    response = requests.delete(url, headers=headers)
    
    if response.status_code == 200:
        print(f"Document {document_id} deleted successfully.")
    else:
        print(f"Failed to delete document {document_id}. Status code: {response.status_code}, Response: {response.text}")

def get_segments_and_content(api_url, dataset_id, document_id, api_key):
    """
    获取指定文档下的所有分段ID。

    :param api_url: API 的基础 URL
    :param dataset_id: 知识库 ID
    :param document_id: 文档 ID
    :param api_key: API 密钥
    :return: 分段 ID 列表
    """
    url = f"{api_url}/v1/datasets/{dataset_id}/documents/{document_id}/segments"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        segments = response.json().get('data', [])
        # 提取分段 ID 列表和 content 字段
        segment_ids = []
        contents = []
        for segment in segments:
            segment_id = segment.get('id')
            content = segment.get('content')
            if segment_id:
                segment_ids.append(segment_id)
            if content:
                contents.append(content)
        return segment_ids, contents
    else:
        print(f"Failed to get segments for document {document_id}. Status code: {response.status_code}, Response: {response.text}")
        return [], []  


def process_content(content, ftp_dir_Prefix, save_path, ftp_host, ftp_user, ftp_password):
    """
    处理 content 内容：
    1. 删除指定的论文链接部分（如果存在）。
    2. 提取 PDF 链接并下载到本地（如果存在）。

    :param content: 原始内容
    :return: 处理后的内容
    """
    if not content or not isinstance(content, str):
        # 如果 content 为空或不是字符串，直接返回
        print("Content is empty or invalid. Skipping processing.")
        return content

    # 删除指定的论文链接部分
    pattern_remove_links = r'英文论文: \[英文\]\(.*?\)中文论文: \[中文\]\(.*?\)中英对照论文: \[中英对照\]\(.*?\)'
    content = re.sub(pattern_remove_links, '', content)

    # 提取 PDF 链接
    pattern_extract_pdf = r'原文PDF链接: (https?://[^\s]+)comment:'
    pdf_links = re.findall(pattern_extract_pdf, content)

    for link in pdf_links:
        # 构造保存路径
        pdf_name = link.split('/')[-1]
        #save_path = "/data/tmp/" # 保存到 tmp 文件夹
        pdfFile = save_path + pdf_name +"/"+ pdf_name +".pdf"
        os.makedirs(os.path.dirname(pdfFile), exist_ok=True)  # 确保目录存在
        
        pattern = r'首次公告:\s*(\d{4}-\d{2}-\d{2})'
        match = re.search(pattern, content)
        if match:
            first_announced_date = match.group(1)  # 提取匹配到的日期字符串
        else:
            first_announced_date = "unknown_date"  # 设置默认值
            
        new_dir_Prefix = os.path.join(ftp_dir_Prefix, first_announced_date, pdf_name).replace("\\", "/")
        
        # 初始化 FTPClient 实例
        ftp_client_instance = FTPClient(ftp_host, ftp_user, ftp_password)
        
        if not os.path.exists(pdfFile):
            # 下载 PDF
            download_pdf(link, pdfFile)
        if os.path.exists(pdfFile):
            ftp_client_instance = FTPClient(ftp_host, ftp_user, ftp_password)
            ftp_client_instance.connect()            
            ftp_client_instance.upload_file(pdfFile, new_dir_Prefix +"/"+ pdf_name +".pdf")
            ftp_client_instance.disconnect()            

    # 返回处理后的内容
    return content

def download_pdf(url, save_path):
    """
    下载 PDF 文件到本地。

    :param url: PDF 文件的 URL
    :param save_path: 保存路径
    """
    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            print(f"PDF downloaded successfully: {save_path}")
        else:
            print(f"Failed to download PDF from {url}. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error downloading PDF from {url}: {e}")

def extract_fields(content):
    # 使用正则表达式提取“领域:”到“摘要:”之间的内容
    pattern = r'领域:\s*([^摘要:]*)摘要:'
    match = re.search(pattern, content)
    if match:
        fields = match.group(1).strip()
        if ',' in fields:
            # 如果包含逗号，按逗号分隔
            return [field.strip() for field in fields.split(',')]
        else:
            # 如果不包含逗号，直接返回一个包含单个元素的列表
            return [fields]
    else:
        return []

def update_segment_keywords(api_url, dataset_id, document_id, segment_id, api_key, content, keywords):
    """
    更新指定段的关键字为空。

    :param api_url: API 的基础 URL
    :param dataset_id: 知识库 ID
    :param document_id: 文档 ID
    :param segment_id: 分段 ID
    :param api_key: API 密钥
    :return: 更新结果
    """
    url = f"{api_url}/v1/datasets/{dataset_id}/documents/{document_id}/segments/{segment_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "segment": {
            "content": f"{content}",
            "answer": "", 
            "keywords": [f"{keyword}" for keyword in keywords],
            "enabled": True
        }
    }
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        print(f"Keywords for segment {segment_id} of document {document_id} updated successfully.")
    else:
        print(f"Failed to update keywords for segment {segment_id} of document {document_id}. Status code: {response.status_code}, Response: {response.text}")

def batch_proc_documents(api_url, dataset_id, api_key, ftp_dir_Prefix, save_path, page, limit, ftp_host, ftp_user, ftp_password):
    """
    批量处理指定知识库 ID 下的单页文档。

    :param api_url: API 的基础 URL
    :param dataset_id: 知识库 ID
    :param api_key: API 密钥
    :param page: 当前页码
    :param limit: 每页返回的文档数量，默认 15
    """
    print(f"Processing page {page} with limit {limit}...")
    document_ids, document_names = get_documents(api_url, dataset_id, api_key, page=page, limit=limit)
    
    if not document_ids:
        print("No documents to process on this page.")
        return
    
    for document_id, document_name in zip(document_ids, document_names):
        segment_ids, contents = get_segments_and_content(api_url, dataset_id, document_id, api_key)
        print(f"Document_id is {document_id}. Document_name is {document_name}.")
        for segment_id, content in zip(segment_ids, contents):
            keywords = extract_fields(content)
            processed_content = process_content(content, ftp_dir_Prefix, save_path, ftp_host, ftp_user, ftp_password)
            update_segment_keywords(api_url, dataset_id, document_id, segment_id, api_key, processed_content, keywords)

        # delete_document(api_url, dataset_id, document_id, api_key)


if __name__ == "__main__":
    api_url = "http://x.x.x.x"  # 替换为你的 API URL
    dataset_id = ""  # 替换为你的知识库 ID
    api_key = ""  # 替换为你的 API 密钥
        
    ftp_dir_Prefix = "/AI/paper/HPC/"  # FTP 服务器目录前缀
    save_path = "/tmp/" # 保存 PDF 文件的本地路径
    limit = 1  # 每页返回的文档数量
    page_max = 38  # 最大页码限制
    page = 38  # 初始化页码
    while True:
        print(f"Fetching page {page}/{page_max}...")
        
        # 检查是否超过最大页码
        if page > page_max:
            print(f"Reached the maximum page limit ({page_max}). Exiting loop.")
            break
        
        # 获取当前页的文档列表
        document_ids, _ = get_documents(api_url, dataset_id, api_key, page=page, limit=limit)
        
        if not document_ids:
            print("No more documents to process. Exiting loop.")
            break
        
        # 处理当前页的文档
        batch_proc_documents(api_url, dataset_id, api_key, ftp_dir_Prefix, save_path, page=page, limit=limit, ftp_host="10.5.171.20", ftp_user="aiuser", ftp_password="0327*J329")
        
        # 如果返回的文档数量小于 limit，说明已经是最后一页
        if len(document_ids) < limit:
            print("Reached the last page. Exiting loop.")
            break
        
        # 增加页码，继续处理下一页
        page += 1
