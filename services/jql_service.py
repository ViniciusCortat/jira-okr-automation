from typing import List, Dict, Optional
from core.jira_client import JiraClient
from datetime import datetime, timedelta
import requests
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed


class JQLService:
    def __init__(self):
        self.client = JiraClient()
        self._cache = {}
        self._changelog_cache = {}
        self._sprint_ids = []
        self._sprint_names = []
        self._sprint_info = []
    
    # ===== SPRINTS =====
    
    def _load_active_sprints(self):
        if not self._sprint_ids:
            sprints = self.client.get_active_sprints_via_agile()
            if sprints:
                self._sprint_ids = [s["id"] for s in sprints if s.get("id")]
                self._sprint_names = [s["name"] for s in sprints if s.get("name")]
                self._sprint_info = sprints
    
    def get_active_sprints_info(self) -> List[Dict]:
        self._load_active_sprints()
        return self._sprint_info
    
    def get_sprint_names(self) -> List[str]:
        self._load_active_sprints()
        return self._sprint_names
    
    def get_primeiro_nome_sprint(self) -> str:
        nomes = self.get_sprint_names()
        return nomes[0] if nomes else "Sprint Desconhecida"
    
    def get_sprint_ids(self) -> List[int]:
        self._load_active_sprints()
        return self._sprint_ids
    
    def get_issues_from_sprints(self) -> List[Dict]:
        sprint_ids = self.get_sprint_ids()
        if not sprint_ids:
            return []
        
        all_issues = []
        for sprint_id in sprint_ids:
            try:
                jql = f'sprint = {sprint_id}'
                data = self.client.search_issues(jql, max_results=500, fields="key,status")
                issues = data.get("issues", [])
                all_issues.extend(issues)
            except Exception:
                continue
        return all_issues
    
    def get_changelog(self, issue_key: str) -> List[Dict]:
        if issue_key in self._changelog_cache:
            return self._changelog_cache[issue_key]
        
        try:
            url = f"{self.client.base_url}/rest/api/3/issue/{issue_key}/changelog"
            headers = self.client.auth.get_headers()
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                changelog = response.json().get("values", [])
                self._changelog_cache[issue_key] = changelog
                return changelog
        except Exception:
            pass
        return []
    
    # ===== RELEASES =====
    
    def get_all_releases(self, projeto: str = "PC") -> List[Dict]:
        cache_key = f"releases_{projeto}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            url = f"{self.client.base_url}/rest/api/3/project/{projeto}/versions"
            headers = self.client.auth.get_headers()
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                versions = response.json()
                releases = [v for v in versions if not v.get('archived', False)]
                self._cache[cache_key] = releases
                return releases
        except Exception:
            pass
        return []
    
    def get_releases_semana_atual(self, projeto: str = "PC") -> List[Dict]:
        releases = self.get_all_releases(projeto)
        
        hoje = datetime.now()
        dias_para_segunda = hoje.weekday()
        segunda = (hoje - timedelta(days=dias_para_segunda)).replace(hour=0, minute=0, second=0)
        domingo = (segunda + timedelta(days=6)).replace(hour=23, minute=59, second=59)
        
        result = []
        for r in releases:
            release_date = r.get('releaseDate')
            if release_date and r.get('released', False):
                try:
                    data_release = datetime.strptime(release_date, "%Y-%m-%d")
                    if segunda <= data_release <= domingo:
                        result.append(r)
                except:
                    pass
        return result
    
    # ===== OKRs RESTAURADOS =====
    
    def get_rejected_tasks_count(self) -> int:
        """Conta tarefas rejeitadas na sprint atual"""
        issues = self.get_issues_from_sprints()
        rejected = 0
        for issue in issues:
            status = issue["fields"].get("status", {}).get("name", "").lower()
            if "rejeitado" in status:
                rejected += 1
        return rejected
    
    def get_bugs_proatividade_count(self) -> int:
        """Conta bugs de proatividade nos últimos 7 dias"""
        data_limite = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        reporter_id = "712020:e6f80390-5c4b-4d5f-bcbf-be6620f45767"
        jql = f'created >= {data_limite} AND project = PC AND type = Hotfix AND reporter = {reporter_id}'
        try:
            data = self.client.search_issues(jql, max_results=200, fields="key")
            return len(data.get("issues", []))
        except Exception:
            return 0
    
    def get_bugs_reprovados_qa_count(self) -> int:
        """Conta bugs reprovados pelo QA no mês atual"""
        primeiro_dia_mes = datetime.now().replace(day=1).strftime("%Y-%m-%d")
        jql = f'project = "PC" AND status changed FROM "Validar" TO "Rejeitado da validação" AFTER {primeiro_dia_mes}'
        try:
            data = self.client.search_issues(jql, max_results=200, fields="key")
            return len(data.get("issues", []))
        except Exception:
            return 0
    
    # ===== OKRs de PRODUTO =====
    
    def get_quantidade_deploy(self) -> int:
        releases = self.get_releases_semana_atual("PC")
        return len(releases)
    
    def get_bugs_dentro_sla(self) -> float:
        releases = self.get_releases_semana_atual("PC")
        hotfix = self._get_hotfix_from_releases(releases)
        if not hotfix:
            return 0.0
        
        dentro_sla = 0
        for h in hotfix:
            changelog = self.get_changelog(h['key'])
            if not self._hotfix_excedeu_limite(changelog, 48):
                dentro_sla += 1
        return round((dentro_sla / len(hotfix)) * 100, 2)
    
    def get_total_bugs_48h_15(self) -> int:
        releases = self.get_releases_por_periodo("PC", 15)
        return len(self._get_hotfix_from_releases(releases))
    
    def get_total_bugs_entregues(self) -> int:
        releases = self.get_releases_semana_atual("PC")
        return len(self._get_hotfix_from_releases(releases))
    
    def get_bugs_escalados_prazo(self) -> int:
        releases = self.get_releases_semana_atual("PC")
        hotfix = self._get_hotfix_from_releases(releases)
        
        total = 0
        for h in hotfix:
            changelog = self.get_changelog(h['key'])
            if self._hotfix_excedeu_limite(changelog, 48):
                total += 1
        return total
    
    def get_bugs_subidos_nova_func(self) -> int:
        from config.variables import Variables
        novas = Variables.get_novas_funcionalidades()
        releases = self.get_releases_semana_atual("PC")
        return self._contar_hotfix_por_funcionalidades(releases, novas)
    
    def get_bugs_subidos_nova_func_vs_total(self) -> str:
        from config.variables import Variables
        novas = Variables.get_novas_funcionalidades()
        releases = self.get_releases_semana_atual("PC")
        
        total = len(self._get_hotfix_from_releases(releases))
        novas_count = self._contar_hotfix_por_funcionalidades(releases, novas)
        
        return f"{novas_count} - {total}"
    
    def get_taxa_bugs_com_tag(self) -> float:
        data_limite = datetime.now() - timedelta(days=7)
        jql = f'project = PC AND type = Hotfix AND created >= {data_limite.strftime("%Y-%m-%d")}'
        
        try:
            data = self.client.search_issues(jql, max_results=500, fields="key,customfield_10338")
            issues = data.get("issues", [])
            if not issues:
                return 0.0
            
            total = len(issues)
            sem_tag = 0
            for issue in issues:
                campo = issue["fields"].get("customfield_10338")
                if not campo or (isinstance(campo, dict) and not campo.get("value")):
                    sem_tag += 1
            
            return round((1 - (sem_tag / total)) * 100, 2)
        except Exception:
            return 0.0
    
    def contar_hotfix_por_funcionalidade(self, funcionalidade: str) -> int:
        CAMPO = "customfield_10338"
        self._load_active_sprints()
        if not self._sprint_ids:
            return 0
        
        total = 0
        for sprint_id in self._sprint_ids:
            jql = f'project = PC AND sprint = {sprint_id} AND type = Hotfix'
            try:
                data = self.client.search_issues(jql, max_results=200, fields=f"key,{CAMPO}")
                for issue in data.get("issues", []):
                    campo = issue["fields"].get(CAMPO)
                    if campo and isinstance(campo, dict) and campo.get("value") == funcionalidade:
                        total += 1
            except Exception:
                continue
        return total
    
    def contar_hotfix_por_funcionalidade_com_status(self, funcionalidade: str) -> Dict:
        CAMPO = "customfield_10338"
        self._load_active_sprints()
        if not self._sprint_ids:
            return {"total": 0, "resolvidos": 0, "abertos": 0}
        
        status_resolvidos = ["BUG RESOLVIDO", "Resolvido", "Resolved", "Fechado", "Closed", "Concluído", "Done", "CANCELADO"]
        total = resolvidos = 0
        
        for sprint_id in self._sprint_ids:
            jql = f'project = PC AND sprint = {sprint_id} AND type = Hotfix'
            try:
                data = self.client.search_issues(jql, max_results=200, fields=f"key,status,{CAMPO}")
                for issue in data.get("issues", []):
                    campo = issue["fields"].get(CAMPO)
                    if campo and isinstance(campo, dict) and campo.get("value") == funcionalidade:
                        total += 1
                        if issue["fields"].get("status", {}).get("name", "") in status_resolvidos:
                            resolvidos += 1
            except Exception:
                continue
        return {"total": total, "resolvidos": resolvidos, "abertos": total - resolvidos}
    
    def get_tickets_nova_integracao(self) -> int:
        from config.variables import Variables
        self._load_active_sprints()
        if not self._sprint_ids:
            return 0
        
        novas = Variables.get_novas_integracoes()
        total = 0
        for sprint_id in self._sprint_ids:
            jql = f'project = PC AND sprint = {sprint_id} AND type = Hotfix'
            try:
                data = self.client.search_issues(jql, max_results=200, fields="key,customfield_10338")
                for issue in data.get("issues", []):
                    campo = issue["fields"].get("customfield_10338")
                    if campo and isinstance(campo, dict) and campo.get("value") == "Integrações":
                        child = campo.get("child")
                        if child and isinstance(child, dict) and child.get("value") in novas:
                            total += 1
            except Exception:
                continue
        return total
    
    # ===== OKRs de SERVICE DESK =====
    
    def get_lead_time_bugs(self) -> Dict:
        return self._calcular_lead_time_por_critico(None, None)
    
    def get_lead_time_bugs_critico(self) -> Dict:
        return self._calcular_lead_time_por_critico(True, None)
    
    def get_lead_time_bugs_nao_critico(self) -> Dict:
        return self._calcular_lead_time_por_critico(False, None)
    
    def get_bugs_criticos(self) -> int:
        from config.variables import Variables
        data_limite = datetime.now() - timedelta(days=Variables.LEAD_TIME_DIAS)
        jql = 'project = SP AND type = Bug AND status = "BUG RESOLVIDO"'
        
        try:
            data = self.client.search_issues(jql, max_results=500, fields="key,created,customfield_10377")
            total = 0
            for issue in data.get("issues", []):
                campo = issue["fields"].get("customfield_10377")
                if campo and isinstance(campo, dict) and campo.get("value") == "Sim":
                    changelog = self.get_changelog(issue["key"])
                    for entry in sorted(changelog, key=lambda x: x['created']):
                        for item in entry.get('items', []):
                            if item.get('field') == 'status' and item.get('toString') == "BUG RESOLVIDO":
                                try:
                                    resolved = datetime.strptime(entry['created'].split('.')[0], "%Y-%m-%dT%H:%M:%S")
                                    if resolved >= data_limite:
                                        total += 1
                                except:
                                    pass
                                break
                        else:
                            continue
                        break
            return total
        except Exception:
            return 0
    
    def get_bugs_por_quinzena(self) -> int:
        from config.variables import Variables
        inicio, fim = Variables.get_periodo_analise()
        jql = f'project = SP AND type = Bug AND created >= {inicio.strftime("%Y-%m-%d")} AND created <= {fim.strftime("%Y-%m-%d")}'
        try:
            data = self.client.search_issues(jql, max_results=500, fields="key,status")
            cancelados = Variables.STATUS_CANCELADOS
            return sum(1 for i in data.get("issues", []) if i["fields"].get("status", {}).get("name", "") not in cancelados)
        except Exception:
            return 0
    
    def get_bugs_cancelados_quinzena(self) -> int:
        from config.variables import Variables
        inicio, fim = Variables.get_periodo_analise()
        jql = f'project = SP AND type = Bug AND created >= {inicio.strftime("%Y-%m-%d")} AND created <= {fim.strftime("%Y-%m-%d")}'
        try:
            data = self.client.search_issues(jql, max_results=500, fields="key,status")
            cancelados = Variables.STATUS_CANCELADOS
            return sum(1 for i in data.get("issues", []) if i["fields"].get("status", {}).get("name", "") in cancelados)
        except Exception:
            return 0
    
    def get_taxa_bug_reaberto(self) -> float:
        CAMPO = "customfield_10405"
        hoje = datetime.now()
        dias_para_segunda = hoje.weekday()
        segunda = (hoje - timedelta(days=dias_para_segunda)).replace(hour=0, minute=0, second=0)
        domingo = (segunda + timedelta(days=6)).replace(hour=23, minute=59, second=59)
        
        jql = f'project = SP AND type = Bug AND created >= {segunda.strftime("%Y-%m-%d")} AND created <= {domingo.strftime("%Y-%m-%d")}'
        try:
            data = self.client.search_issues(jql, max_results=500, fields=f"key,{CAMPO}")
            issues = data.get("issues", [])
            if not issues:
                return 0.0
            
            total = len(issues)
            reabertos = 0
            for issue in issues:
                campo = issue["fields"].get(CAMPO)
                if campo and isinstance(campo, list) and len(campo) > 0:
                    for item in campo:
                        if isinstance(item, dict) and item.get("value") == "Sim":
                            reabertos += 1
                            break
                elif campo and isinstance(campo, dict) and campo.get("value") == "Sim":
                    reabertos += 1
            
            return round((reabertos / total) * 100, 2) if total > 0 else 0.0
        except Exception:
            return 0.0
    
    def get_bugs_escalados_complexidade(self) -> int:
        from config.variables import Variables
        time_qa = Variables.get_time_qa_emails()
        data_limite = datetime.now() - timedelta(days=7)
        jql = f'project = PC AND type = Hotfix AND created >= {data_limite.strftime("%Y-%m-%d")}'
        
        try:
            data = self.client.search_issues(jql, max_results=500, fields="key")
            issues = data.get("issues", [])
            
            total = 0
            for issue in issues:
                changelog = self.get_changelog(issue["key"])
                for entry in sorted(changelog, key=lambda x: x['created']):
                    for item in entry.get('items', []):
                        if item.get('field') == 'assignee':
                            de = item.get('fromString', '')
                            para = item.get('toString', '')
                            if de in time_qa and para not in time_qa:
                                total += 1
                                break
                    else:
                        continue
                    break
            return total
        except Exception:
            return 0
    
    # ===== MÉTODOS PRIVADOS AUXILIARES =====
    
    def _get_hotfix_from_releases(self, releases: List[Dict]) -> List[Dict]:
        all_hotfix = []
        for release in releases:
            nome = release.get('name')
            jql = f'project = PC AND fixVersion = "{nome}" AND type = Hotfix'
            try:
                data = self.client.search_issues(jql, max_results=200, fields="key")
                all_hotfix.extend(data.get("issues", []))
            except Exception:
                continue
        return all_hotfix
    
    def _contar_hotfix_por_funcionalidades(self, releases: List[Dict], funcionalidades: List[str]) -> int:
        CAMPO = "customfield_10338"
        total = 0
        for release in releases:
            nome = release.get('name')
            jql = f'project = PC AND fixVersion = "{nome}" AND type = Hotfix'
            try:
                data = self.client.search_issues(jql, max_results=200, fields=f"key,{CAMPO}")
                for issue in data.get("issues", []):
                    campo = issue["fields"].get(CAMPO)
                    if campo and isinstance(campo, dict) and campo.get("value") in funcionalidades:
                        total += 1
            except Exception:
                continue
        return total
    
    def _hotfix_excedeu_limite(self, changelog: List[Dict], limite_horas: int) -> bool:
        tempo = 0
        em_doing = False
        entrou_em = None
        
        for entry in sorted(changelog, key=lambda x: x['created']):
            data = datetime.strptime(entry['created'].split('.')[0], "%Y-%m-%dT%H:%M:%S")
            for item in entry.get('items', []):
                if item.get('field') == 'status':
                    para = item.get('toString', '')
                    if "doing" in para.lower() and not em_doing:
                        em_doing = True
                        entrou_em = data
                    elif "doing" not in para.lower() and em_doing:
                        tempo += (data - entrou_em).total_seconds()
                        em_doing = False
        
        if em_doing and entrou_em:
            tempo += (datetime.now() - entrou_em).total_seconds()
        return (tempo / 3600) > limite_horas
    
    def _calcular_lead_time_por_critico(self, apenas_critico: Optional[bool], dias: Optional[int]) -> Dict:
        from config.variables import Variables
        if dias is None:
            dias = Variables.LEAD_TIME_DIAS
        
        data_limite = datetime.now() - timedelta(days=dias)
        jql = 'project = SP AND type = Bug AND status = "BUG RESOLVIDO"'
        
        try:
            data = self.client.search_issues(jql, max_results=500, fields="key,created,customfield_10377")
            issues = data.get("issues", [])
            if not issues:
                return {"media": 0, "mediana": 0, "total": 0}
            
            def processar(issue):
                key = issue["key"]
                created = issue["fields"].get("created")
                if not created:
                    return None
                
                campo = issue["fields"].get("customfield_10377")
                is_critico = campo and isinstance(campo, dict) and campo.get("value") == "Sim"
                
                if apenas_critico is not None:
                    if apenas_critico and not is_critico:
                        return None
                    if not apenas_critico and is_critico:
                        return None
                
                changelog = self.get_changelog(key)
                for entry in sorted(changelog, key=lambda x: x['created']):
                    for item in entry.get('items', []):
                        if item.get('field') == 'status' and item.get('toString') == "BUG RESOLVIDO":
                            try:
                                resolved = datetime.strptime(entry['created'].split('.')[0], "%Y-%m-%dT%H:%M:%S")
                                if resolved < data_limite:
                                    return None
                                created_date = datetime.strptime(created.split('.')[0], "%Y-%m-%dT%H:%M:%S")
                                return (resolved - created_date).total_seconds() / 3600 / 24
                            except:
                                return None
                return None
            
            lead_times = []
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(processar, issue) for issue in issues]
                for future in as_completed(futures):
                    result = future.result()
                    if result is not None:
                        lead_times.append(result)
            
            if not lead_times:
                return {"media": 0, "mediana": 0, "total": 0}
            
            lead_times.sort()
            media = sum(lead_times) / len(lead_times)
            n = len(lead_times)
            mediana = lead_times[n//2] if n % 2 else (lead_times[n//2 - 1] + lead_times[n//2]) / 2
            
            return {"media": round(media, 1), "mediana": round(mediana, 1), "total": len(lead_times)}
        except Exception:
            return {"media": 0, "mediana": 0, "total": 0}
    
    def get_releases_por_periodo(self, projeto: str = "PC", dias: int = 15) -> List[Dict]:
        releases = self.get_all_releases(projeto)
        data_limite = datetime.now() - timedelta(days=dias)
        result = []
        for r in releases:
            release_date = r.get('releaseDate')
            if release_date and r.get('released', False):
                try:
                    if datetime.strptime(release_date, "%Y-%m-%d") >= data_limite:
                        result.append(r)
                except:
                    pass
        return result