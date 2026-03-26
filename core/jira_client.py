import requests
from typing import Optional, Dict, List
from core.auth import OAuth2Client

class JiraClient:
    def __init__(self):
        self.auth = OAuth2Client()
        self.base_url = self.auth.get_base_url()
        self.board_id = 1  # Board PC
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        url = f"{self.base_url}{endpoint}"
        headers = self.auth.get_headers()
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"❌ Erro HTTP {e.response.status_code}")
            return None
        except Exception:
            return None
    
    def search_issues(self, jql: str, max_results: int = 100, fields: str = None, page_token: str = None) -> Dict:
        """
        Busca issues usando JQL com suporte a paginação
        """
        endpoint = "/rest/api/3/search/jql"
        params = {"jql": jql, "maxResults": max_results}
        
        if fields:
            params["fields"] = fields
        
        if page_token:
            params["pageToken"] = page_token
        
        try:
            response_data = self._make_request(endpoint, params)
            if response_data and "issues" in response_data:
                for issue in response_data["issues"]:
                    if "fields" not in issue:
                        issue["fields"] = {}
                return response_data
            return {"issues": [], "isLast": True}
        except Exception:
            return {"issues": [], "isLast": True}
    
    def get_active_sprints_via_agile(self) -> List[Dict]:
        try:
            url = f"{self.base_url}/rest/agile/1.0/board/{self.board_id}/sprint"
            params = {"state": "active"}
            headers = self.auth.get_headers()
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("values", []) if data else []
        except Exception:
            return []
    
    def test_connection(self) -> bool:
        try:
            result = self.search_issues("project = PC", max_results=1)
            return result is not None
        except Exception:
            return False