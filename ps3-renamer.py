import os
import csv
import re
import logging
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
    
    def load_csv_data(self) -> bool:
        """
        Load game data from CSV file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.csv_file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                
                for row in csv_reader:
                    # Extract data from specific columns based on the CSV structure
                    title_id = row.get('Title_ID', '').strip()
                    title_name = row.get('Title_Name', '').strip()
                    sony_game_name = row.get('Sony_Game_Name', '').strip()
                    version = row.get('Version', '').strip()
                    
                    # Use Sony_Game_Name if available, otherwise use Title_Name
                    game_name = sony_game_name if sony_game_name else title_name
                    
                    if title_id:
                        self.game_data[title_id] = {
                            'name': game_name or 'Unknown Game',
                            'version': version or '01.00'
                        }
                
                self.logger.info(f"Loaded {len(self.game_data)} games from CSV")
                return True
                
        except Exception as e:
            self.logger.error(f"Error loading CSV file: {e}")
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
        
        for pattern in [pattern1, pattern2, pattern3]:
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
        Extract version from filename if available
        
        Args:
            filename: The filename to parse
            
        Returns:
            str or None: Extracted version or None if not found
        """
        # Look for version patterns like V0600, v01.00, A0126, etc.
        patterns = [
            r'V(\d{4})',  # V0600 format
            r'v(\d+\.\d+)',  # v01.00 format
            r'_(\d+\.\d+)_',  # _01.00_ format
            r'-A(\d{4})-',  # -A0126- format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                version = match.group(1)
                # Convert 4-digit format to decimal
                if len(version) == 4 and '.' not in version:
                    version = f"{version[:2]}.{version[2:]}"
                return version
        
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
        Generate new filename based on CSV data
        
        Args:
            title_id: Game title ID
            filename: Original filename
            
        Returns:
            str or None: New filename or None if data not found
        """
        # Look for game data by title ID (try different formats)
        game_info = None
        title_id_variations = [
            title_id,
            title_id.replace('-', ''),
            f"{title_id[:4]}-{title_id[4:]}" if '-' not in title_id else title_id.replace('-', '')
        ]
        
        for tid_var in title_id_variations:
            if tid_var in self.game_data:
                game_info = self.game_data[tid_var]
                break
        
        if not game_info:
            self.logger.warning(f"No game data found for title ID: {title_id}")
            return None
        
        game_name = game_info['name']
        version = game_info['version']
        
        # Try to extract version from filename if CSV version is default
        filename_version = self.extract_version_from_filename(filename)
        if filename_version and version == '01.00':
            version = filename_version
        
        # Format the new filename
        new_filename = f"{game_name} [UPDATE {version}][{title_id}].pkg"
        return self.sanitize_filename(new_filename)
    
    def is_already_formatted(self, filename: str) -> bool:
        """
        Check if filename is already in the correct format
        
        Args:
            filename: Filename to check
            
        Returns:
            bool: True if already formatted correctly
        """
        pattern = r'.+\s\[UPDATE\s[\d.]+\]\[[A-Z]{4}-\d{5}\]\.pkg$'
        return bool(re.match(pattern, filename))
    
    def preview_rename_operations(self) -> List[Tuple[str, str, str]]:
        """
        Preview what files will be renamed without actually renaming them
        
        Returns:
            List of tuples (old_filename, new_filename, status)
        """
        if not self.directory_path.exists():
            self.logger.error(f"Directory not found: {self.directory_path}")
            return []
        
        preview_operations = []
        pkg_files = list(self.directory_path.glob("*.pkg"))
        
        if not pkg_files:
            self.logger.warning(f"No .pkg files found in {self.directory_path}")
            return []
        
        for file_path in pkg_files:
            filename = file_path.name
            
            # Check if already formatted
            if self.is_already_formatted(filename):
                preview_operations.append((filename, filename, "SKIP - Already formatted"))
                continue
            
            # Extract title ID
            title_id = self.extract_title_id_from_filename(filename)
            if not title_id:
                preview_operations.append((filename, "", "ERROR - Could not extract title ID"))
                continue
            
            # Generate new filename
            new_filename = self.generate_new_filename(title_id, filename)
            if not new_filename:
                preview_operations.append((filename, "", "ERROR - No game data found"))
                continue
            
            # Check if target file already exists
            new_file_path = file_path.parent / new_filename
            if new_file_path.exists():
                preview_operations.append((filename, new_filename, "WARNING - Target file already exists"))
                continue
            
            preview_operations.append((filename, new_filename, "READY"))
        
        return preview_operations
    
    def create_backup(self) -> bool:
        """
        Create a backup of all .pkg files
        
        Returns:
            bool: True if backup successful, False otherwise
        """
        backup_dir = self.directory_path / "backup_before_rename"
        
        try:
            backup_dir.mkdir(exist_ok=True)
            pkg_files = list(self.directory_path.glob("*.pkg"))
            
            for file_path in pkg_files:
                if file_path.parent != backup_dir:  # Don't backup files already in backup dir
                    backup_file_path = backup_dir / file_path.name
                    shutil.copy2(file_path, backup_file_path)
            
            self.logger.info(f"Backup created in: {backup_dir}")
            print(f"✓ Backup created in: {backup_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating backup: {e}")
            print(f"✗ Error creating backup: {e}")
            return False
    
    def rename_files(self) -> Dict[str, str]:
        """
        Process and rename files in the specified directory
        
        Returns:
            dict: Dictionary of old_filename -> new_filename mappings
        """
        if not self.directory_path.exists():
            self.logger.error(f"Directory not found: {self.directory_path}")
            return {}
        
        renamed_files = {}
        pkg_files = list(self.directory_path.glob("*.pkg"))
        
        if not pkg_files:
            self.logger.warning(f"No .pkg files found in {self.directory_path}")
            return {}
        
        self.logger.info(f"Found {len(pkg_files)} .pkg files to process")
        
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
                
                file_path.rename(new_file_path)
                renamed_files[filename] = new_filename
                self.logger.info(f"Renamed: {filename} -> {new_filename}")
                
            except Exception as e:
                self.logger.error(f"Error renaming {filename}: {e}")
        
        return renamed_files
    
    def run(self) -> bool:
        """
        Main execution method with preview and backup options
        
        Returns:
            bool: True if successful, False otherwise
        """
        self.logger.info("Starting PS3 file renaming process")
        
        # Load CSV data
        if not self.load_csv_data():
            return False
        
        # Preview rename operations
        print("\n" + "="*80)
        print("PREVIEW MODE - Analyzing files for renaming...")
        print("="*80)
        
        preview_operations = self.preview_rename_operations()
        
        if not preview_operations:
            print("No files found to process.")
            return True
        
        # Display preview
        ready_count = 0
        skip_count = 0
        error_count = 0
        warning_count = 0
        
        print(f"\nFound {len(preview_operations)} files to analyze:\n")
        
        for old_name, new_name, status in preview_operations:
            if status == "READY":
                print(f"✓ READY: {old_name}")
                print(f"    --> {new_name}")
                ready_count += 1
            elif status.startswith("SKIP"):
                print(f"⏭ SKIP: {old_name} ({status})")
                skip_count += 1
            elif status.startswith("WARNING"):
                print(f"⚠ WARNING: {old_name}")
                print(f"    --> {new_name} ({status})")
                warning_count += 1
            elif status.startswith("ERROR"):
                print(f"✗ ERROR: {old_name} ({status})")
                error_count += 1
            print()
        
        # Summary
        print("="*80)
        print("SUMMARY:")
        print(f"  Files ready to rename: {ready_count}")
        print(f"  Files to skip: {skip_count}")
        print(f"  Files with warnings: {warning_count}")
        print(f"  Files with errors: {error_count}")
        print("="*80)
        
        if ready_count == 0 and warning_count == 0:
            print("No files need to be renamed.")
            return True
        
        # Ask for backup
        print("\nBACKUP OPTION:")
        print("A backup creates a safety copy of all your .pkg files in a")
        print("'backup_before_rename' folder before proceeding with renaming. This allows you to")
        print("restore the original names in case of any issues.")
        print()
        
        while True:
            backup_choice = input("Do you want to create a backup before renaming? (y/n): ").lower().strip()
            if backup_choice in ['y', 'yes', 'o', 'oui']:
                if not self.create_backup():
                    print("Failed to create backup. Stopping process.")
                    return False
                break
            elif backup_choice in ['n', 'no', 'non']:
                print("No backup will be created.")
                break
            else:
                print("Please answer 'y' (yes) or 'n' (no)")
        
        # Confirm rename operation
        print(f"\nDo you want to proceed with renaming {ready_count + warning_count} files?")
        while True:
            confirm = input("Confirm renaming? (y/n): ").lower().strip()
            if confirm in ['y', 'yes', 'o', 'oui']:
                break
            elif confirm in ['n', 'no', 'non']:
                print("Operation cancelled.")
                return False
            else:
                print("Please answer 'y' (yes) or 'n' (no)")
        
        # Perform rename
        print("\nRenaming in progress...")
        renamed_files = self.rename_files()
        
        # Summary
        print("\n" + "="*80)
        print("RESULTS:")
        self.logger.info(f"Process completed. Renamed {len(renamed_files)} files.")
        print(f"Files successfully renamed: {len(renamed_files)}")
        
        if renamed_files:
            print("\nRenamed files:")
            for old_name, new_name in renamed_files.items():
                print(f"  {old_name}")
                print(f"  --> {new_name}")
                print()
        
        print("="*80)
        return True


def main():
    """
    Main function to run the renamer
    """
    print("PS3 File Renamer - Automatic Renaming Tool")
    print("="*50)
    
    # Configuration - use the correct CSV file path
    csv_file_path = "/home/admin/Downloads/ps3-update-scraper-main/ps3_titles_updates/ps3_titles_download_links.csv"
    
    # Check if CSV file exists
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
    
    # Create renamer instance and run
    renamer = PS3FileRenamer(csv_file_path, directory_path)
    success = renamer.run()
    
    if success:
        print("\nRenaming completed successfully!")
    else:
        print("\nErrors were encountered. Check the log file for more details.")


if __name__ == "__main__":
    main()