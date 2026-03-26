from typing import List, Dict, Optional
from core.jira_client import JiraClient
from datetime import datetime, timedelta
import re
import requests

class JQLService:
    def __init__(self):
        self.client = JiraClient()
        self._sprint_ids = []
        self._sprint_names = []
        self._cached_metrics = None
        
        # Cache para releases
        self._releases_cache = {
            "todas": None,
            "semana_atual": None,
            "ultimos_15_dias": None,
            "ultimo_acesso": None
        }
    
    def _load_active_sprints(self):
        """Carrega IDs e nomes de TODAS as sprints ativas"""
        if not self._sprint_ids:
            sprints = self.client.get_active_sprints_via_agile()
            if sprints:
                self._sprint_ids = [s["id"] for s in sprints if s.get("id")]
                self._sprint_names = [s["name"] for s in sprints if s.get("name")]
    
    def _extrair_ciclo(self, nome_completo: str) -> str:
        """Extrai apenas o ciclo (ex: 'Sprint 26Q1.5') do nome completo"""
        if not nome_completo:
            return "Sprint Desconhecida"
        
        match = re.search(r'(Sprint\s+\d{2}Q\d\.\d+)', nome_completo)
        if match:
            return match.group(1)
        
        parts = nome_completo.split()
        if len(parts) >= 3:
            return f"{parts[0]} {parts[1]} {parts[2]}"
        
        return nome_completo
    
    def get_nome_ciclo(self) -> str:
        """Retorna o nome do CICLO (sem sufixos) baseado na primeira sprint"""
        self._load_active_sprints()
        if not self._sprint_names:
            return "Sprint Desconhecida"
        
        return self._extrair_ciclo(self._sprint_names[0])
    
    # ===== MÉTODOS PARA RELEASES =====
    
    def _obter_todas_releases(self, projeto: str = "PC") -> List[Dict]:
        """
        Obtém todas as releases do projeto
        Resultado é cacheado para evitar múltiplas chamadas
        """
        if self._releases_cache["todas"] is not None:
            return self._releases_cache["todas"]
        
        try:
            url = f"{self.client.base_url}/rest/api/3/project/{projeto}/versions"
            headers = self.client.auth.get_headers()
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                versions = response.json()
                # Filtrar apenas releases (não arquivadas)
                releases = [v for v in versions if not v.get('archived', False)]
                self._releases_cache["todas"] = releases
                self._releases_cache["ultimo_acesso"] = datetime.now()
                return releases
            else:
                print(f"⚠️ Erro ao buscar releases: {response.status_code}")
                return []
        except Exception as e:
            print(f"⚠️ Erro ao buscar releases: {e}")
            return []
    
    def _obter_releases_por_periodo(self, dias: int) -> List[Dict]:
        """
        Obtém releases lançadas nos últimos X dias
        Usa cache para evitar requisições repetidas
        """
        cache_key = f"ultimos_{dias}_dias"
        
        if self._releases_cache.get(cache_key) is not None:
            return self._releases_cache[cache_key]
        
        todas = self._obter_todas_releases()
        data_limite = datetime.now() - timedelta(days=dias)
        
        releases_periodo = []
        for release in todas:
            release_date = release.get('releaseDate')
            if not release_date or not release.get('released', False):
                continue
            
            try:
                data_release = datetime.strptime(release_date, "%Y-%m-%d")
                if data_release >= data_limite:
                    releases_periodo.append(release)
            except:
                continue
        
        self._releases_cache[cache_key] = releases_periodo
        return releases_periodo
    
    def _obter_releases_semana_atual(self) -> List[Dict]:
        """
        Obtém releases lançadas na semana atual (segunda a domingo)
        """
        if self._releases_cache["semana_atual"] is not None:
            return self._releases_cache["semana_atual"]
        
        todas = self._obter_todas_releases()
        
        hoje = datetime.now()
        dias_para_segunda = hoje.weekday()
        segunda = hoje - timedelta(days=dias_para_segunda)
        segunda = segunda.replace(hour=0, minute=0, second=0, microsecond=0)
        
        domingo = segunda + timedelta(days=6)
        domingo = domingo.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        releases_semana = []
        for release in todas:
            release_date = release.get('releaseDate')
            if not release_date or not release.get('released', False):
                continue
            
            try:
                data_release = datetime.strptime(release_date, "%Y-%m-%d")
                data_release = data_release.replace(hour=12, minute=0)
                
                if segunda <= data_release <= domingo:
                    releases_semana.append(release)
            except:
                continue
        
        self._releases_cache["semana_atual"] = releases_semana
        return releases_semana
    
    def contar_releases_semana_atual(self) -> int:
        """OKR 1: quantidade_deploy - releases na semana atual"""
        releases = self._obter_releases_semana_atual()
        return len(releases)
    
    def _hotfix_excedeu_limite(self, issue_key: str, limite_horas: int) -> bool:
        """
        Verifica se um hotfix excedeu o limite de horas em status 'doing'
        """
        try:
            url = f"{self.client.base_url}/rest/api/3/issue/{issue_key}/changelog"
            headers = self.client.auth.get_headers()
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                return False
            
            changelog = response.json().get("values", [])
            
            tempo_doing = 0
            em_doing = False
            entrou_em = None
            
            for entry in sorted(changelog, key=lambda x: x['created']):
                data = datetime.strptime(entry['created'].split('.')[0], "%Y-%m-%dT%H:%M:%S")
                
                for item in entry.get('items', []):
                    if item['field'] == 'status':
                        para = item['toString']
                        
                        if "doing" in para.lower() and not em_doing:
                            em_doing = True
                            entrou_em = data
                        elif "doing" not in para.lower() and em_doing:
                            tempo_doing += (data - entrou_em).total_seconds()
                            em_doing = False
            
            if em_doing and entrou_em:
                tempo_doing += (datetime.now() - entrou_em).total_seconds()
            
            return (tempo_doing / 3600) > limite_horas
            
        except Exception as e:
            print(f"⚠️ Erro ao analisar issue {issue_key}: {e}")
            return False
    
    def contar_bugs_dentro_sla_semana_atual(self) -> float:
        """
        OKR 2: bugs_dentro_sla - percentual de hotfix que ficaram DENTRO de 48h em 'doing'
        Retorna: (hotfix com menos de 48h / total de hotfix) * 100
        """
        releases = self._obter_releases_semana_atual()
        if not releases:
            return 0.0
        
        total_hotfix = 0
        hotfix_dentro_sla = 0
        
        for release in releases:
            nome = release.get('name')
            jql = f'project = PC AND fixVersion = "{nome}" AND type = Hotfix'
            
            try:
                data = self.client.search_issues(jql, max_results=200, fields="key")
                issues = data.get("issues", [])
                
                for issue in issues:
                    total_hotfix += 1
                    if not self._hotfix_excedeu_limite(issue['key'], 48):
                        hotfix_dentro_sla += 1
            except Exception as e:
                print(f"⚠️ Erro ao analisar release {nome}: {e}")
                continue
        
        if total_hotfix == 0:
            return 0.0
        
        percentual = (hotfix_dentro_sla / total_hotfix) * 100
        return round(percentual, 2)
    
    def contar_hotfix_ultimos_15_dias(self) -> int:
        """
        OKR 3: total_bugs_48h_15 - contar hotfix nas releases dos últimos 15 dias
        """
        releases = self._obter_releases_por_periodo(15)
        if not releases:
            return 0
        
        total_hotfix = 0
        
        for release in releases:
            nome = release.get('name')
            jql = f'project = PC AND fixVersion = "{nome}" AND type = Hotfix'
            
            try:
                data = self.client.search_issues(jql, max_results=200, fields="key")
                issues = data.get("issues", [])
                total_hotfix += len(issues)
            except Exception as e:
                print(f"⚠️ Erro ao contar hotfix em {nome}: {e}")
                continue
        
        return total_hotfix
    
    # ===== MÉTODOS EXISTENTES =====
    
    def _get_all_issues_from_current_sprints(self) -> List[Dict]:
        """Busca issues de TODAS as sprints ativas"""
        self._load_active_sprints()
        
        if not self._sprint_ids:
            return []
        
        all_issues = []
        for sprint_id in self._sprint_ids:
            try:
                jql = f'sprint = {sprint_id}'
                fields = "key,status"
                data = self.client.search_issues(jql, max_results=500, fields=fields)
                issues = data.get("issues", []) if data else []
                all_issues.extend(issues)
            except Exception as e:
                print(f"      ⚠️ Erro na sprint {sprint_id}: {e}")
                continue
        
        return all_issues
    
    def get_consolidated_metrics(self) -> Dict:
        if not self._cached_metrics:
            self._calcular_todas_metricas()
        return {
            "total_tarefas": self._cached_metrics["total_tarefas"],
            "taxa_conclusao": self._cached_metrics["taxa_conclusao"]
        }
    
    def _calcular_todas_metricas(self) -> Dict:
        """Calcula métricas de TODAS as sprints"""
        issues = self._get_all_issues_from_current_sprints()
        
        total_tarefas = len(issues)
        total_concluidas = 0
        completed_keywords = ["done", "concluído", "resolved", "closed", "fechado"]
        
        for issue in issues:
            if not issue or "fields" not in issue:
                continue
            status = issue["fields"].get("status", {}).get("name", "").lower()
            if any(keyword in status for keyword in completed_keywords):
                total_concluidas += 1
        
        taxa_conclusao = (total_concluidas / total_tarefas * 100) if total_tarefas > 0 else 0
        
        quantidade_deploy = self.contar_releases_semana_atual()
        bugs_dentro_sla = self.contar_bugs_dentro_sla_semana_atual()
        total_bugs_48h_15 = self.contar_hotfix_ultimos_15_dias()
        
        self._cached_metrics = {
            "total_tarefas": total_tarefas,
            "taxa_conclusao": round(taxa_conclusao, 2),
            "tarefas_nao_aprovadas": 0,
            "bugs_proatividade": 0,
            "bugs_reprovados_qa": 0,
            "quantidade_deploy": quantidade_deploy,
            "bugs_dentro_sla": bugs_dentro_sla,
            "total_bugs_48h_15": total_bugs_48h_15
        }
        
        return self._cached_metrics
    
    def get_rejected_tasks_count(self) -> int:
        if not self._cached_metrics:
            self._calcular_todas_metricas()
        return self._cached_metrics["tarefas_nao_aprovadas"]
    
    def get_bugs_proatividade_count(self) -> int:
        if not self._cached_metrics:
            self._calcular_todas_metricas()
        return self._cached_metrics["bugs_proatividade"]
    
    def get_bugs_reprovados_qa_count(self) -> int:
        if not self._cached_metrics:
            self._calcular_todas_metricas()
        return self._cached_metrics["bugs_reprovados_qa"]
    
    def get_quantidade_deploy(self) -> int:
        if not self._cached_metrics:
            self._calcular_todas_metricas()
        return self._cached_metrics["quantidade_deploy"]
    
    def get_bugs_dentro_sla(self) -> float:
        if not self._cached_metrics:
            self._calcular_todas_metricas()
        return self._cached_metrics["bugs_dentro_sla"]
    
    def get_total_bugs_48h_15(self) -> int:
        if not self._cached_metrics:
            self._calcular_todas_metricas()
        return self._cached_metrics["total_bugs_48h_15"]
    
    def get_sprint_metrics_dict(self) -> Dict:
        if not self._cached_metrics:
            self._calcular_todas_metricas()
        return self._cached_metrics