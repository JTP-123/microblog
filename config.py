import os 
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config():
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, os.environ.get('DATABASE_FILE', 'data.db'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False 
    # 配置email
    MAIL_SERVER = os.environ.get('MAIL_SERVER') 
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 465) # qq邮箱端口为465或者587
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL') is not None # 邮件安全协议为True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') # 邮件用户名
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') # 邮箱SMTP协议授权码
    ADMINS = ['1732813001@qq.com'] # toaddrs:= a list of strings
    POSTS_PER_PAGE = 25
    COMMENTS_PER_PAGE = 30
    LANGUAGES = ['en', 'zh', 'ja']
    MS_TRANSLATOR_KEY = os.environ.get('MS_TRANSLATOR_KEY')
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')
    UPLOAD_FOLDER = r'C:\Users\sky\Documents\UpLoad' # 上传文件路径
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'} # 允许的文件后缀名
    MAX_CONTENT_LENGTH = 16 * 1000 * 1000 # 上传文件大小
