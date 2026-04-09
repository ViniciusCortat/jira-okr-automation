import csv
from datetime import datetime
from typing import Dict, List
from pathlib import Path
from config.settings import Settings


class CSVHandler:
    DATA_DIR = Settings.DATA_DIR
    
    @classmethod
    def _get_csv_path(cls, responsavel: str) -> Path:
        """Retorna o caminho do CSV para uma pessoa específica"""
        return cls.DATA_DIR / f"{responsavel}_okr.csv"
    
    @classmethod
    def _get_existing_columns(cls, responsavel: str) -> List[str]:
        csv_path = cls._get_csv_path(responsavel)
        
        if not csv_path.exists():
            return []
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            try:
                return next(reader)
            except StopIteration:
                return []
    
    @classmethod
    def append_metrics(cls, dados_responsavel: Dict):
        responsavel = dados_responsavel.get("responsavel")
        if not responsavel:
            return
        
        csv_path = cls._get_csv_path(responsavel)
        valores = dados_responsavel["valores"]
        data_coleta = dados_responsavel["data_coleta"]
        sprint = dados_responsavel["sprint"]
        
        colunas_base = ["data_coleta", "sprint"]
        
        colunas_existentes = cls._get_existing_columns(responsavel)
        colunas_atuais = list(valores.keys())
        
        todas_colunas = colunas_base.copy()
        for col in colunas_existentes:
            if col not in todas_colunas and col not in colunas_base:
                todas_colunas.append(col)
        for col in colunas_atuais:
            if col not in todas_colunas and col not in colunas_base:
                todas_colunas.append(col)
        
        row = {"data_coleta": data_coleta, "sprint": sprint, **valores}
        
        existing_data = []
        if csv_path.exists():
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                existing_data = list(reader)
        
        existing_data.append(row)
        
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=todas_colunas)
            writer.writeheader()
            writer.writerows(existing_data)
        
        print(f"   ✓ Dados salvos em: {csv_path}")
    
    @classmethod
    def salvar_todos_csvs(cls, dados_por_responsavel: Dict[str, Dict]):
        for responsavel, dados in dados_por_responsavel.items():
            dados["responsavel"] = responsavel
            cls.append_metrics(dados)