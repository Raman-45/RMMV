"""
RMMV Dashboard — Application Configuration
============================================
Central configuration for the Flask application.
Uses a class-based config pattern for easy environment switching.
"""

import os

# Base directory of the project (where this file lives)
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration class for the RMMV application."""

    # --- Security -----------------------------------------------------------
    SECRET_KEY = 'rmmv-dev-secret-key-change-in-production'

    # --- Database ------------------------------------------------------------
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'instance', 'rmmv.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- File Uploads --------------------------------------------------------
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov'}
