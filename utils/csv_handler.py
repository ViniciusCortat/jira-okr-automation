import csv
from datetime import datetime
from typing import Dict, List
from config.settings import Settings

class CSVHandler:
    CSV_FILE = Settings.DATA_DIR / "sprint_metrics.csv"
    
    NOVOS_CAMPOS = [
        "data_coleta",
        "sprint",
        "total_tarefas",
        "taxa_conclusao",
        "tarefas_nao_aprovadas",
        "bugs_proatividade",
        "bugs_reprovados_qa",
        "quantidade_deploy",
        "bugs_dentro_sla",
        "total_bugs_48h_15"
    ]
    
    ANTIGOS_CAMPOS = [
        "data_coleta",
        "ciclo",
        "total_tarefas",
        "taxa_conclusao",
        "tarefas_nao_aprovadas",
        "bugs_proatividade",
        "bugs_reprovados_qa"
    ]
    
    @classmethod
    def _detectar_formato_csv(cls) -> List[str]:
        if not cls.CSV_FILE.exists():
            return cls.NOVOS_CAMPOS
        
        with open(cls.CSV_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            try:
                cabecalho = next(reader)
                if "ciclo" in cabecalho:
                    return cls.ANTIGOS_CAMPOS
                return cls.NOVOS_CAMPOS
            except StopIteration:
                return cls.NOVOS_CAMPOS
    
    @classmethod
    def load_existing_data(cls) -> List[Dict]:
        if not cls.CSV_FILE.exists():
            return []
        
        with open(cls.CSV_FILE, 'r', encoding='utf-8') as f:
            return list(csv.DictReader(f))
    
    @classmethod
    def append_metrics(cls, nome_sprint: str, metrics: Dict):
        campos = cls._detectar_formato_csv()
        
        linha_base = {
            "data_coleta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_tarefas": metrics["total_tarefas"],
            "taxa_conclusao": f"{metrics['taxa_conclusao']:.2f}",
            "tarefas_nao_aprovadas": metrics["tarefas_nao_aprovadas"],
            "bugs_proatividade": metrics["bugs_proatividade"],
            "bugs_reprovados_qa": metrics["bugs_reprovados_qa"],
            "quantidade_deploy": metrics.get("quantidade_deploy", 0),
            "bugs_dentro_sla": f"{metrics.get('bugs_dentro_sla', 0):.2f}",
            "total_bugs_48h_15": metrics.get("total_bugs_48h_15", 0)
        }
        
        if "ciclo" in campos:
            linha_base["ciclo"] = nome_sprint
        else:
            linha_base["sprint"] = nome_sprint
        
        data = cls.load_existing_data()
        data.append(linha_base)
        
        with open(cls.CSV_FILE, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=campos)
            writer.writeheader()
            writer.writerows(data)