from flask import Flask, render_template, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_moment import Moment
from werkzeug.security import generate_password_hash,check_password_hash
from flask_migrate import Migrate

app = Flask(__name__)
moment = Moment(app)
app.config['SECRET_KEY'] = 'thisissecret'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///db.db"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login_page"

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# DEFINE Blog model
class Blog(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String(200), nullable = False)
    body = db.Column(db.String, nullable = False)
    author = db.Column(db.String(20), nullable = False)
    created_date = db.Column(db.DateTime, server_default = db.func.now())
    view_count = db.Column(db.Integer, default=0)

# DEFINE MODEL user
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key = True)
    email = db.Column(db.String(255), nullable = False, unique = True)
    username = db.Column(db.String(255), nullable = False, unique = True)
    password = db.Column(db.String(255), nullable=False, unique = False)
    liked_posts = db.relationship("Blog", secondary="likes", backref="likes", lazy=True)

    def set_password(self, password):
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)

# DEFINE MODEL comments
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    body = db.Column(db.String, nullable = False)
    post_id = db.Column(db.Integer, nullable = False)
    author = db.Column(db.String, nullable = False)
    created_at = db.Column(db.DateTime, server_default = db.func.now())

likes = db.Table('likes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('post_id', db.Integer, db.ForeignKey('blog.id'), primary_key=True)
)

db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route('/', methods=["GET","POST"])
@login_required
def root():
    if request.method == "POST":
        form_data = Blog(title = request.form['title'],
                        body = request.form['description'],
                        author = current_user.username)
        db.session.add(form_data)
        db.session.commit()
        return redirect(url_for("root"))
    if not current_user.is_anonymous:
        posts = Blog.query.order_by(Blog.created_date.desc()).all()
        for i in posts:
            i.comments = Comment.query.filter_by(post_id = i.id).all()
        
        return render_template("./view/logged_in.html", posts = posts)
    else:
        return render_template("index.html")

@app.route('/login', methods=["GET", "POST"])
def login_page():
    if current_user.is_anonymous:
        print("redirect login")
    elif current_user.is_authenticated:
        return redirect(url_for("root"))
    if request.method == "POST":
        user = User.query.filter_by(email = request.form['email']).first()
        if not user:
            flash("Email or password incorrect", "danger")
        else:
            if user.check_password(request.form['password']):
                print("user logged in", user.username)
                login_user(user)
                return redirect(url_for("root"))
            
    return render_template("./ultilities/login.html")

@app.route('/signup', methods=["GET", "POST"])
def signup_page():
    if current_user.is_authenticated:
        return redirect(url_for("root"))
    if request.method == "POST":
        check_user = User.query.filter_by(email = request.form['email']).first()
        if not check_user:
            new_user = User(
                username = request.form['username'],
                email = request.form['email']
            )
            new_user.set_password(request.form['password'])
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for("login_page"))
        else:
            flash("This email is used, please use another email", "warning")
        
    return render_template("./ultilities/signup.html")

@app.route("/posts")
@login_required
def post_page():
    posts = Blog.query.order_by(Blog.created_date.desc()).all()
    print("get posts", posts)
    return render_template("./view/view_post.html", posts = posts)

@app.route("/post/<id>", methods=["GET","POST"])
@login_required
def page_detail(id): 
    print("idddd", id)
    action = request.args.get('action')
    blog = Blog.query.filter_by(id = id).first()
    blog.view_count = blog.view_count + 1
    db.session.add(blog)
    db.session.commit()
    comments = Comment.query.filter_by(post_id = id).all()
    print("comments length", len(comments))
    if request.method == "POST":
        if action == "edit":
            return render_template("./view/view_post_detail.html", post = blog, action = action)
        elif action == "update":
            blog.title = request.form['title']
            blog.body = request.form['body']
            db.session.commit()
            return redirect(url_for('page_detail', id=id))
        elif action == "comment":
            comment = Comment()
            comment.body = request.form['body']
            comment.author = current_user.username
            comment.post_id = id
            db.session.add(comment)
            db.session.commit()
            return redirect(url_for('page_detail', id=id))
        elif action == "delete_comment":
            comment = Comment.query.filter_by(id = request.form['comment-id']).first()
            db.session.delete(comment)
            db.session.commit()
            print("delte comment", request.form['comment-id'])
            return redirect(url_for("page_detail", id=id))
        elif action == "delete_post":
            db.session.delete(blog)
            db.session.commit()
            return redirect(url_for("root"))
        elif action == "liked_post":
            current_user.liked_posts.append(blog)
            db.session.commit()
            return redirect(url_for('page_detail', id=id))
        elif action == "unliked_post":
            print("khoa", current_user)
            print("khoa mini", blog)
            current_user.liked_posts.remove(blog)
            db.session.commit()
            return redirect(url_for('page_detail', id=id))
    return render_template("./view/view_post_detail.html", post = blog, comments = comments)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("root"))


# Root for POST ( post a post and load post )

if __name__ == "__main__":
    app.run(debug=True)