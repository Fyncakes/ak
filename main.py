# main.py
import os
from dotenv import load_dotenv
load_dotenv()

from cakes import create_app

app = create_app()

if __name__ == '__main__':
    # For development, run with debug=True.
    # The production server (Gunicorn) will run this file without __main__.
    port = int(os.environ.get('FLASK_RUN_PORT', 5001))
    app.run(debug=True, port=port)