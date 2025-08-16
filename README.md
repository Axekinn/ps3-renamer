# PS3 File Renamer

A Python tool designed to automatically rename `.pkg` files for PS3 games using information from a CSV file. This project simplifies the organization of PS3 game update files by assigning them consistent and informative names.
I recommend downloading the CSV file [here](https://github.com/Axekinn/ps3-update-scraper/blob/main/ps3_titles_updates/ps3_titles_download_links.csv) and adjusting the path in the code at the end.

## Features

- Automatic extraction of **Title_ID** and version from `.pkg` files.
- File renaming using data from the CSV file.
- Directory permission checks before renaming.
- Analysis of mismatches between `.pkg` files and CSV entries.
- Handling of duplicates and name conflicts.
- Logging operations for auditing and debugging.

## Requirements

- Python 3.7 or higher
- Python libraries:
  - `pandas`
  - `re`
  - `shutil`
  - `pathlib`

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/Axekinn/ps3-file-renamer.git
   cd ps3-file-renamer
   ```

2. Install Python dependencies:
   ```bash
   pip install pandas
   ```

3. Place your CSV file containing PS3 game information in the project directory. By default, the expected file is `ps3_titles_download_links.csv`.

## Usage

1. Run the main script:
   ```bash
   python ps3-renamer.py
   ```

2. Follow the instructions in the terminal:
   - Enter the path to the directory containing `.pkg` files.
   - Confirm the proposed actions (renaming, analysis, etc.).

3. Renamed files will be saved in the same directory.

## File Naming Format

Files will be renamed using the following format:
```
[Game Name] [UPDATE Version]Title_ID.pkg
```
Example:
```
Call of Duty: Modern Warfare 3 [UPDATE 01.24]BLES-01433.pkg
```

## Debugging and Analysis

The script includes tools to:
- Identify `.pkg` files that do not match CSV entries.
- Generate a report of renaming issues.

## Contributing

Contributions are welcome! If you'd like to improve this project, please open an issue or submit a pull request.

## Author

Created by **Axekinn**.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
