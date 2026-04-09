from config.settings import Settings
from core.jira_client import JiraClient
from services.jql_service import JQLService
from services.okr_service import OKRService
from utils.csv_handler import CSVHandler


def main():
    try:
        Settings.validate()
        
        client = JiraClient()
        if not client.test_connection():
            print("❌ Falha na conexão com Jira")
            return
        
        jql_service = JQLService()
        okr_service = OKRService(jql_service)
        
        print("\n📊 Executando OKRs...")
        
        dados_por_responsavel = okr_service.get_dados_por_responsavel()
        CSVHandler.salvar_todos_csvs(dados_por_responsavel)
        
        print(f"\n💾 CSVs salvos em: {CSVHandler.DATA_DIR}")
        
    except ValueError as e:
        print(f"❌ Erro de configuração: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")


if __name__ == "__main__":
    main()