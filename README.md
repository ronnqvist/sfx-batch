# `sfx-batch` - Batch Sound Effects Generation CLI

`sfx-batch` is a Python Command-Line Interface (CLI) tool designed to batch-generate sound effects from text prompts. It processes a CSV file containing these prompts and utilizes the `elevenlabs-sfx` library to interact with the ElevenLabs API for sound generation.

This tool is inspired by the `elevenbatch` project but focuses exclusively on sound effects, leveraging the dedicated `elevenlabs-sfx` library.

## Features

*   **CSV Input:** Processes semicolon-delimited (`;`) CSV files.
*   **UTF-8 Support:** Correctly handles UTF-8 encoded files, including those with a Byte Order Mark (BOM).
*   **Flexible Prompt Column:** Specify the prompt column by name or 0-based index.
*   **Automatic Quote Stripping:** Removes surrounding double quotes (`"`) from prompts.
*   **API Key Management:**
    *   Prioritizes `ELEVENLABS_API_KEY` environment variable.
    *   Fallback to `--api-key` CLI argument.
    *   Graceful error if no key is found.
*   **Customizable Output:**
    *   Specify output directory (defaults to `./sfx_output/`).
    *   Directory created automatically if it doesn't exist.
*   **Intelligent Filename Generation:**
    *   Filenames derived from prompts.
    *   Robust sanitization for filesystem safety.
    *   Automatic handling of filename collisions (e.g., `sound.mp3`, `sound_1.mp3`).
*   **Configurable Generation Parameters:**
    *   `--duration`: Set sound effect duration (0.5-22.0s).
    *   `--prompt-influence`: Control prompt influence (0.0-1.0).
    *   `--max-retries`: Configure API call retry attempts.
*   **Logging:**
    *   Standard INFO level logging for key operations.
    *   Optional `--verbose` and `--debug` flags for more detailed output.
*   **User-Friendly CLI:** Built with `Typer` for a modern experience.

## Important Note on Generated Files (Current Version)

*   **Mock Audio Data:** The current version of `sfx-batch` uses an internal mock of the `elevenlabs-sfx` library for development and testing purposes. As a result, the `.mp3` files generated **do not contain actual audio data** but rather placeholder text content.
*   **Integration Required for Real Audio:** To generate real sound effects, `sfx-batch` must be integrated with the actual `elevenlabs-sfx` library. This involves installing the `elevenlabs-sfx` library and updating `sfx-batch/main.py` to import the `SFXClient` and its exceptions from `elevenlabs_sfx` instead of using the internal mock.

## Installation

### For Users

1.  **Ensure Python 3.8+ is installed.**
2.  Install `sfx-batch` using pip. This will also install `elevenlabs-sfx` as a dependency from PyPI (once both are published).
    ```bash
    pip install sfx-batch
    ```
    *(Note: `sfx-batch` and `elevenlabs-sfx` are not yet on PyPI. This is the target command for when they are.)*

### For Developers

1.  **Ensure Python 3.8+ is installed.**
2.  Clone both the `sfx-batch` and `elevenlabs-sfx` repositories.
    ```bash
    git clone https://github.com/yourusername/sfx-batch.git # Replace with actual URL
    git clone https://github.com/yourusername/elevenlabs-sfx.git # Replace with actual URL
    ```
3.  Ensure the `elevenlabs-sfx` repository is located at `../elevenlabs-sfx` relative to the `sfx-batch` project directory, or that `elevenlabs-sfx` is installed in your environment in editable mode.
    ```
    your_projects/
    ├── elevenlabs-sfx/
    └── sfx-batch/
    ```
4.  Navigate to the `elevenlabs-sfx` directory and install it in editable mode:
    ```bash
    cd ../elevenlabs-sfx
    pip install -e .
    cd ../sfx-batch
    ```
5.  Install `sfx-batch` in editable mode from within the `sfx-batch` directory. This will use the locally installed `elevenlabs-sfx`.
    ```bash
    pip install -e .[dev]
    ```
    The `[dev]` extra installs development dependencies like `pytest`.

## API Key Setup

`sfx-batch` requires an ElevenLabs API key to generate sound effects.

1.  **Obtain an API Key:** Sign up or log in at [ElevenLabs](https://elevenlabs.io/) and find your API key in your profile section.
2.  **Set Environment Variable (Recommended):**
    Set the `ELEVENLABS_API_KEY` environment variable to your API key.
    *   On Linux/macOS:
        ```bash
        export ELEVENLABS_API_KEY="your_api_key_here"
        ```
        (Add this line to your `.bashrc`, `.zshrc`, or shell configuration file for persistence.)
    *   On Windows (PowerShell):
        ```powershell
        $env:ELEVENLABS_API_KEY="your_api_key_here"
        ```
        (For persistence, search for "environment variables" in Windows settings.)
3.  **Use CLI Argument (Alternative):**
    You can provide the API key directly using the `--api-key` argument when running the tool. This will override the environment variable if both are set.
    ```bash
    sfx-batch prompts.csv --prompt-column "description" --api-key "your_api_key_here"
    ```
4.  **Using a `.env` File (Alternative):**
    You can place a file named `.env` in the directory where you run `sfx-batch` (or in your project's root directory). `sfx-batch` will automatically load environment variables from this file.
    Create a `.env` file with the following content:
    ```env
    ELEVENLABS_API_KEY="your_api_key_here"
    ```
    **Important:** Add `.env` to your `.gitignore` file to prevent accidentally committing your API key.
    The order of precedence for API key sources is:
    1.  `--api-key` CLI argument.
    2.  Shell environment variable (`ELEVENLABS_API_KEY`).
    3.  Variable defined in the `.env` file.

## Usage

The basic command structure is:
`sfx-batch [OPTIONS] CSV_FILE`

### Arguments & Options

*   `CSV_FILE`: (Required) Path to the input semicolon-delimited (`;`) CSV file.
*   `--prompt-column TEXT_COLUMN` / `-p TEXT_COLUMN`: (Required) The name or 0-based integer index of the column in the CSV file that contains the text prompts.
*   `--delimiter TEXT`: Delimiter character used in the CSV file. (Default: `;`)
*   `--duration-column TEXT_OR_INT`: Optional. Name or 0-based index of the CSV column for per-prompt duration in seconds (0.5-22.0). If provided and a valid value exists in a row, it overrides the global `--duration` for that prompt.
*   `--influence-column TEXT_OR_INT`: Optional. Name or 0-based index of the CSV column for per-prompt influence (0.0-1.0). If provided and a valid value exists in a row, it overrides the global `--prompt-influence` for that prompt.
*   `--api-key TEXT`: Your ElevenLabs API key. Overrides `ELEVENLABS_API_KEY` environment variable.
*   `--output-dir DIRECTORY` / `-o DIRECTORY`: Directory to save the generated MP3 files. (Default: `./sfx_output/`)
*   `--duration FLOAT` / `-d FLOAT`: Global duration of the sound effect in seconds (0.5-22.0). Used if not overridden by `--duration-column`. (Default: `5.0`)
*   `--prompt-influence FLOAT` / `-i FLOAT`: Global influence of the prompt on the generation (0.0-1.0). Used if not overridden by `--influence-column`. (Default: `0.3`)
*   `--max-retries INTEGER` / `-r INTEGER`: Maximum number of retry attempts for API calls (0-10). (Default: `3`)
*   `--verbose` / `-v`: Enable verbose logging for progress and detailed information.
*   `--debug`: Enable debug level logging for troubleshooting.
*   `--help`: Show help message and exit.

### Examples

1.  **Basic usage (API key via environment variable):**
    Assumes `ELEVENLABS_API_KEY` is set.
    ```bash
    # export ELEVENLABS_API_KEY="your_actual_api_key" # If not already set
    sfx-batch prompts.csv --prompt-column "description"
    ```

2.  **Specifying output directory, duration, and influence:**
    ```bash
    sfx-batch input_data.csv --prompt-column 0 --output-dir "my_sounds" --duration 3.5 --prompt-influence 0.75
    ```

3.  **Using `--api-key` argument and verbose logging:**
    ```bash
    sfx-batch sound_list.csv --prompt-column "SFX_Prompt" --api-key "another_api_key_here" --verbose
    ```

## CSV File Format

*   **Delimiter:** The tool defaults to semicolon-delimited (`;`) CSV files. You can specify a different delimiter using the `--delimiter` argument (e.g., `--delimiter ","` for comma-separated files).
*   **Encoding:** The file should be **UTF-8 encoded**. Files with a Byte Order Mark (BOM) are also supported.
*   **Header Row:** The **first row is treated as a header** and is automatically skipped by the tool.
*   **Prompt Column (Required):** You must specify the column containing text prompts using `--prompt-column`.
*   **Optional Columns for Per-Prompt Settings:**
    *   You can optionally include columns in your CSV to specify `duration` and `prompt_influence` for individual sound effects.
    *   Use the `--duration-column` and `--influence-column` CLI arguments to tell `sfx-batch` which columns to use.
    *   If these arguments are provided and a valid value is found in the specified column for a row, it will override the global `--duration` or `--prompt-influence` setting for that specific prompt.
    *   If the columns are not specified, or if a cell in such a column is empty or contains an invalid value, the global CLI settings (or their defaults) will be used, and a warning may be logged.
*   **Quote Stripping:** Surrounding double quotes (`"`) around prompts (and other text values from the CSV) will be automatically removed.

### Example CSV (`prompts.csv` - Semicolon-delimited with optional duration)

```csv
SFX_Prompt;Notes;OptionalDuration
"A loud thunder clap with rain";For storm scene;3.5
"Gentle wind blowing through trees";Ambient background for forest;
"Spaceship door hissing open";Sci-fi project;2.0
"A single, clear bell toll";;5.0
```
To process this file:
```bash
# Using semicolon delimiter (default) and specifying the duration column
sfx-batch prompts.csv --prompt-column "SFX_Prompt" --duration-column "OptionalDuration"

# If the file was comma-delimited:
# sfx-batch prompts.csv --prompt-column "SFX_Prompt" --duration-column "OptionalDuration" --delimiter ","
```
In this example:
- "A loud thunder clap..." will have a duration of 3.5s.
- "Gentle wind..." will use the global `--duration` (default 5.0s) because its `OptionalDuration` cell is empty.
- "Spaceship door..." will have a duration of 2.0s.
- "A single, clear bell toll" will have a duration of 5.0s (from its CSV cell).

## Troubleshooting

*   **API Key Errors:**
    *   "ElevenLabs API key not found...": Ensure `ELEVENLABS_API_KEY` is set correctly or use `--api-key`.
    *   "API Key Error: Invalid API Key" (or similar from `elevenlabs-sfx`): Double-check your API key for typos or validity.
*   **CSV Format Issues:**
    *   "Prompt column name '...' not found...": Verify the column name or index provided with `--prompt-column` matches your CSV header or structure.
    *   "Skipping malformed row...": Check the specified row in your CSV for incorrect delimiter usage or missing columns.
    *   Ensure your CSV is semicolon-delimited, not comma-delimited.
*   **File Not Found:**
    *   "Invalid value for 'CSV_FILE': File '...' does not exist.": Check the path to your CSV file.
*   **Permission Errors:**
    *   "Could not create output directory...": Ensure you have write permissions for the location where `sfx-batch` is trying to create the output directory.
*   **Rate Limit Errors:**
    *   "Rate Limit Error...": You've made too many requests to the ElevenLabs API in a short period. Wait and try again later, or process smaller batches. Consider adjusting `--max-retries`.

## Contributing

(Optional - Add guidelines if you plan to accept contributions.)
Currently, contributions are welcome! Please open an issue to discuss potential changes or submit a pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
(Note: A `LICENSE` file should be added to the repository, typically containing the full MIT License text.)
