import ftplib
import os

from rich.console import Console

class FTPClient:
    """FTP客户端封装类
    
    提供FTP连接、文件上传和目录创建等操作的封装。
    自动处理UTF-8编码和目录创建。

    Attributes:
        host (str): FTP服务器地址
        user (str): 登录用户名
        password (str): 登录密码
        ftp (ftplib.FTP): FTP连接对象
        console (rich.console.Console): 控制台输出对象
    """
    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.password = password
        self.ftp = None
        self.console = Console()

    def connect(self):
        """连接到FTP服务器
        
        建立FTP连接并登录，设置被动模式为False，尝试启用UTF-8编码。
        
        Raises:
            ftplib.all_errors: 如果连接或登录失败
        """
        self.ftp = ftplib.FTP(self.host)
        self.ftp.login(self.user, self.password)
        self.ftp.set_pasv(False)
        # 启用UTF-8编码
        try:
            self.ftp.sendcmd('OPTS UTF8 ON')
        except ftplib.all_errors as e:
            self.console.log(f"Failed to enable UTF-8 encoding: {e}")

    def disconnect(self):
        """断开FTP连接
        
        安全关闭FTP连接，如果连接存在则调用quit()方法关闭。
        会自动将ftp属性设置为None。
        """
        if self.ftp:
            self.ftp.quit()
            self.ftp = None

    def upload_file(self, local_file_path, remote_file_path):
        """上传文件到FTP服务器
        
        自动创建远程目录(如果不存在)并上传文件，使用二进制模式传输。

        Args:
            local_file_path (str): 本地文件路径
            remote_file_path (str): 远程文件路径

        Raises:
            Exception: 如果上传过程中出现错误
            ConnectionError: 如果未连接到FTP服务器
        """
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
        """递归确保目录存在
        
        检查并递归创建目录路径中的所有不存在的目录。

        Args:
            path (str): 要确保存在的目录路径

        Raises:
            ftplib.error_perm: 如果目录创建失败
        """
        try:
            self.ftp.cwd(path)
        except ftplib.error_perm:
            # Directory does not exist, create it
            parent, directory = os.path.split(path)
            if parent and parent != '/':
                self.ensure_directory_exists(parent)
            self.ftp.mkd(directory)
            self.ftp.cwd(directory)
