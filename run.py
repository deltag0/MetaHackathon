from app import create_app
from flask import send_from_directory
import os

app = create_app()

if os.environ.get("FLASK_DEBUG", "false").lower() == "true":
    @app.route("/test")
    def test_ui():
        return send_from_directory(os.path.dirname(__file__), "test.html")

if __name__ == "__main__":
    app.run(debug=True)
