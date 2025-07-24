import os
import json
import logging
import time
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

from config import Config

# Nastavení loggingu
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AzureOCRClient:
    """Klient pro Azure Document Intelligence API"""
    
    def __init__(self, config: Config = None):
        """
        Inicializace Azure OCR klienta
        
        Args:
            config: Konfigurace (pokud není zadána, použije se výchozí)
        """
        if config is None:
            config = Config
            
        self.config = config
        self.endpoint = config.AZURE_ENDPOINT
        self.key = config.AZURE_KEY
        self.model_id = config.MODEL_ID
        
        # Vytvoření klienta
        self.client = DocumentIntelligenceClient(
            endpoint=self.endpoint,
            credential=AzureKeyCredential(self.key)
        )
        
        logger.info(f"Azure OCR klient inicializován s modelem: {self.model_id}")
    
    def analyze_document_from_file(self, file_path: str) -> Optional[Dict]:
        """
        Analyzuje dokument ze souboru
        
        Args:
            file_path: Cesta k souboru
            
        Returns:
            Dict s výsledky analýzy nebo None při chybě
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"Soubor neexistuje: {file_path}")
                return None
                
            logger.info(f"Analyzuji dokument: {file_path.name}")
            
            # Otevření a odeslání souboru
            with open(file_path, "rb") as file:
                poller = self.client.begin_analyze_document(
                    model_id=self.model_id,
                    body=file,
                    content_type="application/octet-stream"
                )
                
            result = poller.result()
            logger.info(f"Analýza dokončena pro: {file_path.name}")
            
            return self._process_result(result, file_path.name)
            
        except Exception as e:
            logger.error(f"Chyba při analýze {file_path}: {str(e)}")
            return None
    
    def analyze_document_from_url(self, document_url: str) -> Optional[Dict]:
        """
        Analyzuje dokument z URL
        
        Args:
            document_url: URL dokumentu
            
        Returns:
            Dict s výsledky analýzy nebo None při chybě
        """
        try:
            logger.info(f"Analyzuji dokument z URL: {document_url}")
            
            poller = self.client.begin_analyze_document(
                self.model_id,
                AnalyzeDocumentRequest(url_source=document_url)
            )
            
            result = poller.result()
            logger.info(f"Analýza z URL dokončena")
            
            return self._process_result(result, document_url)
            
        except Exception as e:
            logger.error(f"Chyba při analýze URL {document_url}: {str(e)}")
            return None
    
    def _process_result(self, result, source_name: str) -> Dict:
        """
        Zpracuje výsledek z Azure API do strukturovaného formátu
        
        Args:
            result: Výsledek z Azure API
            source_name: Název zdroje (soubor/URL)
            
        Returns:
            Strukturovaný slovník s výsledky
        """
        processed_result = {
            "source_file": source_name,
            "status": "success",
            "model_id": result.model_id,
            "api_version": result.api_version,
            "extracted_fields": {},
            "raw_content": result.content if hasattr(result, 'content') else "",
            "confidence_scores": {},
            "document_count": len(result.documents) if result.documents else 0
        }
        
        # Zpracování extrahovaných polí z dokumentů
        if result.documents:
            for idx, document in enumerate(result.documents):
                logger.info(f"Zpracovávám dokument #{idx + 1}, typ: {document.doc_type}, confidence: {document.confidence}")
                
                # Extrakce polí
                if document.fields:
                    for field_name, field in list(document.fields.items()):
                        if field.content:
                            processed_result["extracted_fields"][field_name] = field.content
                            processed_result["confidence_scores"][field_name] = field.confidence
                            
                            logger.info(f"Pole '{field_name}': '{field.content}' (confidence: {field.confidence:.2%})")
        
        return processed_result
    
    def extract_key_fields(self, analysis_result: Dict) -> Dict:
        """
        Extrahuje klíčové informace ze záručního listu
        
        Args:
            analysis_result: Výsledek analýzy
            
        Returns:
            Dict s klíčovými poli
        """
        fields = analysis_result.get("extracted_fields", {})
        
        # Mapování polí na standardní názvy
        key_fields = {
            "jmeno_zakaznika": fields.get("kupující kotle jméno", ""),
            "adresa_zakaznika": fields.get("adresa zákazníka", "") or fields.get("adresa zákazníka doplneni", ""),
            "datum_instalace": fields.get("datum uvedení do provozu", ""),
            "typ_kotle": fields.get("Typ kotle", ""),
            "vyrobni_cislo": fields.get("výrobní číslo kotle", ""),
            "prodejce": fields.get("prodejce kotle", ""),
            "adresa_prodejce": fields.get("adresa prodejce", ""),
            "regulators": fields.get("regulátor", ""),
            "cislo_opravneni": fields.get("číslo oprávnění", "")
        }
        
        # Přidání confidence scores
        confidence_scores = analysis_result.get("confidence_scores", {})
        for field_name in list(key_fields.keys()):
            # Najdi odpovídající confidence score
            for original_field, confidence in confidence_scores.items():
                if any(keyword in original_field.lower() for keyword in self._get_field_keywords(field_name)):
                    key_fields[f"{field_name}_confidence"] = confidence
                    break
        
        return key_fields
    
    def _get_field_keywords(self, field_name: str) -> List[str]:
        """Vrátí klíčová slova pro mapování polí"""
        keywords_map = {
            "jmeno_zakaznika": ["kupující", "jméno"],
            "adresa_zakaznika": ["adresa zákazníka", "adresa"],
            "datum_instalace": ["datum", "uvedení", "provozu"],
            "typ_kotle": ["typ", "kotle"],
            "vyrobni_cislo": ["výrobní", "číslo"],
            "prodejce": ["prodejce"],
            "adresa_prodejce": ["adresa prodejce"],
            "regulators": ["regulátor"],
            "cislo_opravneni": ["oprávnění"]
        }
        return keywords_map.get(field_name, [field_name])
    
    def process_directory(self, input_dir: str, output_dir: str) -> List[Dict]:
        """
        Zpracuje všechny dokumenty ve složce
        
        Args:
            input_dir: Vstupní složka s dokumenty
            output_dir: Výstupní složka pro JSON výsledky
            
        Returns:
            Seznam výsledků analýzy
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        results = []
        supported_formats = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp'}
        
        # Vytvoření processed složky
        processed_path = Path("data/processed")
        processed_path.mkdir(parents=True, exist_ok=True)
        
        for file_path in input_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in supported_formats:
                # Analýza dokumentu
                result = self.analyze_document_from_file(str(file_path))
                
                if result:
                    # Extrakce klíčových polí
                    key_fields = self.extract_key_fields(result)
                    result["key_fields"] = key_fields
                    
                    # Uložení výsledku do JSON
                    output_file = output_path / f"{file_path.stem}_analysis.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"Výsledek uložen: {output_file}")
                    
                    # 🔄 PŘESUN ZPRACOVANÉHO SOUBORU
                    try:
                        processed_file = processed_path / file_path.name
                        shutil.move(str(file_path), str(processed_file))
                        logger.info(f"✅ Soubor přesunut: {file_path.name} → data/processed/")
                        result["moved_to_processed"] = True
                    except Exception as e:
                        logger.warning(f"⚠️ Chyba přesunu souboru {file_path.name}: {e}")
                        result["moved_to_processed"] = False
                    
                else:
                    # Záznam neúspěšné analýzy
                    result = {
                        "source_file": file_path.name,
                        "status": "failed",
                        "error": "Analýza se nezdařila",
                        "moved_to_processed": False
                    }
                
                results.append(result)
                
                # Přidáme pauzu mezi požadavky aby nedošlo k rate limitu
                time.sleep(2)
        
        logger.info(f"Zpracováno {len(results)} souborů")
        return results

# Ukázkové použití
if __name__ == "__main__":
    try:
        # Test konfigurace
        Config.validate_azure_config()
        
        # Vytvoření klienta
        ocr_client = AzureOCRClient()
        
        # Test na zpracovaných souborech
        input_folder = "data/input"
        output_folder = "data/output"
        
        if os.path.exists(input_folder):
            results = ocr_client.process_directory(input_folder, output_folder)
            
            print(f"\n=== VÝSLEDKY ANALÝZY ===")
            print(f"Zpracováno celkem: {len(results)} souborů")
            
            success_count = sum(1 for r in results if r.get('status') == 'success')
            failed_count = len(results) - success_count
            
            print(f"Úspěšných: {success_count}")
            print(f"Neúspěšných: {failed_count}")
            if len(results) > 0:
                print(f"Úspěšnost: {success_count/len(results)*100:.1f}%")
            else:
                print("Úspěšnost: 0% (žádné soubory nenalezeny)")
            
            # Ukázka extrahovaných dat
            for result in results[:3]:  # Zobraz první 3
                if result.get('status') == 'success':
                    print(f"\n--- {result['source_file']} ---")
                    key_fields = result.get('key_fields', {})
                    for field, value in key_fields.items():
                        if value and not field.endswith('_confidence'):
                            print(f"  {field}: {value}")
        else:
            print(f"Složka {input_folder} neexistuje")
            print("Nejdřív spusťte image_processor.py")
            
    except Exception as e:
        print(f"Chyba: {str(e)}")
        print("Zkontrolujte konfiguraci Azure credentials v config.py") 