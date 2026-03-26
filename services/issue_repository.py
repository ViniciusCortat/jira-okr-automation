from typing import List, Dict, Tuple, Optional
from core.jira_client import JiraClient
from concurrent.futures import ThreadPoolExecutor, as_completed

class IssueRepository:
    """Responsável apenas por buscar issues via API"""
    
    def __init__(self, client: JiraClient):
        self.client = client
    
    def buscar_issues_da_sprint(self, sprint_id: int, projeto: str = "PC") -> Tuple[str, List[Dict]]:
        """Busca todas as issues de uma sprint de um projeto específico"""
        try:
            jql = f'project = "{projeto}" AND sprint = {sprint_id}'
            data = self.client.search_issues(jql, max_results=500, fields="key,status")
            return ("issues", data.get("issues", []) if data else [])
        except Exception:
            return ("issues", [])
    
    def contar_rejeitadas_na_sprint(self, sprint_id: int, projeto: str = "PC") -> Tuple[str, int]:
        """Conta tarefas rejeitadas em uma sprint de um projeto específico"""
        try:
            jql = f'project = "{projeto}" AND sprint = {sprint_id} AND status changed FROM "Validar" TO "Rejeitado da validação"'
            data = self.client.search_issues(jql, max_results=100, fields="key")
            return ("rejeitadas", len(data.get("issues", [])) if data else 0)
        except Exception:
            return ("rejeitadas", 0)
    
    def buscar_bugs_proatividade(self, projeto: str = "PC") -> Tuple[str, int]:
        """Busca bugs proatividade dos últimos 7 dias em um projeto"""
        try:
            from datetime import datetime, timedelta
            data_corte = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            reporter_id = "712020:e6f80390-5c4b-4d5f-bcbf-be6620f45767"
            jql = f'project = "{projeto}" AND created >= {data_corte} AND type = Hotfix AND reporter = {reporter_id}'
            data = self.client.search_issues(jql, max_results=100, fields="key")
            return ("bugs_proatividade", len(data.get("issues", [])) if data else 0)
        except Exception:
            return ("bugs_proatividade", 0)
    
    def buscar_bugs_reprovados(self, projeto: str = "PC") -> Tuple[str, int]:
        """Busca bugs reprovados no mês atual em um projeto"""
        try:
            from datetime import datetime
            primeiro_dia_mes = datetime.now().replace(day=1).strftime("%Y-%m-%d")
            jql = f'project = "{projeto}" AND status changed FROM "Validar" TO "Rejeitado da validação" AFTER {primeiro_dia_mes}'
            data = self.client.search_issues(jql, max_results=100, fields="key")
            return ("bugs_reprovados", len(data.get("issues", [])) if data else 0)
        except Exception:
            return ("bugs_reprovados", 0)
    
    def buscar_tudo_paralelo(self, sprint_ids: List[int], projeto: str = "PC") -> Dict:
        """Executa todas as buscas em paralelo para um projeto específico"""
        resultados = {
            "issues": [],
            "rejeitadas": [],
            "bugs_proatividade": 0,
            "bugs_reprovados": 0
        }
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            
            for sid in sprint_ids:
                futures.append(executor.submit(self.buscar_issues_da_sprint, sid, projeto))
                futures.append(executor.submit(self.contar_rejeitadas_na_sprint, sid, projeto))
            
            futures.append(executor.submit(self.buscar_bugs_proatividade, projeto))
            futures.append(executor.submit(self.buscar_bugs_reprovados, projeto))
            
            for future in as_completed(futures):
                try:
                    identificador, valor = future.result()
                    
                    if identificador == "issues":
                        resultados["issues"].extend(valor)
                    elif identificador == "rejeitadas":
                        resultados["rejeitadas"].append(valor)
                    elif identificador == "bugs_proatividade":
                        resultados["bugs_proatividade"] = valor
                    elif identificador == "bugs_reprovados":
                        resultados["bugs_reprovados"] = valor
                        
                except Exception:
                    continue
        
        return resultados