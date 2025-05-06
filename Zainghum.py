from flask import Flask, request, render_template_string, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from azure.storage.blob import BlobServiceClient, ContentSettings
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

app = Flask(__name__)
app.secret_key = 'b3e2f8a1c2d6432d874a8c57df4383f73a0e5b5a2c62dbf0a5f8b4c87c22c948'  # Required for session and flash
app.config['SQLALCHEMY_DATABASE_URI'] = (
    'mssql+pyodbc://UnitedKingdom:Kingdom123!%40%23@instadb.database.windows.net:1433/instadb'
    '?driver=ODBC+Driver+17+for+SQL+Server'
    '&Encrypt=yes'
    '&TrustServerCertificate=yes'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

AZURE_CONNECTION_STRING = 'DefaultEndpointsProtocol=https;AccountName=instastorage1;AccountKey=irm4Yz81XrcJQyZ7EY5GxIMUpEIlFxqssK1hEisrgwyz7OiVz/llIFUZWJx0mBBmO1dnUStf/ubD+AStA1VUaw==;EndpointSuffix=core.windows.net'
AZURE_CONTAINER_NAME = 'storage'

db = SQLAlchemy(app)
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
try:
    blob_service_client.create_container(AZURE_CONTAINER_NAME)
except Exception:
    pass


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(512), nullable=False)


class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    caption = db.Column(db.String(256), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    people_present = db.Column(db.String(256), nullable=True)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    file_path = db.Column(db.String(512), nullable=False)
    media_type = db.Column(db.String(20), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='media')
    ratings = db.relationship('Rating', backref='media')


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)


class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'media_id', name='unique_user_media_rating'),)


with app.app_context():
    db.create_all()


def include_template(template_string, **kwargs):
    return render_template_string(template_string, **kwargs)


base_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary-color: #4361ee;
            --secondary-color: #3f37c9;
            --bg-color: #f8f9fa;
            --text-color: #212529;
            --light-gray: #e9ecef;
            --dark-gray: #6c757d;
            --success: #4bb543;
            --danger: #dc3545;
            --card-bg: #ffffff;
            --shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            --radius: 8px;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
            padding: 0;
            margin: 0;
        }

        .container {
            width: 100%;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            background-color: var(--card-bg);
            box-shadow: var(--shadow);
            padding: 20px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            margin: 0;
            color: var(--primary-color);
            font-size: 24px;
            font-weight: 600;
        }

        .header-links {
            display: flex;
            gap: 15px;
        }

        .card {
            background-color: var(--card-bg);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            padding: 25px;
            margin-bottom: 20px;
        }

        .form-group {
            margin-bottom: 15px;
        }

        .form-control {
            width: 100%;
            padding: 12px;
            border: 1px solid var(--light-gray);
            border-radius: var(--radius);
            font-size: 16px;
            transition: border-color 0.3s;
        }

        .form-control:focus {
            border-color: var(--primary-color);
            outline: none;
        }

        .btn {
            display: inline-block;
            background-color: var(--primary-color);
            color: white;
            padding: 12px 20px;
            border: none;
            border-radius: var(--radius);
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            text-decoration: none;
            transition: background-color 0.3s;
        }

        .btn:hover {
            background-color: var(--secondary-color);
        }

        .btn-block {
            display: block;
            width: 100%;
        }

        .btn-secondary {
            background-color: var(--dark-gray);
        }

        .btn-secondary:hover {
            background-color: #5a6268;
        }

        a {
            color: var(--primary-color);
            text-decoration: none;
        }

        a:hover {
            text-decoration: underline;
        }

        .media-card {
            margin-bottom: 30px;
            border-radius: var(--radius);
            overflow: hidden;
        }

        .media-header {
            padding: 15px;
            background-color: var(--card-bg);
            border-bottom: 1px solid var(--light-gray);
        }

        .media-header h2 {
            margin: 0;
            font-size: 20px;
            font-weight: 600;
        }

        .media-body {
            padding: 15px;
            background-color: var(--card-bg);
        }

        .media-content {
            margin: 15px 0;
            display: flex;
            justify-content: center;
            align-items: center;
            background-color: black;
            overflow: hidden;
            border-radius: var(--radius);
        }

        .media-content video,
        .media-content img {
            max-width: 100%;
            height: auto;
            display: block;
        }

        .comments-section,
        .ratings-section {
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid var(--light-gray);
        }

        .comment-list,
        .rating-list {
            list-style: none;
            padding: 0;
            margin: 15px 0;
        }

        .comment-item,
        .rating-item {
            padding: 10px;
            background-color: var(--light-gray);
            border-radius: var(--radius);
            margin-bottom: 10px;
        }

        .flash-messages {
            margin-bottom: 20px;
        }

        .flash-message {
            padding: 12px;
            border-radius: var(--radius);
            margin-bottom: 10px;
        }

        .flash-success {
            background-color: var(--success);
            color: white;
        }

        .flash-danger {
            background-color: var(--danger);
            color: white;
        }

        .caption {
            color: var(--dark-gray);
            margin-bottom: 15px;
        }

        .meta-info {
            font-size: 14px;
            color: var(--dark-gray);
            margin-bottom: 15px;
        }

        .section-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
            color: var(--primary-color);
        }

        .star-rating {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .star-input {
            display: flex;
        }

        .star-input input[type="radio"] {
            display: none;
        }

        .star-input label {
            color: var(--light-gray);
            font-size: 24px;
            cursor: pointer;
        }

        .star-input input[type="radio"]:checked ~ label,
        .star-input label:hover ~ label,
        .star-input label:hover {
            color: gold;
        }

        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }

            .header {
                flex-direction: column;
                text-align: center;
            }

            .header-links {
                margin-top: 15px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ header_title }}</h1>
            <div class="header-links">
                {% if 'user_id' in session %}
                    <a href="{{ url_for('logout') }}" class="btn btn-secondary">Logout</a>
                {% else %}
                    <a href="{{ url_for('login') }}" class="btn">Login</a>
                    <a href="{{ url_for('register') }}" class="btn btn-secondary">Register</a>
                {% endif %}
            </div>
        </div>

        <div class="flash-messages">
            {% for category, message in get_flashed_messages(with_categories=true) %}
                <div class="flash-message flash-{{ category }}">{{ message }}</div>
            {% endfor %}
        </div>

        <div class="content">
            {{ include_template(content, url_for=url_for, session=session, get_creator_media=get_creator_media, get_average_rating=get_average_rating, get_user_rating=get_user_rating, media=media) | safe }}
        </div>
    </div>
</body>
</html>
'''


# Routes
@app.route('/')
def index():
    content = '''
    <div class="card">
        <h2 style="text-align: center; margin-bottom: 30px;">Share and Discover Amazing Content</h2>
        <div style="display: flex; justify-content: center; gap: 20px;">
            <a href="{{ url_for('login') }}" class="btn">Login</a>
            <a href="{{ url_for('register') }}" class="btn btn-secondary">Register</a>
        </div>
    </div>
    '''
    return render_template_string(
        base_template,
        title="Welcome",
        header_title="Media Share Platform",
        content=content,
        include_template=include_template
    )


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        hashed_password = generate_password_hash(password)
        user = User(username=username, email=email, role=role, password=hashed_password)
        try:
            db.session.add(user)
            db.session.commit()
            flash('Account created successfully!', 'success')
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash('Username or email already exists.', 'danger')

    content = '''
    <div class="card">
        <h2 style="margin-bottom: 20px;">Create an Account</h2>
        <form method="POST">
            <div class="form-group">
                <input type="text" name="username" class="form-control" placeholder="Username" required>
            </div>
            <div class="form-group">
                <input type="email" name="email" class="form-control" placeholder="Email" required>
            </div>
            <div class="form-group">
                <input type="password" name="password" class="form-control" placeholder="Password" required>
            </div>
            <div class="form-group">
                <select name="role" class="form-control" required>
                    <option value="">Select Role</option>
                    <option value="creator">Creator</option>
                    <option value="consumer">Consumer</option>
                </select>
            </div>
            <button type="submit" class="btn btn-block">Register</button>
        </form>
        <div style="text-align: center; margin-top: 20px;">
            <a href="{{ url_for('login') }}">Login</a>
        </div>
    </div>
    '''
    return render_template_string(
        base_template,
        title="Register",
        header_title="Create Account",
        content=content,
        include_template=include_template
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            session['username'] = user.username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    content = '''
    <div class="card">
        <h2 style="margin-bottom: 20px;">Log In</h2>
        <form method="POST">
            <div class="form-group">
                <input type="text" name="username" class="form-control" placeholder="Username" required>
            </div>
            <div class="form-group">
                <input type="password" name="password" class="form-control" placeholder="Password" required>
            </div>
            <button type="submit" class="btn btn-block">Login</button>
        </form>
        <div style="text-align: center; margin-top: 20px;">
            Don't have an account? <a href="{{ url_for('register') }}">Register</a>
        </div>
    </div>
    '''
    return render_template_string(
        base_template,
        title="Login",
        header_title="Login to Your Account",
        content=content,
        include_template=include_template
    )


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if session['role'] == 'creator':
        content = '''
        <div class="card">
            <h2 style="margin-bottom: 20px;">Upload New Media</h2>
            <form method="POST" action="{{ url_for('upload') }}" enctype="multipart/form-data">
                <div class="form-group">
                    <input type="text" name="title" class="form-control" placeholder="Title" required>
                </div>
                <div class="form-group">
                    <textarea name="caption" class="form-control" placeholder="Caption" rows="3"></textarea>
                </div>
                <div class="form-group">
                    <input type="text" name="location" class="form-control" placeholder="Location">
                </div>
                <div class="form-group">
                    <input type="text" name="people_present" class="form-control" placeholder="People Present (comma separated)">
                </div>
                <div class="form-group">
                    <label for="file">Select File:</label>
                    <input type="file" name="file" id="file" class="form-control" required>
                </div>
                <div class="form-group">
                    <select name="media_type" class="form-control" required>
                        <option value="">Select Media Type</option>
                        <option value="video">Video</option>
                        <option value="picture">Picture</option>
                    </select>
                </div>
                <button type="submit" class="btn btn-block

">Upload Media</button>
            </form>
        </div>

        <div class="card">
            <h2 style="margin-bottom: 20px;">Your Uploaded Media</h2>
            {% set creator_media = get_creator_media(session['user_id']) %}
            {% if creator_media %}
                {% for item in creator_media %}
                    <div class="media-card">
                        <div class="media-header">
                            <h2>{{ item.title | e }}</h2>
                        </div>
                        <div class="media-body">
                            <p class="caption">{{ item.caption | e }}</p>
                            <p class="meta-info">
                                {% if item.location %}Location: {{ item.location | e }}<br>{% endif %}
                                {% if item.people_present %}People: {{ item.people_present | e }}<br>{% endif %}
                                Uploaded: {{ item.upload_date.strftime('%Y-%m-%d %H:%M') }}
                            </p>

                            <div class="media-content">
                                {% if item.media_type == 'video' %}
                                    <video width="100%" controls>
                                        <source src="{{ item.file_path | e }}" type="video/mp4">
                                        Your browser does not support video playback.
                                    </video>
                                {% else %}
                                    <img src="{{ item.file_path | e }}" alt="{{ item.title | e }}">
                                {% endif %}
                            </div>

                            <div class="comments-section">
                                <h3 class="section-title">Comments ({{ item.comments|length }})</h3>
                                <ul class="comment-list">
                                    {% for comment in item.comments %}
                                        <li class="comment-item">{{ comment.text | e }}</li>
                                    {% endfor %}
                                    {% if not item.comments %}
                                        <li class="comment-item">No comments yet.</li>
                                    {% endif %}
                                </ul>
                            </div>

                            <div class="ratings-section">
                                <h3 class="section-title">Ratings ({{ item.ratings|length }})</h3>
                                <ul class="rating-list">
                                    {% for rating in item.ratings %}
                                        <li class="rating-item">{{ rating.value }}/5</li>
                                    {% endfor %}
                                    {% if not item.ratings %}
                                        <li class="rating-item">No ratings yet.</li>
                                    {% endif %}
                                </ul>
                                {% if item.ratings %}
                                    <p>Average Rating: {{ get_average_rating(item.ratings) }}/5</p>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                {% endfor %}
            {% else %}
                <p>You haven't uploaded any media yet.</p>
            {% endif %}
        </div>
        '''
    else:
        search_query = request.args.get('search', '')
        if search_query:
            media = Media.query.filter(Media.title.ilike(f'%{search_query}%')).options(
                joinedload(Media.comments),
                joinedload(Media.ratings)
            ).order_by(Media.upload_date.desc()).all()
        else:
            media = Media.query.options(
                joinedload(Media.comments),
                joinedload(Media.ratings)
            ).order_by(Media.upload_date.desc()).all()

        content = '''
        <div class="card">
            <h2 style="margin-bottom: 20px;">Discover Media</h2>
            <form method="GET" action="{{ url_for('dashboard') }}" style="margin-bottom: 20px;">
                <div class="form-group">
                    <input type="text" name="search" class="form-control" placeholder="Search by title..." value="{{ search_query | e }}">
                </div>
                <button type="submit" class="btn">Search</button>
            </form>

            {% if media %}
                {% for item in media %}
                    <div class="media-card">
                        <div class="media-header">
                            <h2>{{ item.title | e }}</h2>
                        </div>
                        <div class="media-body">
                            <p class="caption">{{ item.caption | e }}</p>
                            <p class="meta-info">
                                {% if item.location %}Location: {{ item.location | e }}<br>{% endif %}
                                {% if item.people_present %}People: {{ item.people_present | e }}<br>{% endif %}
                                Uploaded: {{ item.upload_date.strftime('%Y-%m-%d %H:%M') }}
                            </p>

                            <div class="media-content">
                                {% if item.media_type == 'video' %}
                                    <video width="100%" controls>
                                        <source src="{{ item.file_path | e }}" type="video/mp4">
                                        Your browser does not support video playback.
                                    </video>
                                {% else %}
                                    <img src="{{ item.file_path | e }}" alt="{{ item.title | e }}">
                                {% endif %}
                            </div>

                            <div class="comments-section">
                                <h3 class="section-title">Comments</h3>
                                <ul class="comment-list">
                                    {% for comment in item.comments %}
                                        <li class="comment-item">{{ comment.text | e }}</li>
                                    {% endfor %}
                                    {% if not item.comments %}
                                        <li class="comment-item">No comments yet.</li>
                                    {% endif %}
                                </ul>

                                <form method="POST" action="{{ url_for('comment') }}" style="margin-top: 15px;">
                                    <input type="hidden" name="media_id" value="{{ item.id }}">
                                    <div class="form-group">
                                        <input type="text" name="text" class="form-control" placeholder="Add a comment..." required>
                                    </div>
                                    <button type="submit" class="btn">Post Comment</button>
                    </form>
                            </div>

                            <div class="ratings-section">
                                <h3 class="section-title">Ratings</h3>

                                {% if item.ratings %}
                                    <p>Average Rating: {{ get_average_rating(item.ratings) }}/5 ({{ item.ratings|length }} ratings)</p>
                                {% else %}
                                    <p>No ratings yet.</p>
                                {% endif %}

                                {% set user_rating = get_user_rating(session['user_id'], item.id) %}
                                {% if user_rating %}
                                    <p>Your rating: {{ user_rating.value }}/5</p>
                                {% else %}
                                    <form method="POST" action="{{ url_for('rate') }}" style="margin-top: 15px;">
                                        <input type="hidden" name="media_id" value="{{ item.id }}">
                                        <div class="form-group">
                                            <div class="star-rating">
                                                <div class="star-input">
                                                    {% for i in range(5, 0, -1) %}
                                                        <input type="radio" id="star{{ i }}-{{ item.id }}" name="value" value="{{ i }}" required>
                                                        <label for="star{{ i }}-{{ item.id }}">★</label>
                                                    {% endfor %}
                                                </div>
                                                <button type="submit" class="btn">Rate</button>
                                            </div>
                                        </div>
                                    </form>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                {% endfor %}
            {% else %}
                <p>No media found{% if search_query %} for "{{ search_query | e }}"{% endif %}.</p>
            {% endif %}
        </div>
        '''

    def get_creator_media(creator_id):
        return Media.query.filter_by(creator_id=creator_id).options(
            joinedload(Media.comments),
            joinedload(Media.ratings)
        ).order_by(Media.upload_date.desc()).all()

    def get_average_rating(ratings):
        if not ratings:
            return 0
        total = sum(rating.value for rating in ratings)
        return round(total / len(ratings), 1)

    def get_user_rating(user_id, media_id):
        return Rating.query.filter_by(user_id=user_id, media_id=media_id).first()

    return render_template_string(
        base_template,
        title="Dashboard",
        header_title=f"Welcome, {session.get('username', 'User')}",
        content=content,
        get_creator_media=get_creator_media,
        get_average_rating=get_average_rating,
        get_user_rating=get_user_rating,
        media=media if session['role'] == 'consumer' else None,
        search_query=search_query if session['role'] == 'consumer' else '',
        include_template=include_template
    )


@app.route('/upload', methods=['POST'])
def upload():
    if 'user_id' not in session or session['role'] != 'creator':
        flash('You must be logged in as a creator to upload media.', 'danger')
        return redirect(url_for('login'))

    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('dashboard'))

    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('dashboard'))

    title = request.form.get('title')
    if not title:
        flash('Title is required', 'danger')
        return redirect(url_for('dashboard'))

    media_type = request.form.get('media_type')
    if not media_type or media_type not in ['video', 'picture']:
        flash('Valid media type is required', 'danger')
        return redirect(url_for('dashboard'))

    caption = request.form.get('caption', '')
    location = request.form.get('location', '')
    people_present = request.form.get('people_present', '')

    try:

        import uuid
        filename = f"{uuid.uuid4().hex}_{file.filename}"

        content_type = 'video/mp4' if media_type == 'video' else 'image/jpeg'
        if media_type == 'video' and not file.filename.lower().endswith(('.mp4', '.mov', '.avi', '.wmv')):
            flash('Only video files are allowed for video uploads.', 'danger')
            return redirect(url_for('dashboard'))
        elif media_type == 'picture' and not file.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
            flash('Only image files are allowed for picture uploads.', 'danger')
            return redirect(url_for('dashboard'))

        blob_client = blob_service_client.get_blob_client(container=AZURE_CONTAINER_NAME, blob=filename)
        blob_client.upload_blob(file, overwrite=True, content_settings=ContentSettings(content_type=content_type))
        blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{AZURE_CONTAINER_NAME}/{filename}"

        media = Media(
            title=title,
            caption=caption,
            location=location,
            people_present=people_present,
            file_path=blob_url,
            media_type=media_type,
            creator_id=session['user_id']
        )

        db.session.add(media)
        db.session.commit()
        flash('Media uploaded successfully!', 'success')

    except Exception as e:
        flash(f'Error uploading media: {str(e)}', 'danger')

    return redirect(url_for('dashboard'))


@app.route('/comment', methods=['POST'])
def comment():
    if 'user_id' not in session:
        flash('You must be logged in to comment.', 'danger')
        return redirect(url_for('login'))

    media_id = request.form.get('media_id')
    text = request.form.get('text')

    if not media_id or not text:
        flash('Media ID and comment text are required.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        media_id = int(media_id)
        media = Media.query.get(media_id)
        if not media:
            flash('Invalid media item.', 'danger')
            return redirect(url_for('dashboard'))

        comment = Comment(
            text=text,
            user_id=session['user_id'],
            media_id=media_id
        )

        db.session.add(comment)
        db.session.commit()
        flash('Comment added successfully!', 'success')

    except ValueError:
        flash('Invalid media ID.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding comment: {str(e)}', 'danger')

    return redirect(url_for('dashboard'))


@app.route('/rate', methods=['POST'])
def rate():
    if 'user_id' not in session:
        flash('You must be logged in to rate media.', 'danger')
        return redirect(url_for('login'))

    media_id = request.form.get('media_id')
    value = request.form.get('value')

    if not media_id or not value:
        flash('Media ID and rating value are required.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        media_id = int(media_id)
        value = int(value)

        if not 1 <= value <= 5:
            flash('Rating must be between 1 and 5.', 'danger')
            return redirect(url_for('dashboard'))

        media = Media.query.get(media_id)
        if not media:
            flash('Invalid media item.', 'danger')
            return redirect(url_for('dashboard'))

        existing_rating = Rating.query.filter_by(user_id=session['user_id'], media_id=media_id).first()
        if existing_rating:
            flash('You have already rated this media item.', 'warning')
            return redirect(url_for('dashboard'))

        rating = Rating(
            value=value,
            user_id=session['user_id'],
            media_id=media_id
        )

        db.session.add(rating)
        db.session.commit()
        flash('Rating submitted successfully!', 'success')

    except ValueError:
        flash('Invalid media ID or rating value.', 'danger')
    except IntegrityError:
        db.session.rollback()
        flash('You have already rated this media.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error submitting rating: {str(e)}', 'danger')

    return redirect(url_for('dashboard'))


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


@app.route('/404')
def page_not_found(e):
    content = '''
    <div class="card">
        <h2 style="text-align: center; margin-bottom: 20px;">Page Not Found</h2>
        <p style="text-align: center;">The page you are looking for doesn't exist.</p>
        <div style="text-align: center; margin-top: 20px;">
            <a href="{{ url_for('index') }}" class="btn">Go Home</a>
        </div>
    </div>
    '''
    return render_template_string(
        base_template,
        title="404 Not Found",
        header_title="Page Not Found",
        content=content,
        include_template=include_template
    ), 404


@app.errorhandler(500)
def server_error(e):
    content = '''
    <div class="card">
        <h2 style="text-align: center; margin-bottom: 20px;">Server Error</h2>
        <p style="text-align: center;">Something went wrong on our end. Please try again later.</p>
        <div style="text-align: center; margin-top: 20px;">
            <a href="{{ url_for('index') }}" class="btn">Go Home</a>
        </div>
    </div>
    '''
    return render_template_string(
        base_template,
        title="500 Server Error",
        header_title="Server Error",
        content=content,
        include_template=include_template
    ), 500


@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response


if __name__ == '__main__':
    app.run()