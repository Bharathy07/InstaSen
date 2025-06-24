from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, send_from_directory
from flask_login import login_required, current_user, logout_user
from werkzeug.utils import secure_filename
from models import db, User, Post, Comment, Like, Notification, Follow, Message
from textblob import TextBlob
import os
import uuid
from sqlalchemy import or_, and_

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def feed():
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    return render_template('feed.html', posts=posts)

@main_bp.route('/post', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        image = request.files.get('image')
        caption = request.form.get('caption')
        if not image:
            flash('Image is required!')
            return redirect(url_for('main.create_post'))
        filename = secure_filename(f"{uuid.uuid4().hex}_{image.filename}")
        image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        sentiment, score = analyze_sentiment(caption)
        post = Post(image_filename=filename, caption=caption, sentiment=sentiment, sentiment_score=score, author=current_user)
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('main.feed'))
    return render_template('create_post.html')

@main_bp.route('/post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    if request.method == 'POST':
        content = request.form.get('content')
        if content:
            sentiment, score = analyze_sentiment(content)
            comment = Comment(content=content, sentiment=sentiment, sentiment_score=score, author=current_user, post=post)
            db.session.add(comment)
            db.session.commit()
            # Notification for comment
            if post.author.id != current_user.id:
                notif = Notification(user_id=post.author.id, message=f"{current_user.username} commented on your post.")
                db.session.add(notif)
                db.session.commit()
            return redirect(url_for('main.post_detail', post_id=post_id))
    return render_template('post_detail.html', post=post)

@main_bp.route('/delete_comment/<int:comment_id>/<int:post_id>', methods=['POST'])
@login_required
def delete_comment(comment_id, post_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.user_id == current_user.id:
        db.session.delete(comment)
        db.session.commit()
        flash('Comment deleted.')
    else:
        flash('You can only delete your own comments.')
    return redirect(url_for('main.post_detail', post_id=post_id))

@main_bp.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    if like:
        db.session.delete(like)
    else:
        db.session.add(Like(user_id=current_user.id, post_id=post_id))
        # Notification for like
        if post.author.id != current_user.id:
            notif = Notification(user_id=post.author.id, message=f"{current_user.username} liked your post.")
            db.session.add(notif)
    db.session.commit()
    return redirect(request.referrer or url_for('main.feed'))

@main_bp.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user.id == current_user.id:
        flash('You cannot follow yourself.')
    elif not any(f.followed_id == user.id for f in current_user.followed):
        f = Follow(follower_id=current_user.id, followed_id=user.id)
        db.session.add(f)
        db.session.commit()
        flash(f'You are now following {user.username}.')
    return redirect(url_for('main.profile', username=username))

@main_bp.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first_or_404()
    f = Follow.query.filter_by(follower_id=current_user.id, followed_id=user.id).first()
    if f:
        db.session.delete(f)
        db.session.commit()
        flash(f'You have unfollowed {user.username}.')
    return redirect(url_for('main.profile', username=username))

@main_bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    results = []
    query = ''
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        if query:
            results = User.query.filter(User.username.ilike(f'%{query}%')).all()
    return render_template('search.html', results=results, query=query)

@main_bp.route('/user/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(user_id=user.id).order_by(Post.timestamp.desc()).all()
    is_following = False
    if user.id != current_user.id:
        is_following = Follow.query.filter_by(follower_id=current_user.id, followed_id=user.id).first() is not None
    follower_count = user.followers.count()
    following_count = user.followed.count()
    return render_template('profile.html', user=user, posts=posts, is_following=is_following, follower_count=follower_count, following_count=following_count)

@main_bp.route('/notifications')
@login_required
def notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).all()
    # Mark all as read
    for notif in notifs:
        notif.is_read = True
    db.session.commit()
    return render_template('notifications.html', notifications=notifs)

@main_bp.route('/delete_profile', methods=['POST'])
@login_required
def delete_profile():
    user = current_user
    # Delete all related data
    from models import Post, Comment, Like, Follow, Notification
    # Delete likes by user
    Like.query.filter_by(user_id=user.id).delete()
    # Delete comments by user
    Comment.query.filter_by(user_id=user.id).delete()
    # Delete posts by user (and their likes/comments)
    posts = Post.query.filter_by(user_id=user.id).all()
    for post in posts:
        Like.query.filter_by(post_id=post.id).delete()
        Comment.query.filter_by(post_id=post.id).delete()
        db.session.delete(post)
    # Delete follows (as follower and followed)
    Follow.query.filter_by(follower_id=user.id).delete()
    Follow.query.filter_by(followed_id=user.id).delete()
    # Delete notifications for user
    Notification.query.filter_by(user_id=user.id).delete()
    # Delete user
    db.session.delete(user)
    db.session.commit()
    logout_user()
    flash('Your profile and all related data have been deleted.')
    return redirect(url_for('auth.register'))

@main_bp.route('/messages')
@login_required
def messages_inbox():
    from models import Message
    # Get all users who have messaged with current user
    user_ids = set()
    for m in Message.query.filter(or_(Message.sender_id==current_user.id, Message.recipient_id==current_user.id)).all():
        user_ids.add(m.sender_id)
        user_ids.add(m.recipient_id)
    user_ids.discard(current_user.id)
    users = User.query.filter(User.id.in_(user_ids)).all() if user_ids else []
    return render_template('messages_inbox.html', users=users, Message=Message)

@main_bp.route('/messages/<username>', methods=['GET', 'POST'])
@login_required
def conversation(username):
    other = User.query.filter_by(username=username).first_or_404()
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if content:
            msg = Message(sender_id=current_user.id, recipient_id=other.id, content=content)
            db.session.add(msg)
            db.session.commit()
    # Mark all received messages as read
    Message.query.filter_by(sender_id=other.id, recipient_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    # Get all messages between users
    messages = Message.query.filter(
        or_(
            and_(Message.sender_id==current_user.id, Message.recipient_id==other.id),
            and_(Message.sender_id==other.id, Message.recipient_id==current_user.id)
        )
    ).order_by(Message.timestamp.asc()).all()
    return render_template('conversation.html', other=other, messages=messages)

@main_bp.route('/upload_profile_image', methods=['POST'], endpoint='upload_profile_image')
@login_required
def upload_profile_image():
    image = request.files.get('profile_image')
    if not image:
        flash('No image selected!')
        return redirect(url_for('main.profile', username=current_user.username))
    filename = secure_filename(f"profile_{current_user.id}_{uuid.uuid4().hex}_{image.filename}")
    image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
    current_user.profile_image = filename
    db.session.commit()
    flash('Profile image updated!')
    return redirect(url_for('main.profile', username=current_user.username))

def analyze_sentiment(text):
    if not text:
        return 'Neutral', 0.0
    analysis = TextBlob(text)
    polarity = round(analysis.sentiment.polarity, 3)
    if polarity > 0:
        sentiment = 'Positive'
    elif polarity < 0:
        sentiment = 'Negative'
    else:
        sentiment = 'Neutral'
    return sentiment, polarity 