from app import create_app, db, cli
from app.models import User, Post, Comment, Notification, Message

app = create_app()
cli.register(app)

# shell_context_processor是shell上下文处理器, 运行flask shell命令自动调用被注册函数make_shell_context
@app.shell_context_processor
def make_shell_context():
    # 返回的必须是字典, 因为必须给在shell内部每一个被引用referenced的变量处提供名称
    return {'db': db, 'User': User, 'Post': Post, 'Comment': Comment, 'Notification': Notification, 'Message': Message}