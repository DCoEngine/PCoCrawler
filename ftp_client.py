import ftplib
import os

from rich.console import Console

class FTPClient:
    def __init__(self):
        self.host = "10.5.171.20"
        self.user = "aiuser"
        self.password = "0327*J329"
        self.ftp = None
        self.console = Console()

    def connect(self):
        self.ftp = ftplib.FTP(self.host)
        self.ftp.login(self.user, self.password)
        self.ftp.set_pasv(False)
        # 启用UTF-8编码
        try:
            self.ftp.sendcmd('OPTS UTF8 ON')
        except ftplib.all_errors as e:
            self.console.log(f"Failed to enable UTF-8 encoding: {e}")

    def disconnect(self):
        if self.ftp:
            self.ftp.quit()
            self.ftp = None

    def upload_file(self, local_file_path, remote_file_path):
        self.console.log(f"Attempting to upload {local_file_path} to {remote_file_path}")
        with open(local_file_path, 'rb') as file:
            try:
                self.create_directory_if_not_exists(os.path.dirname(remote_file_path))
                self.ftp.storbinary(f'STOR {remote_file_path}', file)
                self.console.log(f"Upload successful: {remote_file_path}")
            except Exception as e:
                self.console.log(f"Failed to upload: {e}")

    def create_directory_if_not_exists(self, directory_path):
        """
        创建目录，如果目录已存在则不创建
        :param directory_path: 要创建的目录路径
        """
        if not self.ftp:
            raise ConnectionError("Not connected to the FTP server")

        # 分割路径为各个子目录
        # directories = directory_path.split('/')
        # current_path = ''
        self.ensure_directory_exists(directory_path)
        print(f"Directory created: {directory_path}")
        # for directory in directories:
        #     if not directory:
        #         continue
        #     # 拼接路径并规范化
        #     current_path = os.path.normpath(os.path.join(current_path, directory))
    
        #     # 将路径中的分隔符转换为 /
        #     current_path = current_path.replace(os.sep, '/')
        #     #     # 尝试切换到目录，如果失败则创建目录
        #     #     self.ftp.cwd(current_path)
        #     # except ftplib.error_perm:
        #     #     # 目录不存在，创建目录
        #     #     self.ftp.mkd(current_path)
        #     #     print(f"Directory created: {current_path}")

    def ensure_directory_exists(self, path):
        try:
            self.ftp.cwd(path)
        except ftplib.error_perm:
            # Directory does not exist, create it
            parent, directory = os.path.split(path)
            if parent and parent != '/':
                self.ensure_directory_exists(parent)
            self.ftp.mkd(directory)
            self.ftp.cwd(directory)  