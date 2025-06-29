# Instagram-like Sentiment Analyzer

This is a full-featured Instagram-like web app built with Flask. Users can register, log in, upload image posts with captions, comment, like, and view a feed. Sentiment analysis is performed on captions and comments, displaying the result beside each.

## Features
- User authentication (register, login, logout)
- User profiles
- Image uploads for posts
- Feed showing all posts
- Comments and likes on posts
- Sentiment analysis for captions and comments (with emoji and score)
- SQLite database (via SQLAlchemy)
- Modern, responsive UI

## Setup
1. Clone the repository or copy the files to your project directory.
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the app:
   ```
   python app.py
   ```
4. Visit [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

## Project Structure
- `app.py` — Main Flask application
- `templates/` — HTML templates
- `static/` — Static files (images, CSS, JS)
- `requirements.txt` — Python dependencies
- `README.md` — This file

## Notes
- Images are stored in `static/images/`.
- The database is `app.db` (SQLite).
- Sentiment analysis uses TextBlob.

---

Feel free to customize and extend the app! #   I n s t a S e n  
 