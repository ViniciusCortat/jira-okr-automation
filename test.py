"""
testar_novas_vs_total.py
Testa a comparação entre hotfix de novas funcionalidades vs total
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.auth import OAuth2Client
import requests
from datetime import datetime, timedelta

def testar_novas_vs_total():
    CAMPO_FUNCIONALIDADE = "customfield_10338"
    NOVAS_FUNCIONALIDADES = ["Precificar", "Dashboard V2", "Comprar V2"]
    
    print("="*80)
    print("🔍 TESTE: NOVAS FUNCIONALIDADES VS TOTAL")
    print("="*80)
    print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    try:
        auth = OAuth2Client()
        headers = auth.get_headers()
        base_url = auth.get_base_url()
        
        # Calcular semana anterior (para ter dados)
        hoje = datetime.now()
        dias_para_segunda = hoje.weekday()
        segunda_esta_semana = (hoje - timedelta(days=dias_para_segunda)).replace(hour=0, minute=0, second=0)
        segunda_passada = segunda_esta_semana - timedelta(days=7)
        domingo_passado = segunda_passada + timedelta(days=6)
        
        print(f"\n📅 Período: {segunda_passada.strftime('%d/%m/%Y')} → {domingo_passado.strftime('%d/%m/%Y')}")
        
        # Buscar releases da semana passada
        url_releases = f"{base_url}/rest/api/3/project/PC/versions"
        response = requests.get(url_releases, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Erro ao buscar releases: {response.status_code}")
            return
        
        versions = response.json()
        releases_semana = []
        
        for v in versions:
            release_date = v.get('releaseDate')
            if release_date and v.get('released', False):
                try:
                    data_release = datetime.strptime(release_date, "%Y-%m-%d")
                    if segunda_passada <= data_release <= domingo_passado:
                        releases_semana.append(v)
                except:
                    pass
        
        print(f"\n📦 Releases na semana: {len(releases_semana)}")
        for r in releases_semana:
            print(f"   • {r['name']} - {r['releaseDate']}")
        
        if not releases_semana:
            print("\n⚠️ Nenhuma release encontrada")
            return
        
        total_hotfix = 0
        novas_hotfix = 0
        detalhes = []
        
        for release in releases_semana:
            nome = release.get('name')
            jql = f'project = PC AND fixVersion = "{nome}" AND type = Hotfix'
            url = f"{base_url}/rest/api/3/search/jql"
            params = {
                "jql": jql,
                "maxResults": 100,
                "fields": f"key,summary,{CAMPO_FUNCIONALIDADE}"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                issues = data.get("issues", [])
                total_hotfix += len(issues)
                
                for issue in issues:
                    key = issue['key']
                    campo = issue["fields"].get(CAMPO_FUNCIONALIDADE)
                    valor = None
                    
                    if campo and isinstance(campo, dict):
                        valor = campo.get("value", "")
                    
                    is_nova = valor in NOVAS_FUNCIONALIDADES
                    
                    if is_nova:
                        novas_hotfix += 1
                    
                    detalhes.append({
                        "key": key,
                        "release": nome,
                        "funcionalidade": valor or "(vazio)",
                        "is_nova": is_nova
                    })
        
        print(f"\n📊 RESULTADOS:")
        print(f"   • Total de hotfixes: {total_hotfix}")
        print(f"   • Hotfix de NOVAS funcionalidades: {novas_hotfix}")
        print(f"\n   📈 FORMATO: {novas_hotfix} - {total_hotfix}")
        
        print(f"\n📋 DETALHES:")
        for item in detalhes:
            nova_marcador = "🆕" if item["is_nova"] else "  "
            print(f"   {nova_marcador} {item['key']} - {item['release']}")
            print(f"      Funcionalidade: {item['funcionalidade']}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    testar_novas_vs_total()