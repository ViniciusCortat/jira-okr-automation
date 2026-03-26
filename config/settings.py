import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Settings:
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "data"
    DATA_DIR.mkdir(exist_ok=True)
    
    # OAuth 2.0 Credentials
    JIRA_CLIENT_ID = os.getenv("JIRA_CLIENT_ID")
    JIRA_CLIENT_SECRET = os.getenv("JIRA_CLIENT_SECRET")
    JIRA_CLOUD_ID = os.getenv("JIRA_CLOUD_ID")
    JIRA_BOARD_ID = int(os.getenv("JIRA_BOARD_ID", 1))
    
    # Domínio (para URL clássica)
    JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")  # ← ADICIONADO
    
    # Token pessoal (fallback)
    JIRA_EMAIL = os.getenv("JIRA_EMAIL")
    JIRA_TOKEN = os.getenv("JIRA_TOKEN")
    
    @classmethod
    def validate(cls):
        missing = []
        if not cls.JIRA_CLIENT_ID:
            missing.append("JIRA_CLIENT_ID")
        if not cls.JIRA_CLIENT_SECRET:
            missing.append("JIRA_CLIENT_SECRET")
        if not cls.JIRA_CLOUD_ID:
            missing.append("JIRA_CLOUD_ID")
        
        if missing:
            raise ValueError(f"Missing OAuth credentials: {', '.join(missing)}")