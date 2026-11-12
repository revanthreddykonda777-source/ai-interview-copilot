"""Root entrypoint for AI Interview Copilot."""

import os
from backend.server import app

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode)


