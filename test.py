"""
bugs_sp_contagem_manual.py
Conta bugs do SP filtrando manualmente (já que JQL não está funcionando corretamente)
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.auth import OAuth2Client
import requests
from datetime import datetime

def contar_bugs_sp():
    """Conta bugs do SP filtrando manualmente"""
    
    print("="*80)
    print("🔍 BUGS DO SP - CONTAGEM MANUAL")
    print("="*80)
    print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    # Status a serem ignorados (considerados como "concluídos")
    status_ignorar = [
        "BUG RESOLVIDO",
        "CANCELADO",
        "DESPRIORIZADO",
        "MELHORIA",
        "MELHORIA RESOLVIDA",
        "PRODUCT BACKLOG REGISTRADO",
        "Fechado",
        "Closed",
        "Resolvido",
        "Concluído",
        "Done"
    ]
    
    print(f"\n📋 Status a ignorar (considerados concluídos):")
    for s in status_ignorar:
        print(f"   • {s}")
    
    try:
        auth = OAuth2Client()
        headers = auth.get_headers()
        base_url = auth.get_base_url()
        
        url = f"{base_url}/rest/api/3/search/jql"
        
        # Buscar TODOS os tickets do SP (sem filtro de tipo)
        # Depois vamos filtrar manualmente
        print("\n1️⃣ BUSCANDO TODOS OS TICKETS DO SP")
        print("-"*60)
        
        params = {
            "jql": "project = SP",
            "maxResults": 500,  # Aumentado para pegar todos
            "fields": "key,summary,status,issuetype,created,duedate,priority,assignee"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Erro: {response.status_code}")
            return
        
        data = response.json()
        todos_tickets = data.get("issues", [])
        total_todos = data.get("total", 0)
        
        print(f"   Total de tickets no projeto SP: {total_todos}")
        
        # Coletar tipos encontrados
        tipos_encontrados = set()
        for ticket in todos_tickets:
            tipo = ticket["fields"]["issuetype"]["name"]
            tipos_encontrados.add(tipo)
        
        print(f"\n   Tipos de issues encontrados: {sorted(tipos_encontrados)}")
        
        # Filtrar apenas BUGS (pelo nome do tipo)
        # Procurar qualquer tipo que contenha "bug" (case insensitive)
        tipos_bug = [t for t in tipos_encontrados if "bug" in t.lower()]
        
        if not tipos_bug:
            print("\n⚠️ Nenhum tipo de 'bug' encontrado. Usando todos os tickets?")
            bugs = todos_tickets
            print(f"   Todos os tickets serão analisados: {len(bugs)}")
        else:
            print(f"\n🎯 Tipos considerados como 'bug': {tipos_bug}")
            bugs = [t for t in todos_tickets if t["fields"]["issuetype"]["name"] in tipos_bug]
        
        print(f"\n   Total de bugs identificados: {len(bugs)}")
        
        if not bugs:
            print("\n📭 Nenhum bug encontrado")
            return
        
        # Classificar bugs
        bugs_concluidos = []
        bugs_nao_concluidos = []
        
        for bug in bugs:
            status = bug["fields"]["status"]["name"]
            if status in status_ignorar:
                bugs_concluidos.append(bug)
            else:
                bugs_nao_concluidos.append(bug)
        
        print("\n" + "="*80)
        print("📊 ESTATÍSTICAS")
        print("="*80)
        print(f"\n📈 RESUMO:")
        print(f"   • Total de bugs: {len(bugs)}")
        print(f"   • Bugs concluídos: {len(bugs_concluidos)}")
        print(f"   • Bugs NÃO concluídos: {len(bugs_nao_concluidos)}")
        
        if len(bugs) > 0:
            percentual_concluidos = (len(bugs_concluidos) / len(bugs)) * 100
            print(f"   • Taxa de conclusão: {percentual_concluidos:.1f}%")
        
        # Distribuição por status dos bugs NÃO concluídos
        if bugs_nao_concluidos:
            print("\n📊 DISTRIBUIÇÃO DOS BUGS NÃO CONCLUÍDOS POR STATUS:")
            por_status = {}
            for bug in bugs_nao_concluidos:
                status = bug["fields"]["status"]["name"]
                por_status[status] = por_status.get(status, 0) + 1
            
            for status, count in sorted(por_status.items(), key=lambda x: x[1], reverse=True):
                print(f"   • {status}: {count}")
        
        # Listar bugs não concluídos
        if bugs_nao_concluidos:
            print("\n" + "-"*80)
            print("📋 LISTA DE BUGS NÃO CONCLUÍDOS")
            print("-"*80)
            
            for i, bug in enumerate(bugs_nao_concluidos, 1):
                fields = bug['fields']
                key = bug['key']
                summary = fields.get('summary', 'N/A')
                status = fields.get('status', {}).get('name', 'N/A')
                tipo = fields.get('issuetype', {}).get('name', 'N/A')
                created = fields.get('created', 'N/A')[:10] if fields.get('created') else 'N/A'
                due_date = fields.get('duedate', 'N/A')
                priority = fields.get('priority', {}).get('name', 'N/A')
                
                assignee = fields.get('assignee')
                assignee_name = assignee.get('displayName', 'Não atribuído') if assignee else 'Não atribuído'
                
                # Calcular dias desde a criação
                dias_aberto = "N/A"
                if fields.get('created'):
                    try:
                        created_date = datetime.strptime(created, "%Y-%m-%d")
                        dias_aberto = (datetime.now() - created_date).days
                    except:
                        pass
                
                print(f"\n{i:2d}. 🐛 {key} ({tipo})")
                print(f"   📝 {summary[:80]}")
                print(f"   📊 Status: {status}")
                print(f"   📅 Criado: {created} ({dias_aberto} dias atrás)")
                if due_date != 'N/A':
                    print(f"   ⏰ Data limite: {due_date}")
                print(f"   🎯 Prioridade: {priority}")
                print(f"   👤 Responsável: {assignee_name}")
                print("-"*40)
        
        # Bugs com data limite vencida
        bugs_vencidos = []
        for bug in bugs_nao_concluidos:
            due_date = bug['fields'].get('duedate')
            if due_date:
                try:
                    due = datetime.strptime(due_date, "%Y-%m-%d")
                    if due < datetime.now():
                        bugs_vencidos.append(bug)
                except:
                    pass
        
        if bugs_vencidos:
            print(f"\n⚠️ BUGS COM DATA LIMITE VENCIDA ({len(bugs_vencidos)}):")
            for b in bugs_vencidos:
                key = b['key']
                due = b['fields'].get('duedate')
                status = b['fields']['status']['name']
                print(f"   • {key}: venceu em {due} (status: {status})")
        
        # Sugestão para integração
        print("\n" + "="*80)
        print("💡 EXEMPLO DE FUNÇÃO PARA INTEGRAR NO CÓDIGO PRINCIPAL")
        print("="*80)
        print("""
def contar_bugs_abertos_sp():
    '''Conta bugs abertos no projeto SP'''
    
    # Status considerados como "concluídos"
    status_concluidos = [
        "BUG RESOLVIDO", "CANCELADO", "DESPRIORIZADO", 
        "MELHORIA", "MELHORIA RESOLVIDA", "PRODUCT BACKLOG REGISTRADO",
        "Fechado", "Closed", "Resolvido", "Concluído", "Done"
    ]
    
    # Buscar todos os tickets do SP
    data = client.search_issues("project = SP", max_results=500)
    tickets = data.get("issues", [])
    
    # Filtrar apenas bugs
    bugs = [t for t in tickets if "bug" in t["fields"]["issuetype"]["name"].lower()]
    
    # Filtrar bugs abertos
    bugs_abertos = [b for b in bugs if b["fields"]["status"]["name"] not in status_concluidos]
    
    return len(bugs_abertos)
""")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    contar_bugs_sp()