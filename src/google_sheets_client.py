import logging
import json
import csv
from datetime import datetime
from pathlib import Path
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Konfigurace logování
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleSheetsClient:
    def __init__(self, credentials_file='google-credentials.json'):
        """
        Inicializace Google Sheets klienta
        
        Args:
            credentials_file: Cesta k JSON souboru s Service Account klíči
        """
        self.credentials_file = credentials_file
        self.service = None
        self.spreadsheet_id = None
        self.processed_files_db = Path("processed_files.txt")
        self.duplicates_log = Path("duplicates_log.txt")
        
        # Scope pro Google Sheets API
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        self._authenticate()
        self._load_processed_files()
    
    def _authenticate(self):
        """Autentizace přes Service Account"""
        try:
            if not Path(self.credentials_file).exists():
                logger.error(f"Soubor s credentials nenalezen: {self.credentials_file}")
                logger.info("Vytvořte Service Account v Google Cloud Console a stáhněte JSON klíč")
                return False
            
            credentials = Credentials.from_service_account_file(
                self.credentials_file, 
                scopes=self.scopes
            )
            
            self.service = build('sheets', 'v4', credentials=credentials)
            logger.info("✅ Google Sheets API připojeno")
            return True
            
        except Exception as error:
            logger.error(f"❌ Chyba autentizace: {error}")
            return False
    
    def _load_processed_files(self):
        """Načte seznam už zpracovaných souborů"""
        self.processed_files = set()
        
        if self.processed_files_db.exists():
            try:
                with open(self.processed_files_db, 'r', encoding='utf-8') as f:
                    for line in f:
                        filename = line.strip()
                        if filename:
                            self.processed_files.add(filename)
                logger.info(f"📋 Načteno {len(self.processed_files)} už zpracovaných souborů")
            except Exception as e:
                logger.warning(f"Chyba čtení databáze: {e}")
        else:
            logger.info("📋 Databáze zpracovaných souborů neexistuje, vytvořím novou")
            self.processed_files_db.touch()
    
    def _add_to_processed(self, filename):
        """Přidá soubor do databáze zpracovaných"""
        if filename not in self.processed_files:
            self.processed_files.add(filename)
            try:
                with open(self.processed_files_db, 'a', encoding='utf-8') as f:
                    f.write(f"{filename}\n")
                logger.info(f"✅ Zaevidován: {filename}")
            except Exception as e:
                logger.error(f"❌ Chyba zápisu do databáze: {e}")

    def create_spreadsheet(self, title="OCR Výsledky"):
        """Vytvoří nový Google Sheets dokument"""
        try:
            spreadsheet = {
                'properties': {
                    'title': title
                },
                'sheets': [{
                    'properties': {
                        'title': 'OCR Data'
                    }
                }]
            }
            
            result = self.service.spreadsheets().create(body=spreadsheet).execute()
            self.spreadsheet_id = result['spreadsheetId']
            
            logger.info(f"✅ Vytvořen Google Sheets: {result['properties']['title']}")
            logger.info(f"📊 Spreadsheet ID: {self.spreadsheet_id}")
            logger.info(f"🔗 URL: https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}")
            
            return self.spreadsheet_id
            
        except HttpError as error:
            logger.error(f"❌ Chyba vytváření Sheets: {error}")
            return None

    def upload_csv_data(self, csv_file_path, sheet_name='Sheet1'):
        """Nahraje data z CSV do Google Sheets"""
        try:
            # Načtení CSV dat
            data = []
            with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
                csv_reader = csv.reader(csvfile)
                for row in csv_reader:
                    data.append(row)
            
            if not data:
                logger.error("CSV soubor je prázdný")
                return False
            
            # Příprava dat pro Google Sheets API
            body = {
                'values': data
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A1",
                valueInputOption='RAW',
                body=body
            ).execute()
            
            logger.info(f"✅ Nahráno {len(data)} řádků do Google Sheets")
            logger.info(f"📊 Aktualizováno buněk: {result.get('updatedCells')}")
            
            return True
            
        except Exception as error:
            logger.error(f"❌ Chyba nahrávání CSV: {error}")
            return False

    def upload_azure_json_data(self, json_dir='data/output', sheet_name='Sheet1'):
        """Nahraje jen specifické sloupce z Azure JSON dat s kontrolou duplikátů"""
        try:
            # Načtení JSON souborů
            json_dir = Path(json_dir)
            json_files = list(json_dir.glob("*_analysis.json"))
            
            if not json_files:
                logger.error(f"Žádné JSON soubory nenalezeny v {json_dir}")
                return False
            
            # Definice požadovaných sloupců (v pořadí jak chceš)
            required_fields = [
                "Typ kotle",
                "výrobní číslo kotle", 
                "prodejce kotle",
                "adresa prodejce",
                "kupující kotle jmeno",
                "adresa zákazníka",
                "datum uvedení do provozu",
                "číslo oprávnění",
                "regulátor",
                "adresa zakaznika doplneni"
            ]
            
            # Kontrola duplikátů a třídění souborů
            new_files = []
            duplicate_files = []
            
            for json_file in json_files:
                filename = json_file.name
                if filename in self.processed_files:
                    duplicate_files.append(filename)
                    logger.warning(f"⚠️ DUPLIKÁT: {filename} (už byl zpracován)")
                else:
                    new_files.append(json_file)
            
            # Zobrazení statistik
            logger.info(f"📊 KONTROLA DUPLIKÁTŮ:")
            logger.info(f"  Celkem souborů: {len(json_files)}")
            logger.info(f"  Nových k nahrání: {len(new_files)}")
            logger.info(f"  Duplikátů přeskočeno: {len(duplicate_files)}")
            
            # Záznam do log souboru pro zpětnou kontrolu
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"\n=== {timestamp} ===\n"
            log_entry += f"Celkem souborů: {len(json_files)}\n"
            log_entry += f"Nových k nahrání: {len(new_files)}\n"
            log_entry += f"Duplikátů přeskočeno: {len(duplicate_files)}\n"
            
            if duplicate_files:
                logger.warning(f"🚫 DUPLIKÁTY NEBUDOU NAHRÁNY:")
                log_entry += "DUPLIKÁTY:\n"
                for dup in duplicate_files:
                    logger.warning(f"  - {dup}")
                    log_entry += f"  - {dup}\n"
            
            if new_files:
                log_entry += "NOVÉ SOUBORY:\n"
                for new_file in new_files:
                    log_entry += f"  + {new_file.name}\n"
            
            # Uložení do log souboru
            try:
                with open(self.duplicates_log, 'a', encoding='utf-8') as f:
                    f.write(log_entry)
                logger.info(f"📝 Záznam uložen do: {self.duplicates_log}")
            except Exception as e:
                logger.warning(f"⚠️ Chyba zápisu do logu: {e}")
            
            if not new_files:
                logger.info("✅ Žádné nové soubory k nahrání")
                return True
            
            # Načtení pouze nových JSON dat
            json_data = []
            for json_file in new_files:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    json_data.append(data)
            
            logger.info(f"📄 Nahrávám {len(json_data)} nových souborů do Google Sheets")
            
            # Vytvoření hlavičky - název souboru + požadované sloupce
            headers = ["nazev_souboru"] + required_fields
            
            # Vytvoření řádků dat
            rows = [headers]  # Hlavička
            
            for data in json_data:
                row = []
                
                # Název souboru jako první
                row.append(data.get("source_file", ""))
                
                # Data z Azure extracted_fields
                extracted_fields = data.get("extracted_fields", {})
                
                # Pro každý požadovaný sloupec
                for field_name in required_fields:
                    value = extracted_fields.get(field_name, "")
                    row.append(value)
                
                rows.append(row)
            
            # Nahrání dat do Google Sheets
            body = {'values': rows}
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range="A1",
                valueInputOption='RAW',
                body=body
            ).execute()
            
            logger.info(f"✅ Nahráno {len(rows)} řádků do Google Sheets")
            logger.info(f"📊 Aktualizováno buněk: {result.get('updatedCells')}")
            
            # Zaevidování nových souborů do databáze
            for json_file in new_files:
                self._add_to_processed(json_file.name)
            
            logger.info(f"📋 Zaevidováno {len(new_files)} nových souborů do databáze")
            
            return True
            
        except Exception as error:
            logger.error(f"❌ Chyba nahrávání JSON dat: {error}")
            return False
    


def main():
    """Hlavní funkce pro nahrání OCR dat do Google Sheets"""
    logger.info("🚀 Spouštím Google Sheets nahrávání...")
    
    # Inicializace klienta
    client = GoogleSheetsClient()
    
    if not client.service:
        logger.error("❌ Nepodařilo se připojit k Google Sheets API")
        logger.info("\n📋 POSTUP NASTAVENÍ:")
        logger.info("1. Jděte do Google Cloud Console")
        logger.info("2. Vytvořte Service Account")
        logger.info("3. Stáhněte JSON klíč jako 'google-credentials.json'")
        logger.info("4. Umístěte soubor do této složky")
        return
    
    # Použití existujícího spreadsheetu místo vytváření nového
    client.spreadsheet_id = "129XnRNQytuHbvSE3NEa6evVdzlFGDjCRwKxXG58sZfA"
    logger.info(f"✅ Používám existující spreadsheet: {client.spreadsheet_id}")
    
    # Nahrání Azure JSON dat přímo s původními názvy polí
    success = client.upload_azure_json_data(json_dir='data/output', sheet_name='umístění kotlů')
    
    if success:
        logger.info("\n🎉 ÚSPĚCH! Data nahrána do Google Sheets")
        logger.info(f"🔗 Otevřete: https://docs.google.com/spreadsheets/d/{client.spreadsheet_id}")
        

        
    else:
        logger.error("❌ Nepodařilo se nahrát data")

if __name__ == "__main__":
    main() 