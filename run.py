import os

from app.routes import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3003))
    app.run(host="0.0.0.0", port=port, debug=True, threaded=True)
