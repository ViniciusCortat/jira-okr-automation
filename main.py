from config.settings import Settings
from core.jira_client import JiraClient
from services.jql_service import JQLService
from services.okr_service import OKRService
from utils.csv_handler import CSVHandler
from datetime import datetime

def main():
    try:
        Settings.validate()
        
        client = JiraClient()
        if not client.test_connection():
            print("❌ Falha na conexão com Jira")
            return
        
        jql_service = JQLService()
        okr_service = OKRService(jql_service)
        
        # Pega o nome do CICLO (sem sufixos)
        nome_ciclo = jql_service.get_nome_ciclo()
        
        if not nome_ciclo:
            print("📭 Nenhuma sprint ativa encontrada")
            return
        
        print(f"\n📊 Ciclo: {nome_ciclo}")
        
        resultados = okr_service.executar_okrs()
        
        print(f"\n📈 OKRs EXECUTADOS HOJE:")
        for nome, dados in resultados.items():
            print(f"   • {nome}: {dados['valor']}")
        
        metrics = jql_service.get_sprint_metrics_dict()
        CSVHandler.append_metrics(nome_ciclo, metrics)
        
        print(f"\n💾 Dados salvos em: {CSVHandler.CSV_FILE}")
        
    except ValueError as e:
        print(f"❌ Erro de configuração: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

if __name__ == "__main__":
    main()