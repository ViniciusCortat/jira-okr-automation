import requests
import time
from typing import Optional, Dict
from config.settings import Settings

class OAuth2Client:
    TOKEN_URL = "https://auth.atlassian.com/oauth/token"
    
    def __init__(self):
        self.client_id = Settings.JIRA_CLIENT_ID
        self.client_secret = Settings.JIRA_CLIENT_SECRET
        self.cloud_id = Settings.JIRA_CLOUD_ID
        self.access_token: Optional[str] = None
        self.token_expires_at: float = 0
    
    def get_access_token(self) -> str:
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token
        return self._request_new_token()
    
    def _request_new_token(self) -> str:
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": "api.atlassian.com"
        }
        
        try:
            response = requests.post(self.TOKEN_URL, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            self.access_token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            self.token_expires_at = time.time() + expires_in - 60
            
            return self.access_token
            
        except Exception as e:
            print(f"❌ Erro ao obter token: {e}")
            raise
    
    def get_headers(self) -> Dict:
        token = self.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
    
    def get_base_url(self) -> str:
        return f"https://api.atlassian.com/ex/jira/{self.cloud_id}"