from flask import render_template, request
from app import db 
from app.errors import bp 
from app.api.errors import error_response as api_error_response

def wants_json_response():
    return request.accept_mimetypes['application/json'] >= \
        request.accept_mimetypes['text/html']

@bp.app_errorhandler(404)
def not_found_error(error):
    if wants_json_response():
        return api_error_response(404)
    return render_template('errors/404.html'), 404 # render_template自动从templates文件夹下寻找模板

@bp.app_errorhandler(500)
def internal_error(error):
    # 数据库rollback回滚操作, 确保会话session提交前数据恢复到更改前的state
    # 防止失败的数据库会话干扰到模板触发的数据库访问.
    db.session.rollback()
    if wants_json_response():
        return api_error_response(500)
    return render_template('errors/500.html'), 500
