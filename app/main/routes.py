from flask import render_template, flash, redirect, url_for, request, g, jsonify, current_app, request 
from app import db
from flask_login import current_user, login_required
from app.models import User, Post, Comment, Message, Notification
from app.translate import translate 
from app.main.forms import EditProfileForm, EmptyForm, PostForm, SearchForm, CommentForm, FileForm, DeletePostForm, MessageForm, DeleteCommentForm
from flask_babel import _ # _ is gettext() function as a convention
from flask_babel import get_locale
from guess_language import guess_language 
from app.main import bp 
from werkzeug.utils import secure_filename 
from flask import send_from_directory
from datetime import datetime 
from celery import shared_task
from celery.result import AsyncResult
import os 

@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        g.search_form = SearchForm() # search should be rendered before request ends, g's lifetime persists through the life of a request
    g.locale = str(get_locale()) # moment.js library is independent of templates or source code, so it is a must to embed it before request 

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        language = guess_language(form.post.data) # 帖子发布提交时检测帖子文本使用语言
        if language == 'UNKNOWN' or len(language) > 5: # language code like 'zh-tw'
            language = ''
        post = Post(body=form.post.data, author=current_user, language=language)
        db.session.add(post)
        db.session.commit()
        flash(_('Your post is now live!'))
        return redirect(url_for('main.index')) # 重定向避免当令浏览器返回上一个表单页面时, 浏览器发现post请求一样时会提示重新提交表单页面的. redirect使其为get请求
    page = request.args.get('page', 1, type=int)
    posts = current_user.followed_posts().paginate(
        page=page, per_page=current_app.config['POSTS_PER_PAGE'], error_out=False)
    next_url = url_for('main.index', page=posts.next_num) \
        if posts.has_next else None 
    prev_url = url_for('main.index', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title=_('Home'), posts=posts.items, form=form, # post returned from Paginate() is a pagination object of pagination class
                            next_url=next_url, prev_url=prev_url)  # whose attribute itmes contains a list of items in the request.
                                                                                    
@bp.route('/explore')
@login_required 
def explore():
    form = DeletePostForm()
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page=page, per_page=current_app.config['POSTS_PER_PAGE'], error_out=False)
    next_url = url_for('main.explore', page=posts.next_num) \
        if posts.has_next else None 
    prev_url = url_for('main.explore', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('explore.html', title=_('Explore'), posts=posts.items,
                            next_url=next_url, prev_url=prev_url, form=form)

@bp.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404() # first_or_404返回第一条查询记录, 否则返回404错误相应
    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page=page, per_page=current_app.config['POSTS_PER_PAGE'], error_out=False)
    next_url = url_for('main.user', username=username, page=posts.next_num) \
        if posts.has_next else None 
    prev_url = url_for('main.user', username=username, page=posts.prev_num) \
        if posts.has_prev else None 
    form = EmptyForm()
    return render_template('user.html', user=user, posts=posts.items, form=form,
                            next_url=next_url, prev_url=prev_url)

@shared_task(ignore_result=False)
@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required 
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data # 保存当前用户更改的用户名
        current_user.about_me = form.about_me.data # 保存当前用户更改的介绍信息
        db.session.commit() # 因为current_user变量是从数据库中获取的用户, 所以不用db.session.add()
        flash(_('Your changes have been saved.'))
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET': 
        form.username.data = current_user.username # 确保错误GET请求下表单数据至少不被更改
        form.about_me.data = current_user.about_me 
    return render_template('edit_profile.html', title=_('Edit Profile'), form=form)

@bp.post('/edit_profile')
def start_edit():
    a = request.form.get("a", type=int)
    b = request.form.get("b", type=int)
    result = edit_profile.delay(a, b)
    return {"result_id": result.id}

@bp.get('/result/<id>')
def take_result(id):
    result = AsyncResult(id)
    return {
        "ready": result.ready(),
        "successful": result.successful(),
        "value": result.result if result.ready() else None,
    }


@bp.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first() # search for special user to follow by quering username 
        if user is None: # if such user does not exist, return index page
            flash(_('User %(username)s not found', username=username))
            return redirect(url_for('main.index'))
        if  user ==  current_user:
            flash(_("You can't follow yourself!"))
            return redirect(url_for('main.user', username=username))
        current_user.follow(user)
        db.session.commit()
        flash(_('You are following %(username)s now', username=username))
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))

@bp.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash(_('User %(username)s not found', username=username))
            return redirect(url_for('main.index'))
        if user == current_user:
            flash(_("You can't unfollow yourself!"))
            return redirect(url_for('main.user', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash(_("You are not following %(username)s now", username=username))
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))

@bp.route('/translate', methods=['POST'])
@login_required
def translate_text():
    return jsonify({'text': translate(request.form['text'], 
                                      request.form['source_language'],
                                      request.form['dest_language'])})

@bp.route('/search')
@login_required
def search():
    if not g.search_form.validate(): # form.validate_on_submit() words under post request, form.validate ignores how form data was submitted
        flash(_('empty input'))
        return redirect(url_for('main.explore'))
    flash(_('valid input'))
    form = DeletePostForm()
    page = request.args.get('page', 1, type=int)
    posts, total = Post.search(g.search_form.q.data, page,
                                current_app.config['POSTS_PER_PAGE'])
    next_url = url_for('main.search', q=g.search_form.q.data, page=page + 1) \
        if total > page * current_app.config['POSTS_PER_PAGE'] else None # total:= {'value': nums, 'relation': eq}
    prev_url = url_for('main.search', q=g.search_form.q.data, page=page - 1) \
        if page > 1 else None 
    return render_template('search.html', title=_('Search'), posts=posts,
                            next_url=next_url, prev_url=prev_url, form=form)

@shared_task(ignore_result=False)
@bp.route('/post/<int:id>', methods=['GET', 'POST'])
@login_required
def comment(id):
    post = Post.query.get_or_404(id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data, post=post, author=current_user._get_current_object())
        db.session.add(comment)
        db.session.commit()
        flash(_('Your comment has been published.'))
        return redirect(url_for('main.comment', id=post.id))
    page = request.args.get('page', 1, type=int)
    comments = post.comments.order_by(Comment.timestamp.desc()).paginate(
            page=page, per_page=current_app.config['COMMENTS_PER_PAGE'], error_out=False)
    return render_template('comment.html', post=post, comments=comments.items, form=form)

@shared_task(ignore_result=False)
@bp.route('/comment/<int:id>/delete', methods=['GET', 'POST'])
@login_required
def delete_comment(id):
    form = DeleteCommentForm()
    comment = Comment.query.get_or_404(id)
    if form.validate_on_submit():
        db.session.delete(comment)
        db.session.commit()
        flash(_('Comment deleted.'))
        return redirect(url_for('main.comment', id=comment.post_id))
    return render_template('_post.html', form=form)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']
    
@bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    current_app.config['UPLOAD_FOLDER'] = "/home/JTPing/upload_folder"
    form = FileForm()
    if form.validate_on_submit():
        f = form.file.data 
        if f and allowed_file(f.filename):
            filename = secure_filename(f.filename)
            f.save(os.path.join(
                current_app.config['UPLOAD_FOLDER'], filename
            ))
            flash(_('file uploaded successfully!'))
            return redirect(url_for('main.index'))
    files = os.listdir(current_app.config['UPLOAD_FOLDER'])
    return render_template('upload.html', form=form, files=files)

@bp.route('/upload/<name>')
@login_required
def download_file(name):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], name)

@shared_task(ignore_result=False)
@bp.route('/post/<int:id>/delete', methods=['POST'])
@login_required
def delete_post(id):
    form = DeletePostForm()
    post = Post.query.get_or_404(id)
    if form.validate_on_submit():
        db.session.delete(post)
        db.session.commit()
        flash(_('Post deleted.'))
        return redirect(url_for('main.index'))
    return render_template('_post.html', form=form)

@shared_task(ignore_result=False)
@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required 
def edit_post(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author:
        flash(_('Sorry, you can only edit your own post.'))
        return redirect(url_for('main.index'))
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.post.data
        db.session.add(post)
        db.session.commit()
        flash(_('The post has been updated.'))
        render_template('_post.html', form=form, post=post)
        return redirect(url_for('main.index'))
    form.post.data = post.body
    return render_template('edit_post.html', form=form)

@bp.route('/user/<username>/popup')
@login_required
def user_popup(username):
    user = User.query.filter_by(username=username).first_or_404()
    form = EmptyForm()
    return render_template('user_popup.html', user=user, form=form)

@bp.route('/send_message/<recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
    user = User.query.filter_by(username=recipient).first_or_404()
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(author=current_user, recipient=user, body=form.message.data)
        db.session.add(msg)
        user.add_notification('unread_message_count', user.new_messages())
        db.session.commit()
        flash(_('Your message has been sent.'))
        return redirect(url_for('main.user', username=recipient))
    return render_template('send_message.html', title=_('Send Message'), form=form, recipient=recipient)

@bp.route('/messages')
@login_required 
def messages():
    current_user.last_message_read_time = datetime.utcnow() # mark all messages as read 
    current_user.add_notification('unread_message_count', 0)
    db.session.commit()
    page = request.args.get('page', 1, type=int)
    messages = current_user.messages_received.order_by(
        Message.timestamp.desc()).paginate(
            page=page, per_page=current_app.config['POSTS_PER_PAGE'], error_out=False)
    next_url = url_for('main.messages', page=messages.next_num) \
        if messages.has_next else None 
    prev_url = url_for('main.messages', page=messages.prev_num) \
        if messages.has_prev else None 
    return render_template('messages.html', messages=messages.items, next_url=next_url, prev_url=prev_url) 

@bp.route('/notifications')
@login_required
def notifications():
    since = request.args.get('since', 0.0, type=float)
    notifications = current_user.notifications.filter(
        Notification.timestamp > since).order_by(Notification.timestamp.desc())
    return jsonify([{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
    } for n in notifications])




   














