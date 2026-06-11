# PythonAnywhere WSGI configuration file
# This file contains the WSGI configuration required to serve up your
# web application at http://yourusername.pythonanywhere.com/

import sys
import os

# Add your project directory to the sys.path
project_home = '/home/yourusername/RMMV'  # <-- CHANGE 'yourusername' to your PythonAnywhere username
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set the working directory
os.chdir(project_home)

# Import your Flask app
from app import create_app
application = create_app()
