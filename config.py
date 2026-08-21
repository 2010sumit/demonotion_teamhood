import os

# =====================================================================
# CONFIGURATION & SECRET MANAGEMENT SECTION
# =====================================================================
# This module loads environment variables and provides a single access point.
# DO NOT hardcode sensitive API keys or tokens in this file or any code files.
# All actual secrets must be stored in the .env file (which is ignored by Git).

def load_dotenv():
    """Loads environment variables from a local .env file if it exists."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip()
                        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                            val = val[1:-1]
                        os.environ[key] = val
        except Exception:
            pass

# Load environment variables automatically on import
load_dotenv()

# Retrieve credentials from environment with safe placeholders
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "your_openrouter_api_key_placeholder")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "your_notion_token_placeholder")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "your_notion_database_id_placeholder")
GOOGLE_PROJECT_ID = os.environ.get("GOOGLE_PROJECT_ID", "")
