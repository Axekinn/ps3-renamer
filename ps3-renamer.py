import os
import re
import logging
import pandas as pd
import csv
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple, List

class PS3FileRenamer:
    def __init__(self, csv_file_path: str, directory_path: str, log_file: str = "rename_log.txt"):
        """
        Initialize the PS3 File Renamer
        
        Args:
            csv_file_path: Path to the CSV file containing game information
            directory_path: Path to directory containing .pkg files to rename
            log_file: Path to log file for audit purposes
        """
        self.csv_file_path = csv_file_path
        self.directory_path = Path(directory_path)
        self.log_file = log_file
        self.game_data = {}
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # DEBUG: Afficher le répertoire de travail
        print(f"DEBUG: Répertoire de travail actuel: {os.getcwd()}")
        print(f"DEBUG: Répertoire cible spécifié: {self.directory_path}")
        print(f"DEBUG: Répertoire cible existe: {self.directory_path.exists()}")
        if self.directory_path.exists():
            pkg_count = len(list(self.directory_path.glob("*.pkg")))
            print(f"DEBUG: Nombre de fichiers .pkg trouvés: {pkg_count}")
    
    def load_csv_data(self) -> bool:
        """
        Load game data from CSV file into a mapping of title_id -> list[row_dicts]
        """
        try:
            df = pd.read_csv(self.csv_file_path, dtype=str, keep_default_na=False)
            self.game_data = {}
            for _, row in df.iterrows():
                tid = row.get('Title_ID', '')
                if not tid:
                    continue
                norm_tid = tid.replace('-', '').upper()
                entry = {
                    'Title_ID': tid,
                    'Version': row.get('Version', '').strip(),
                    'Name': row.get('Title_Name', row.get('Sony_Game_Name', '')).strip(),
                    'Editions': row.get('Editions', '').strip(),
                    'Filename': row.get('Filename', '').strip(),
                    'Download_URL': row.get('Download_URL', '').strip()
                }
                self.game_data.setdefault(norm_tid, []).append(entry)
            self.logger.info(f"Loaded {sum(len(v) for v in self.game_data.values())} CSV entries for {len(self.game_data)} title IDs")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load CSV: {e}")
            return False
    
    def extract_title_id_from_filename(self, filename: str) -> Optional[str]:
        """
        Extract title ID from various filename formats
        
        Args:
            filename: The filename to parse
            
        Returns:
            str or None: Extracted title ID or None if not found
        """
        # Pattern 1: EP9000-BCES00011_00-... or UP9000-BCUS98148_00-... format
        pattern1 = r'[A-Z]{2}\d{4}-([A-Z]{4}\d{5})'
        
        # Pattern 2: Direct title ID format BCES-00011 or BCES00011
        pattern2 = r'([A-Z]{4}[-]?\d{5})'
        
        # Pattern 3: More flexible pattern for various formats
        pattern3 = r'([A-Z]{3,4}[-]?\d{4,5})'
        
        # Pattern 4: New pattern for EP9001-BCES00326 format (your specific case)
        pattern4 = r'EP\d{4}-([A-Z]{4}\d{5})'
        
        # Pattern 5: Any BCES/BCUS/BLES/BLUS etc. format
        pattern5 = r'([A-Z]{4}\d{5})'
        
        for pattern in [pattern1, pattern4, pattern2, pattern5, pattern3]:
            match = re.search(pattern, filename)
            if match:
                title_id = match.group(1)
                # Normalize format (add hyphen if missing)
                if len(title_id) == 9 and '-' not in title_id:
                    title_id = f"{title_id[:4]}-{title_id[4:]}"
                return title_id
        
        return None
    
    def extract_version_from_filename(self, filename: str) -> Optional[str]:
        """
        Try to get a version string from filename:
          - A0120 -> 01.20
          - V0600 -> 06.00
          - v1.02 or 1.02 -> keep as-is
        """
        # Try -Axxxx- or Axxxx
        m = re.search(r'-A(\d{4})-|_A(\d{4})_|A(\d{4})', filename, flags=re.IGNORECASE)
        if m:
            digits = next(g for g in m.groups() if g)
            return f"{digits[:2]}.{digits[2:]}"
        # Try V0600 / V0600- etc
        m = re.search(r'V(\d{4})', filename, flags=re.IGNORECASE)
        if m:
            digits = m.group(1)
            return f"{digits[:2]}.{digits[2:]}"
        # Try explicit dotted versions
        m = re.search(r'v?(\d+\.\d+)', filename, flags=re.IGNORECASE)
        if m:
            return m.group(1)
        return None
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Remove invalid characters from filename
        
        Args:
            filename: Original filename
            
        Returns:
            str: Sanitized filename
        """
        # Remove invalid characters for Windows/Unix filenames
        invalid_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(invalid_chars, '', filename)
        # Remove trademark symbols that might cause issues
        sanitized = sanitized.replace('™', '').replace('®', '')
        return sanitized
    
    def generate_new_filename(self, title_id: str, filename: str) -> Optional[str]:
        """
        Choose the right CSV row for this file (handle multiple rows for same Title_ID)
        and generate the final filename using the CSV 'Version' when possible.
        """
        norm_tid = title_id.replace('-', '').upper()
        entries = self.game_data.get(norm_tid)
        if not entries:
            self.logger.debug(f"No CSV entries for {norm_tid}")
            return None

        # If single entry, use it
        chosen = entries[0]
        if len(entries) > 1:
            # Prefer exact filename match (CSV Filename or URL)
            fname_lower = filename.lower()
            for e in entries:
                if e.get('Filename') and e['Filename'].lower() in fname_lower:
                    chosen = e
                    break
                if e.get('Download_URL') and e['Download_URL'].lower() in fname_lower:
                    chosen = e
                    break
            else:
                # Try matching by version extracted from filename (A0120 -> 01.20)
                file_ver = self.extract_version_from_filename(filename)
                if file_ver:
                    for e in entries:
                        if e.get('Version') and e['Version'] == file_ver:
                            chosen = e
                            break
                # otherwise keep the first (or could choose latest)
        # Build name using CSV values only
        game_name = chosen.get('Name') or norm_tid
        version = chosen.get('Version') or ''
        edition = chosen.get('Editions') or ''
        # sanitize components
        game_name = self.sanitize_filename(game_name).strip()
        edition = self.sanitize_filename(edition).strip()
        # Construct filename: prefer format already used in your UI
        new_name = f"{game_name} [UPDATE {version}][{chosen.get('Title_ID')}](axekin.com).pkg" if version else f"{game_name} [{chosen.get('Title_ID')}].pkg"
        return self.sanitize_filename(new_name)
    
    def is_already_formatted(self, filename: str) -> bool:
        """
        Check if filename is already in the correct format
        
        Args:
            filename: Filename to check
            
        Returns:
            bool: True if already formatted correctly
        """
        pattern = r'.+\s\[UPDATE\s[\d.]+\]\[[A-Z]{4}-\d{5}\]\(axekin\.com\)\.pkg$'
        return bool(re.match(pattern, filename))
    
    def verify_file_exists_before_and_after(self, old_path: Path, new_path: Path) -> bool:
        """
        Verify file exists before renaming and check if rename was successful
        """
        print(f"DEBUG: Vérification avant renommage:")
        print(f"  - Fichier source existe: {old_path.exists()}")
        print(f"  - Chemin source: {old_path}")
        print(f"  - Chemin destination: {new_path}")
        print(f"  - Destination existe déjà: {new_path.exists()}")
        
        if not old_path.exists():
            print(f"ERREUR: Le fichier source n'existe pas!")
            return False
            
        return True
    
    def rename_files(self) -> Dict[str, str]:
        """
        Process and rename files in the specified directory
        
        Returns:
            dict: Dictionary of old_filename -> new_filename mappings
        """
        if not self.directory_path.exists():
            self.logger.error(f"Directory not found: {self.directory_path}")
            return {}
        
        print(f"\nDEBUG: Démarrage du renommage dans: {self.directory_path.absolute()}")
        
        renamed_files = {}
        pkg_files = list(self.directory_path.glob("*.pkg"))
        
        if not pkg_files:
            self.logger.warning(f"No .pkg files found in {self.directory_path}")
            return {}
        
        self.logger.info(f"Found {len(pkg_files)} .pkg files to process")
        print(f"DEBUG: Fichiers .pkg trouvés: {len(pkg_files)}")
        
        # Afficher les premiers fichiers pour debug
        print("DEBUG: Premiers fichiers trouvés:")
        for i, file_path in enumerate(pkg_files[:5]):
            print(f"  {i+1}. {file_path.name}")
        
        for file_path in pkg_files:
            filename = file_path.name
            
            # Skip if already formatted
            if self.is_already_formatted(filename):
                self.logger.info(f"Skipping already formatted file: {filename}")
                continue
            
            # Extract title ID
            title_id = self.extract_title_id_from_filename(filename)
            if not title_id:
                self.logger.warning(f"Could not extract title ID from: {filename}")
                continue
            
            # Generate new filename
            new_filename = self.generate_new_filename(title_id, filename)
            if not new_filename:
                continue
            
            # Perform rename
            new_file_path = file_path.parent / new_filename
            
            try:
                if new_file_path.exists():
                    self.logger.warning(f"Target file already exists: {new_filename}")
                    continue
                
                # DEBUG: Vérification avant renommage
                if not self.verify_file_exists_before_and_after(file_path, new_file_path):
                    continue
                
                print(f"DEBUG: Tentative de renommage:")
                print(f"  DE: {file_path}")
                print(f"  VERS: {new_file_path}")
                
                # Effectuer le renommage
                file_path.rename(new_file_path)
                
                # Vérifier que le renommage a réussi
                if new_file_path.exists() and not file_path.exists():
                    renamed_files[filename] = new_filename
                    self.logger.info(f"Renamed: {filename} -> {new_filename}")
                    print(f"✓ SUCCÈS: {filename} -> {new_filename}")
                else:
                    print(f"✗ ÉCHEC: Le renommage a échoué pour {filename}")
                    self.logger.error(f"Rename failed for {filename}")
                
            except PermissionError as e:
                self.logger.error(f"Permission denied renaming {filename}: {e}")
                print(f"✗ ERREUR PERMISSION: {filename} - {e}")
            except Exception as e:
                self.logger.error(f"Error renaming {filename}: {e}")
                print(f"✗ ERREUR: {filename} - {e}")
        
        return renamed_files
    
    def check_directory_permissions(self) -> bool:
        """
        Check if we have write permissions in the target directory
        """
        try:
            test_file = self.directory_path / "test_permissions.tmp"
            test_file.touch()
            test_file.unlink()
            print(f"✓ Permissions d'écriture OK dans: {self.directory_path}")
            return True
        except Exception as e:
            print(f"✗ Pas de permissions d'écriture dans: {self.directory_path}")
            print(f"  Erreur: {e}")
            return False
    
    def run(self) -> bool:
        """
        Main execution method with permission checks
        """
        self.logger.info("Starting PS3 file renaming process")
        
        # Check permissions first
        if not self.check_directory_permissions():
            print("ERREUR: Permissions insuffisantes pour écrire dans le répertoire.")
            print("Essayez de lancer le script avec sudo ou changez les permissions du dossier.")
            return False
        
        # Load CSV data
        if not self.load_csv_data():
            return False
        
        # Simple test with first file
        pkg_files = list(self.directory_path.glob("*.pkg"))
        if pkg_files:
            test_file = pkg_files[0]
            print(f"\nTEST avec le premier fichier: {test_file.name}")
            
            if not self.is_already_formatted(test_file.name):
                title_id = self.extract_title_id_from_filename(test_file.name)
                if title_id:
                    new_name = self.generate_new_filename(title_id, test_file.name)
                    if new_name:
                        print(f"Title ID: {title_id}")
                        print(f"Nouveau nom proposé: {new_name}")
                        
                        # Ask for single file test
                        choice = input(f"\nVoulez-vous tester le renommage sur ce fichier uniquement? (y/n): ").lower().strip()
                        if choice in ['y', 'yes', 'o', 'oui']:
                            new_path = test_file.parent / new_name
                            try:
                                print(f"Renommage de: {test_file}")
                                print(f"Vers: {new_path}")
                                test_file.rename(new_path)
                                print("✓ TEST RÉUSSI!")
                                
                                # Restore original name
                                restore = input("Voulez-vous restaurer le nom original? (y/n): ").lower().strip()
                                if restore in ['y', 'yes', 'o', 'oui']:
                                    new_path.rename(test_file)
                                    print("✓ Nom original restauré")
                                
                            except Exception as e:
                                print(f"✗ TEST ÉCHOUÉ: {e}")
                                return False
        
        # Continue with normal process...
        print("\nVoulez-vous continuer avec tous les fichiers? (y/n): ")
        if input().lower().strip() not in ['y', 'yes', 'o', 'oui']:
            return False
        
        # Perform rename on all files
        renamed_files = self.rename_files()
        
        # Summary
        print(f"\nRÉSULTAT FINAL: {len(renamed_files)} fichiers renommés avec succès")
        return True


def analyze_renaming_issues():
    # Charger le CSV
    df = pd.read_csv('ps3_titles_download_links.csv')
    
    # Répertoire contenant les fichiers PKG
    pkg_directory = Path('.')  # Ajustez le chemin selon votre configuration
    
    # Lister tous les fichiers PKG
    pkg_files = list(pkg_directory.glob('*.pkg'))
    
    print(f"Nombre de fichiers PKG trouvés : {len(pkg_files)}")
    print(f"Nombre d'entrées dans le CSV : {len(df)}")
    
    # Extraire les Title_ID des noms de fichiers
    file_title_ids = set()
    for file in pkg_files:
        # Pattern pour extraire le Title_ID du nom de fichier (BCUS-xxxxx ou BCES-xxxxx)
        match = re.search(r'(B[CU][EU]S-?\d{5})', file.name)
        if match:
            title_id = match.group(1).replace('-', '')  # Supprimer le tiret si présent
            file_title_ids.add(title_id)
    
    # Title_ID du CSV (nettoyer les tirets)
    csv_title_ids = set(df['Title_ID'].str.replace('-', ''))
    
    # Analyser les différences
    files_not_in_csv = file_title_ids - csv_title_ids
    csv_not_in_files = csv_title_ids - file_title_ids
    common_title_ids = file_title_ids & csv_title_ids
    
    print(f"\nAnalyse des Title_ID :")
    print(f"- Title_ID communs : {len(common_title_ids)}")
    print(f"- Title_ID dans les fichiers mais pas dans le CSV : {len(files_not_in_csv)}")
    print(f"- Title_ID dans le CSV mais pas dans les fichiers : {len(csv_not_in_files)}")
    
    if files_not_in_csv:
        print(f"\nTitle_ID dans les fichiers mais absents du CSV :")
        for tid in sorted(files_not_in_csv)[:10]:  # Afficher les 10 premiers
            print(f"  - {tid}")
    
    if csv_not_in_files:
        print(f"\nTitle_ID dans le CSV mais absents des fichiers :")
        for tid in sorted(csv_not_in_files)[:10]:  # Afficher les 10 premiers
            print(f"  - {tid}")
    
    return df, pkg_files, common_title_ids

def improved_rename_files():
    df, pkg_files, common_title_ids = analyze_renaming_issues()
    
    # Créer un dictionnaire de mapping Title_ID -> Informations du jeu
    title_mapping = {}
    for _, row in df.iterrows():
        title_id = row['Title_ID'].replace('-', '')
        title_mapping[title_id] = {
            'name': row['Title_Name'],
            'sony_name': row['Sony_Game_Name'],
            'edition': row['Editions'],
            'version': row['Version']
        }
    
    renamed_count = 0
    failed_renames = []
    
    for file in pkg_files:
        # Extraire le Title_ID du fichier
        match = re.search(r'(B[CU][EU]S-?\d{5})', file.name)
        if not match:
            failed_renames.append(f"Pas de Title_ID trouvé dans : {file.name}")
            continue
            
        title_id = match.group(1).replace('-', '')
        
        if title_id not in title_mapping:
            failed_renames.append(f"Title_ID {title_id} non trouvé dans le CSV : {file.name}")
            continue
        
        # Récupérer les informations du jeu
        game_info = title_mapping[title_id]
        
        # Nettoyer le nom du jeu pour le nom de fichier
        clean_name = re.sub(r'[<>:"/\\|?*]', '', game_info['name'])
        clean_name = clean_name.strip()
        
        # Construire le nouveau nom de fichier
        new_name = f"{title_id} - {clean_name}"
        
        # Ajouter la version si disponible
        if game_info['version'] and game_info['version'] != 'nan':
            new_name += f" v{game_info['version']}"
        
        # Ajouter l'édition si différente de "Original"
        if game_info['edition'] and game_info['edition'] not in ['Original', 'nan']:
            new_name += f" ({game_info['edition']})"
        
        new_name += '.pkg'
        new_path = file.parent / new_name
        
        # Éviter les doublons
        counter = 1
        original_new_path = new_path
        while new_path.exists() and new_path != file:
            new_path = file.parent / f"{original_new_path.stem} ({counter}){original_new_path.suffix}"
            counter += 1
        
        try:
            file.rename(new_path)
            renamed_count += 1
            print(f"✓ Renommé : {file.name} -> {new_path.name}")
        except Exception as e:
            failed_renames.append(f"Erreur lors du renommage de {file.name} : {e}")
    
    print(f"\n=== RÉSUMÉ ===")
    print(f"Fichiers renommés avec succès : {renamed_count}")
    print(f"Échecs de renommage : {len(failed_renames)}")
    
    if failed_renames:
        print(f"\nDétails des échecs :")
        for failure in failed_renames[:20]:  # Afficher les 20 premiers échecs
            print(f"  - {failure}")

def main():
    """
    Main function to run the renamer
    """
    print("PS3 File Renamer - Version Debug")
    print("="*50)
    
    # Configuration
    csv_file_path = "/home/admin/Downloads/ps3-update-scraper-main/ps3_titles_updates/ps3_titles_download_links.csv"
    
    if not Path(csv_file_path).exists():
        print(f"Error: CSV file not found: {csv_file_path}")
        return
    
    directory_path = input("Enter the path to the folder containing .pkg files: ").strip()
    
    if not directory_path:
        print("No path provided. Stopping program.")
        return
    
    if not Path(directory_path).exists():
        print(f"Error: Folder not found: {directory_path}")
        return
    
    # Create renamer instance
    renamer = PS3FileRenamer(csv_file_path, directory_path)
    
    # Load CSV data
    if not renamer.load_csv_data():
        return
    
    # Run with debug
    success = renamer.run()
    
    if success:
        print("\nRenaming completed successfully!")
    else:
        print("\nErrors were encountered. Check the debug output above.")
    
    # D'abord analyser le problème
    print("=== ANALYSE DU PROBLÈME ===")
    analyze_renaming_issues()
    
    print("\n" + "="*50)
    print("=== RENOMMAGE AMÉLIORÉ ===")
    
    # Demander confirmation
    response = input("\nVoulez-vous procéder au renommage ? (o/n): ")
    if response.lower() in ['o', 'oui', 'y', 'yes']:
        improved_rename_files()
    else:
        print("Renommage annulé.")


if __name__ == "__main__":
    main()