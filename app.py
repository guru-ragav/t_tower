"""
Root entry point forwarding to tumble_tower/app.py
"""
import os
from tumble_tower.app import app, db

if __name__ == "__main__":
    db.init_db()
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=True)
