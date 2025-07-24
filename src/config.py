import os
from pathlib import Path

class Config:
    """Konfigurace pro OCR projekt"""
    
    # Azure Document Intelligence nastavení
    AZURE_ENDPOINT = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT", "https://ctec.cognitiveservices.azure.com/")
    AZURE_KEY = os.getenv("AZURE_FORM_RECOGNIZER_KEY", "YOUR_KEY_HERE")
    MODEL_ID = os.getenv("AZURE_MODEL_ID", "pokus1")
    
    # Cesty k složkám
    PROJECT_ROOT = Path(__file__).parent.parent
    INPUT_DIR = PROJECT_ROOT / "data" / "input"
    PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
    OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
    
    # Image processing nastavení
    MAX_FILE_SIZE_MB = 4
    
    # Google Sheets nastavení (pro později)
    GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "")
    GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "")
    
    # Logging
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @classmethod
    def validate_azure_config(cls):
        """Zkontroluje že Azure konfigurace je kompletní"""
        if cls.AZURE_ENDPOINT == "YOUR_ENDPOINT_HERE":
            raise ValueError("AZURE_ENDPOINT není nastaven! Nastavte proměnnou prostředí nebo upravte config.py")
        if cls.AZURE_KEY == "YOUR_KEY_HERE":
            raise ValueError("AZURE_KEY není nastaven! Nastavte proměnnou prostředí nebo upravte config.py")
        return True
    
    @classmethod
    def setup_directories(cls):
        """Vytvoří potřebné složky pokud neexistují"""
        cls.INPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Pro snadné použití
def get_config():
    """Vrátí konfiguraci s kontrolou"""
    Config.validate_azure_config()
    Config.setup_directories()
    return Config 