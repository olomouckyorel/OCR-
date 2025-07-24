import os
import shutil
from PIL import Image
from pathlib import Path
import logging

# Nastavení loggingu
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FilePreprocessor:
    def __init__(self, max_size_mb=4):
        """
        Inicializace file preprocessoru pro přípravu souborů před blob uploadem
        
        Args:
            max_size_mb (int): Maximální velikost souboru v MB
        """
        self.max_size_bytes = max_size_mb * 1024 * 1024
        
    def get_file_size(self, file_path):
        """Získá velikost souboru v bytech"""
        return os.path.getsize(file_path)
    
    def needs_compression(self, file_path):
        """Zkontroluje zda soubor potřebuje kompresi"""
        size = self.get_file_size(file_path)
        return size > self.max_size_bytes
    
    def compress_image(self, input_path, output_path, quality=85):
        """
        Komprimuje obrázek zachováním rozumné kvality
        
        Args:
            input_path (str): Cesta k původnímu souboru
            output_path (str): Cesta k výstupnímu souboru
            quality (int): Kvalita komprese (1-100)
        """
        try:
            with Image.open(input_path) as img:
                # Pokud je obrázek velmi velký, zmenšíme rozměry
                if img.width > 2000 or img.height > 2000:
                    img.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
                    logger.info(f"🔄 Zmenšil rozměry obrázku: {input_path}")
                
                # Konverze na RGB pokud je RGBA
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img)
                    img = background
                
                # Uložení s kompresí
                img.save(output_path, 'JPEG', quality=quality, optimize=True)
                
                # Kontrola výsledné velikosti
                new_size = self.get_file_size(output_path)
                if new_size > self.max_size_bytes:
                    # Pokud je stále moc velký, zkusíme nižší kvalitu
                    quality -= 10
                    if quality > 20:
                        return self.compress_image(input_path, output_path, quality)
                    else:
                        logger.warning(f"⚠️ Nepodařilo se zmenšit soubor pod {self.max_size_bytes/1024/1024}MB: {output_path}")
                
                logger.info(f"✅ Komprese: {self.get_file_size(input_path)/1024/1024:.2f}MB → {new_size/1024/1024:.2f}MB")
                return True
                
        except Exception as e:
            logger.error(f"❌ Chyba při kompresi {input_path}: {str(e)}")
            return False
    
    def process_file(self, input_path, output_dir):
        """
        Zpracuje jeden soubor - zkontroluje velikost, zkomprimuje pokud potřeba, přesune
        
        Args:
            input_path (str): Cesta k vstupnímu souboru
            output_dir (str): Výstupní složka
            
        Returns:
            bool: True pokud bylo zpracování úspěšné
        """
        input_path = Path(input_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Kontrola velikosti
        original_size_mb = self.get_file_size(input_path) / 1024 / 1024
        
        if self.needs_compression(input_path):
            logger.info(f"📏 Soubor {input_path.name} je {original_size_mb:.2f}MB (> 4MB), komprimuji...")
            
            # Pro komprimované soubory použijeme .jpg příponu
            output_filename = input_path.stem + "_compressed.jpg"
            output_path = output_dir / output_filename
            
            success = self.compress_image(str(input_path), str(output_path))
            if success:
                # Komprese úspěšná, smažeme originál
                os.remove(str(input_path))
                logger.info(f"✅ Komprimován a přesunut: {input_path.name} → {output_filename}")
            else:
                # Pokud komprese selhala, přesuneme původní soubor
                output_path = output_dir / input_path.name
                shutil.move(str(input_path), str(output_path))
                logger.warning(f"⚠️ Komprese selhala, přesouvám původní soubor: {input_path.name}")
        else:
            # Soubor je dostatečně malý, pouze přesuneme
            output_path = output_dir / input_path.name
            shutil.move(str(input_path), str(output_path))
            logger.info(f"✅ Soubor {input_path.name} ({original_size_mb:.2f}MB) je v pořádku, přesouvám bez změn")
            
        return True
    
    def process_rawdata_to_input(self, rawdata_dir="data/rawdata", input_dir="data/input"):
        """
        Zpracuje všechny soubory z rawdata do input složky
        
        Args:
            rawdata_dir (str): Složka s raw daty
            input_dir (str): Složka pro připravené soubory
            
        Returns:
            dict: Statistiky zpracování
        """
        rawdata_path = Path(rawdata_dir)
        input_path = Path(input_dir)
        
        if not rawdata_path.exists():
            logger.error(f"❌ Složka {rawdata_dir} neexistuje!")
            return {"error": "Rawdata složka neexistuje"}
        
        # Vytvoření input složky
        input_path.mkdir(parents=True, exist_ok=True)
        
        # Statistiky
        total_files = 0
        processed_files = 0
        compressed_files = 0
        copied_files = 0
        total_size_before = 0
        total_size_after = 0
        
        # Podporované formáty
        supported_formats = {'.jpg', '.jpeg', '.png', '.pdf', '.tiff', '.tif', '.bmp'}
        
        logger.info("🚀 === SPOUŠTÍM PREPROCESSING SOUBORŮ ===")
        
        for file_path in rawdata_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in supported_formats:
                total_files += 1
                file_size_before = self.get_file_size(file_path)
                total_size_before += file_size_before
                
                try:
                    if self.needs_compression(file_path):
                        compressed_files += 1
                    else:
                        copied_files += 1
                    
                    success = self.process_file(file_path, input_path)
                    if success:
                        processed_files += 1
                        
                        # Spočítej velikost po zpracování
                        output_file = input_path / (file_path.stem + "_compressed.jpg" if self.needs_compression(file_path) else file_path.name)
                        if output_file.exists():
                            total_size_after += self.get_file_size(output_file)
                        
                except Exception as e:
                    logger.error(f"❌ Chyba při zpracování {file_path}: {str(e)}")
        
        # Výsledné statistiky
        stats = {
            "total_files": total_files,
            "processed_files": processed_files,
            "compressed_files": compressed_files,
            "copied_files": copied_files,
            "size_before_mb": total_size_before / 1024 / 1024,
            "size_after_mb": total_size_after / 1024 / 1024,
            "space_saved_mb": (total_size_before - total_size_after) / 1024 / 1024,
            "compression_ratio": (1 - total_size_after/total_size_before) * 100 if total_size_before > 0 else 0
        }
        
        logger.info("🎉 === PREPROCESSING DOKONČEN ===")
        logger.info(f"📊 Zpracováno: {stats['processed_files']}/{stats['total_files']} souborů")
        logger.info(f"🗜️ Komprimováno: {stats['compressed_files']} souborů")
        logger.info(f"📋 Zkopírováno bez změn: {stats['copied_files']} souborů")
        logger.info(f"💾 Velikost před: {stats['size_before_mb']:.1f}MB")
        logger.info(f"💾 Velikost po: {stats['size_after_mb']:.1f}MB")
        logger.info(f"💰 Ušetřeno místa: {stats['space_saved_mb']:.1f}MB ({stats['compression_ratio']:.1f}%)")
        
        return stats

# Ukázkové použití
if __name__ == "__main__":
    preprocessor = FilePreprocessor(max_size_mb=4)
    
    print("🔧 === FILE PREPROCESSOR ===")
    print("Zpracovávám soubory z rawdata/ do input/")
    print("Soubory > 4MB budou komprimovány")
    print()
    
    stats = preprocessor.process_rawdata_to_input(
        rawdata_dir="data/rawdata",
        input_dir="data/input"
    )
    
    if "error" not in stats:
        print(f"\n✅ HOTOVO!")
        print(f"Soubory jsou připravené ve složce data/input/")
        print(f"Můžete pokračovat blob uploadem")
    else:
        print(f"\n❌ CHYBA: {stats['error']}") 