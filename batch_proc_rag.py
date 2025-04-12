import requests
import re

def get_documents(api_url, dataset_id, api_key):
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
        "limit": 1,
        "page": 2
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

def batch_proc_documents(api_url, dataset_id, api_key):
    """
    批量删除指定知识库 ID 下的所有文档。

    :param api_url: API 的基础 URL
    :param dataset_id: 知识库 ID
    :param api_key: API 密钥
    """
    document_ids, document_names = get_documents(api_url, dataset_id, api_key)
    
    if not document_ids:
        print("No documents to delete.")
        return
    
    for document_id, document_name in zip(document_ids, document_names):
        segment_ids,contents = get_segments_and_content(api_url, dataset_id, document_id, api_key)
        print(f"Document_id is {document_id}. Document_name is {document_name}.")
        for segment_id, content in zip(segment_ids, contents):
            #print(f"Segment_id is {segment_id}. Content is {content}.")
            keywords = extract_fields(content)
            update_segment_keywords(api_url, dataset_id, document_id, segment_id, api_key, content, keywords)

        #delete_document(api_url, dataset_id, document_id, api_key)

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

if __name__ == "__main__":
    api_url = "http://x.x.x.x"
    dataset_id = ""  # 替换为你的知识库 ID
    api_key = ""  # 替换为你的 API 密钥
    
    batch_proc_documents(api_url, dataset_id, api_key)
