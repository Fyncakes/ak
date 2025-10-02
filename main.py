# main.py
from dotenv import load_dotenv
load_dotenv()

from cakes import create_app

app = create_app()

if __name__ == '__main__':
    # For development, run with debug=True.
    # The production server (Gunicorn) will run this file without __main__.
    app.run(debug=True)