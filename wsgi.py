"""
RMMV Dashboard — WSGI Entry Point
=================================
This file is the entry point for production WSGI servers like PythonAnywhere,
gunicorn, or waitress. It instantiates the Flask application.
"""

from app import create_app

application = create_app()
app = application  # Reference alias for compatibility

if __name__ == '__main__':
    # Fallback to run locally if executed directly
    application.run(debug=True, port=5000)
