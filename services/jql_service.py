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
                data = self.client.search_issues(f'sprint = {sprint_id}', max_results=500, fields="key,status")
                all_issues.extend(data.get("issues", []))
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
    
    def get_releases_por_periodo(self, projeto: str = "PC", dias: int = 15) -> List[Dict]:
        releases = self.get_all_releases(projeto)
        data_limite = datetime.now() - timedelta(days=dias)
        return [r for r in releases if r.get('releaseDate') and r.get('released', False) and datetime.strptime(r['releaseDate'], "%Y-%m-%d") >= data_limite]
    
    # ===== MÉTODOS AUXILIARES =====
    def _get_hotfix_from_releases(self, releases: List[Dict]) -> List[Dict]:
        all_hotfix = []
        for release in releases:
            nome = release.get('name')
            try:
                data = self.client.search_issues(f'project = PC AND fixVersion = "{nome}" AND type = Hotfix', max_results=200, fields="key")
                all_hotfix.extend(data.get("issues", []))
            except Exception:
                continue
        return all_hotfix
    
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
    
    # ===== OKRs =====
    def get_quantidade_deploy(self) -> int:
        return len(self.get_releases_semana_atual("PC"))
    
    def get_bugs_dentro_sla(self) -> float:
        releases = self.get_releases_semana_atual("PC")
        hotfix = self._get_hotfix_from_releases(releases)
        if not hotfix:
            return 0.0
        dentro_sla = sum(1 for h in hotfix if not self._hotfix_excedeu_limite(self.get_changelog(h['key']), 48))
        return round((dentro_sla / len(hotfix)) * 100, 2)
    
    def get_total_bugs_48h_15(self) -> int:
        return len(self._get_hotfix_from_releases(self.get_releases_por_periodo("PC", 15)))
    
    def get_bugs_escalados_prazo(self) -> int:
        hotfix = self._get_hotfix_from_releases(self.get_releases_semana_atual("PC"))
        return sum(1 for h in hotfix if self._hotfix_excedeu_limite(self.get_changelog(h['key']), 48))
    
    def get_taxa_bugs_com_tag(self) -> float:
        data_limite = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        try:
            data = self.client.search_issues(f'project = PC AND type = Hotfix AND created >= {data_limite}', max_results=500, fields="key,customfield_10338")
            issues = data.get("issues", [])
            if not issues:
                return 0.0
            total = len(issues)
            sem_tag = sum(1 for i in issues if not i["fields"].get("customfield_10338") or (isinstance(i["fields"].get("customfield_10338"), dict) and not i["fields"]["customfield_10338"].get("value")))
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
            try:
                data = self.client.search_issues(f'project = PC AND sprint = {sprint_id} AND type = Hotfix', max_results=200, fields=f"key,{CAMPO}")
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
            try:
                data = self.client.search_issues(f'project = PC AND sprint = {sprint_id} AND type = Hotfix', max_results=200, fields=f"key,status,{CAMPO}")
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
        novas = Variables.get_novas_integracoes()
        self._load_active_sprints()
        if not self._sprint_ids:
            return 0
        total = 0
        for sprint_id in self._sprint_ids:
            try:
                data = self.client.search_issues(f'project = PC AND sprint = {sprint_id} AND type = Hotfix', max_results=200, fields="key,customfield_10338")
                for issue in data.get("issues", []):
                    campo = issue["fields"].get("customfield_10338")
                    if campo and isinstance(campo, dict) and campo.get("value") == "Integração Principal":
                        child = campo.get("child")
                        if child and isinstance(child, dict) and child.get("value") in novas:
                            total += 1
            except Exception:
                continue
        return total
    
    def get_bugs_escalados_complexidade(self) -> int:
        from config.variables import Variables
        time_qa = Variables.get_time_qa_emails()
        data_limite = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        try:
            data = self.client.search_issues(f'project = PC AND type = Hotfix AND created >= {data_limite}', max_results=500, fields="key")
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
    
    # ===== MÉTODOS DE DETALHAMENTO PARA RELATÓRIO =====
    def _buscar_e_detalhar_issues(self, jql: str, titulo: str, campos: list, limite: int = 100):
        from utils.relatorio_handler import relatorio
        try:
            data = self.client.search_issues(jql, max_results=limite, fields=",".join(campos))
            issues = data.get("issues", [])
            if not issues:
                relatorio.adicionar_linha("  Nenhum item encontrado")
                return
            for issue in issues[:limite]:
                key = issue["key"]
                status = issue["fields"].get("status", {}).get("name", "N/A")
                summary = issue["fields"].get("summary", "N/A")[:70]
                relatorio.adicionar_linha(f"  {key} - {status}")
                relatorio.adicionar_linha(f"    {summary}")
            if len(issues) > limite:
                relatorio.adicionar_linha(f"  ... e mais {len(issues)-limite} itens")
        except Exception as e:
            relatorio.adicionar_linha(f"  Erro: {e}")
    
    def detalhar_bugs_por_quinzena(self):
        from config.variables import Variables
        from utils.relatorio_handler import relatorio
        inicio, fim = Variables.get_periodo_analise()
        jql = f'project = SP AND type = Bug AND created >= {inicio.strftime("%Y-%m-%d")} AND created <= {fim.strftime("%Y-%m-%d")}'
        try:
            data = self.client.search_issues(jql, max_results=500, fields="key,summary,status,created")
            issues = data.get("issues", [])
            cancelados = Variables.STATUS_CANCELADOS
            bugs_ativos = [i for i in issues if i["fields"].get("status", {}).get("name", "") not in cancelados]
            relatorio.adicionar_linha(f"Total de bugs ativos: {len(bugs_ativos)}")
            for bug in bugs_ativos[:30]:
                key = bug["key"]
                status = bug["fields"].get("status", {}).get("name", "N/A")
                created = bug["fields"].get("created", "")[:10]
                summary = bug["fields"].get("summary", "N/A")[:80]
                relatorio.adicionar_linha(f"  {key} - {status} (criado {created})")
                relatorio.adicionar_linha(f"    {summary}")
        except Exception as e:
            relatorio.adicionar_linha(f"  Erro: {e}")
    
    def detalhar_bugs_cancelados_quinzena(self):
        from config.variables import Variables
        from utils.relatorio_handler import relatorio
        inicio, fim = Variables.get_periodo_analise()
        jql = f'project = SP AND type = Bug AND created >= {inicio.strftime("%Y-%m-%d")} AND created <= {fim.strftime("%Y-%m-%d")}'
        cancelados = Variables.STATUS_CANCELADOS
        self._buscar_e_detalhar_issues(jql, "Bugs Cancelados", ["key,summary,status"], 100)
    
    def detalhar_hotfix_por_funcionalidade(self, funcionalidade: str):
        from utils.relatorio_handler import relatorio
        CAMPO = "customfield_10338"
        self._load_active_sprints()
        if not self._sprint_ids:
            relatorio.adicionar_linha("  Nenhuma sprint ativa")
            return
        todos = []
        for sprint_id in self._sprint_ids:
            try:
                data = self.client.search_issues(f'project = PC AND sprint = {sprint_id} AND type = Hotfix', max_results=200, fields=f"key,summary,status,{CAMPO}")
                for issue in data.get("issues", []):
                    campo = issue["fields"].get(CAMPO)
                    if campo and isinstance(campo, dict) and campo.get("value") == funcionalidade:
                        todos.append(issue)
            except Exception:
                continue
        relatorio.adicionar_linha(f"Total: {len(todos)}")
        for item in todos[:30]:
            key = item["key"]
            status = item["fields"].get("status", {}).get("name", "N/A")
            summary = item["fields"].get("summary", "N/A")[:70]
            relatorio.adicionar_linha(f"  {key} - {status}")
            relatorio.adicionar_linha(f"    {summary}")
    
    def detalhar_novas_integracoes(self):
        from config.variables import Variables
        from utils.relatorio_handler import relatorio
        novas = Variables.get_novas_integracoes()
        self._load_active_sprints()
        if not self._sprint_ids:
            relatorio.adicionar_linha("  Nenhuma sprint ativa")
            return
        todos = []
        for sprint_id in self._sprint_ids:
            try:
                data = self.client.search_issues(f'project = PC AND sprint = {sprint_id} AND type = Hotfix', max_results=200, fields="key,summary,status,customfield_10338")
                for issue in data.get("issues", []):
                    campo = issue["fields"].get("customfield_10338")
                    if campo and isinstance(campo, dict) and campo.get("value") == "Integração Principal":
                        child = campo.get("child")
                        if child and isinstance(child, dict) and child.get("value") in novas:
                            todos.append(issue)
            except Exception:
                continue
        relatorio.adicionar_linha(f"Total: {len(todos)}")
        for item in todos[:30]:
            key = item["key"]
            status = item["fields"].get("status", {}).get("name", "N/A")
            summary = item["fields"].get("summary", "N/A")[:70]
            relatorio.adicionar_linha(f"  {key} - {status}")
            relatorio.adicionar_linha(f"    {summary}")
    
    def detalhar_hotfix_novas_funcionalidades(self):
        from config.variables import Variables
        from utils.relatorio_handler import relatorio
        novas = Variables.get_novas_funcionalidades()
        releases = self.get_releases_semana_atual("PC")
        todos = []
        for release in releases:
            nome = release.get('name')
            try:
                data = self.client.search_issues(f'project = PC AND fixVersion = "{nome}" AND type = Hotfix', max_results=200, fields="key,summary,status,customfield_10338")
                for issue in data.get("issues", []):
                    campo = issue["fields"].get("customfield_10338")
                    if campo and isinstance(campo, dict) and campo.get("value") in novas:
                        todos.append(issue)
            except Exception:
                continue
        relatorio.adicionar_linha(f"Total: {len(todos)}")
        for item in todos[:30]:
            key = item["key"]
            status = item["fields"].get("status", {}).get("name", "N/A")
            summary = item["fields"].get("summary", "N/A")[:70]
            relatorio.adicionar_linha(f"  {key} - {status}")
            relatorio.adicionar_linha(f"    {summary}")
    
    def detalhar_hotfix_15_dias(self):
        from utils.relatorio_handler import relatorio
        releases = self.get_releases_por_periodo("PC", 15)
        todos = []
        for release in releases:
            nome = release.get('name')
            try:
                data = self.client.search_issues(f'project = PC AND fixVersion = "{nome}" AND type = Hotfix', max_results=200, fields="key,summary,status")
                for issue in data.get("issues", []):
                    todos.append(issue)
            except Exception:
                continue
        relatorio.adicionar_linha(f"Total: {len(todos)}")
        for item in todos[:30]:
            key = item["key"]
            status = item["fields"].get("status", {}).get("name", "N/A")
            summary = item["fields"].get("summary", "N/A")[:70]
            relatorio.adicionar_linha(f"  {key} - {status}")
            relatorio.adicionar_linha(f"    {summary}")
    
    def detalhar_bugs_reabertos(self):
        from utils.relatorio_handler import relatorio
        CAMPO = "customfield_10405"
        hoje = datetime.now()
        dias_para_segunda = hoje.weekday()
        segunda = (hoje - timedelta(days=dias_para_segunda)).replace(hour=0, minute=0, second=0)
        domingo = (segunda + timedelta(days=6)).replace(hour=23, minute=59, second=59)
        jql = f'project = SP AND type = Bug AND created >= {segunda.strftime("%Y-%m-%d")} AND created <= {domingo.strftime("%Y-%m-%d")}'
        try:
            data = self.client.search_issues(jql, max_results=500, fields=f"key,summary,status,{CAMPO}")
            issues = data.get("issues", [])
            reabertos = []
            for issue in issues:
                campo = issue["fields"].get(CAMPO)
                is_reaberto = False
                if campo and isinstance(campo, list) and len(campo) > 0:
                    for item in campo:
                        if isinstance(item, dict) and item.get("value") == "Sim":
                            is_reaberto = True
                            break
                elif campo and isinstance(campo, dict) and campo.get("value") == "Sim":
                    is_reaberto = True
                if is_reaberto:
                    reabertos.append(issue)
            relatorio.adicionar_linha(f"Total de bugs reabertos: {len(reabertos)}")
            for bug in reabertos[:30]:
                key = bug["key"]
                status = bug["fields"].get("status", {}).get("name", "N/A")
                summary = bug["fields"].get("summary", "N/A")[:70]
                relatorio.adicionar_linha(f"  {key} - {status}")
                relatorio.adicionar_linha(f"    {summary}")
        except Exception as e:
            relatorio.adicionar_linha(f"  Erro: {e}")
    
    def detalhar_bugs_sem_tag(self):
        from utils.relatorio_handler import relatorio
        data_limite = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        jql = f'project = PC AND type = Hotfix AND created >= {data_limite}'
        try:
            data = self.client.search_issues(jql, max_results=500, fields="key,summary,status,customfield_10338")
            issues = data.get("issues", [])
            sem_tag = []
            for issue in issues:
                campo = issue["fields"].get("customfield_10338")
                if not campo or (isinstance(campo, dict) and not campo.get("value")):
                    sem_tag.append(issue)
            relatorio.adicionar_linha(f"Total de hotfix SEM TAG: {len(sem_tag)}")
            for item in sem_tag[:30]:
                key = item["key"]
                status = item["fields"].get("status", {}).get("name", "N/A")
                summary = item["fields"].get("summary", "N/A")[:70]
                relatorio.adicionar_linha(f"  {key} - {status}")
                relatorio.adicionar_linha(f"    {summary}")
        except Exception as e:
            relatorio.adicionar_linha(f"  Erro: {e}")
    
    def detalhar_lead_time_por_criticidade(self, tipo: str = "todos"):
        from utils.relatorio_handler import relatorio
        from config.variables import Variables
        dias = Variables.LEAD_TIME_DIAS
        data_limite = datetime.now() - timedelta(days=dias)
        try:
            data = self.client.search_issues('project = SP AND type = Bug AND status = "BUG RESOLVIDO"', max_results=500, fields="key,created,customfield_10377")
            issues = data.get("issues", [])
            detalhes = []
            for issue in issues:
                key = issue["key"]
                created = issue["fields"].get("created")
                campo = issue["fields"].get("customfield_10377")
                is_critico = campo and isinstance(campo, dict) and campo.get("value") == "Sim"
                if tipo == "criticos" and not is_critico:
                    continue
                if tipo == "nao_criticos" and is_critico:
                    continue
                if not created:
                    continue
                changelog = self.get_changelog(key)
                resolved_date = None
                start_date = None
                historico = []
                for entry in sorted(changelog, key=lambda x: x['created']):
                    data_entry = datetime.strptime(entry['created'].split('.')[0], "%Y-%m-%dT%H:%M:%S")
                    for item in entry.get('items', []):
                        if item.get('field') == 'status':
                            de = item.get('fromString', '')
                            para = item.get('toString', '')
                            historico.append({"data": data_entry, "de": de, "para": para})
                            if para == "BUG RESOLVIDO":
                                resolved_date = data_entry
                                break
                            if para in ["In Progress", "Doing", "Em Andamento"]:
                                start_date = data_entry
                    if resolved_date:
                        break
                if not resolved_date:
                    continue
                if not start_date:
                    try:
                        start_date = datetime.strptime(created.split('.')[0], "%Y-%m-%dT%H:%M:%S")
                    except:
                        continue
                if resolved_date < data_limite:
                    continue
                lead_dias = (resolved_date - start_date).total_seconds() / 3600 / 24
                if lead_dias < 0 or lead_dias > 60:
                    continue
                historico_resumido = [f"  {h['data'].strftime('%d/%m %H:%M')}: {h['de']} → {h['para']}" for h in historico[-5:]]
                detalhes.append({"key": key, "lead_dias": round(lead_dias, 1), "historico": historico_resumido})
            titulo = {"todos": "Lead Time - Todos os Bugs", "criticos": "Lead Time - Bugs Críticos", "nao_criticos": "Lead Time - Bugs Não Críticos"}.get(tipo, "Lead Time - Bugs")
            relatorio.adicionar_linha(titulo)
            relatorio.adicionar_linha("-" * 40)
            if detalhes:
                relatorio.adicionar_linha(f"Total: {len(detalhes)} tickets")
                for d in detalhes[:15]:
                    relatorio.adicionar_linha(f"  {d['key']}: {d['lead_dias']} dias")
                    for linha in d['historico']:
                        relatorio.adicionar_linha(linha, 1)
            else:
                relatorio.adicionar_linha("  Nenhum ticket encontrado no período")
        except Exception as e:
            relatorio.adicionar_linha(f"  Erro: {e}")

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

    def get_bugs_por_quinzena(self) -> int:
        """Conta bugs ativos na quinzena (excluindo cancelados)"""
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
        """Conta bugs cancelados na quinzena"""
        from config.variables import Variables
        inicio, fim = Variables.get_periodo_analise()
        jql = f'project = SP AND type = Bug AND created >= {inicio.strftime("%Y-%m-%d")} AND created <= {fim.strftime("%Y-%m-%d")}'
        try:
            data = self.client.search_issues(jql, max_results=500, fields="key,status")
            cancelados = Variables.STATUS_CANCELADOS
            return sum(1 for i in data.get("issues", []) if i["fields"].get("status", {}).get("name", "") in cancelados)
        except Exception:
            return 0

    def get_bugs_subidos_nova_func(self) -> int:
        """Conta hotfix de novas funcionalidades na semana"""
        from config.variables import Variables
        novas = Variables.get_novas_funcionalidades()
        releases = self.get_releases_semana_atual("PC")
        return self._contar_hotfix_por_funcionalidades(releases, novas)

    def get_bugs_subidos_nova_func_vs_total(self) -> str:
        """Retorna 'novas - total' para releases da semana"""
        from config.variables import Variables
        novas = Variables.get_novas_funcionalidades()
        releases = self.get_releases_semana_atual("PC")
        total = len(self._get_hotfix_from_releases(releases))
        novas_count = self._contar_hotfix_por_funcionalidades(releases, novas)
        return f"{novas_count} - {total}"

    def get_lead_time_bugs(self) -> Dict:
        """Calcula lead time de todos os bugs"""
        return self._calcular_lead_time_por_critico(None, None)

    def get_lead_time_bugs_nao_critico(self) -> Dict:
        """Calcula lead time de bugs NÃO críticos"""
        return self._calcular_lead_time_por_critico(False, None)

    def get_lead_time_bugs_critico(self) -> Dict:
        """Calcula lead time de bugs CRÍTICOS"""
        return self._calcular_lead_time_por_critico(True, None)

    def get_taxa_bug_reaberto(self) -> float:
        """Calcula taxa de bugs reabertos na semana"""
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
        
    def _contar_hotfix_por_funcionalidades(self, releases: List[Dict], funcionalidades: List[str]) -> int:
        """Conta hotfix por lista de funcionalidades"""
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
                resolved_date = None
                start_date = None
                for entry in sorted(changelog, key=lambda x: x['created']):
                    data_entry = datetime.strptime(entry['created'].split('.')[0], "%Y-%m-%dT%H:%M:%S")
                    for item in entry.get('items', []):
                        if item.get('field') == 'status':
                            para = item.get('toString', '')
                            if para == "BUG RESOLVIDO":
                                resolved_date = data_entry
                                break
                            if para in ["In Progress", "Doing", "Em Andamento"]:
                                start_date = data_entry
                    if resolved_date:
                        break
                if not resolved_date:
                    return None
                if not start_date:
                    try:
                        start_date = datetime.strptime(created.split('.')[0], "%Y-%m-%dT%H:%M:%S")
                    except:
                        return None
                if resolved_date < data_limite:
                    return None
                lead_dias = (resolved_date - start_date).total_seconds() / 3600 / 24
                if lead_dias < 0 or lead_dias > 60:
                    return None
                return lead_dias
            
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