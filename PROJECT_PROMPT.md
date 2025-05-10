# Prompt for Coding Agent (e.g., Gemini 2.5 Pro)
## Project: `sfx-batch` - CLI Tool for Batch Sound Effects Generation (using `elevenlabs-sfx` library)

## 1. Project Goal & Overview

You are tasked with developing `sfx-batch`, a robust and user-friendly Python Command-Line Interface (CLI) tool. This tool will enable users to batch-generate sound effects from text prompts provided in a CSV file. Crucially, `sfx-batch` will **utilize the `elevenlabs-sfx` library** (which is a separate project, assumed to be in development concurrently or already available) to handle all direct interactions with the ElevenLabs API.

The `sfx-batch` CLI tool should be inspired by the functionality of the original `elevenbatch` project but will focus exclusively on sound effects generation, leveraging the abstractions provided by the `elevenlabs-sfx` library.

## 2. Core Functional Requirements

### 2.1. CSV Input Processing
-   **File Format:** Process semicolon-delimited (`;`) CSV files.
-   **Encoding:** Must correctly handle UTF-8 encoded files, including those with a Byte Order Mark (BOM).
-   **Header Row:** Automatically skip the first (header) row of the CSV.
-   **Prompt Extraction:**
    -   Allow the user to specify the column containing the text prompts via a CLI argument (either by column name or 0-based index).
    -   Remove any surrounding double quotes (`"`) from the extracted text prompts.

### 2.2. Sound Effect Generation Orchestration (via `elevenlabs-sfx` library)
-   For each relevant row and extracted prompt in the CSV:
    -   Call the appropriate sound generation function (e.g., `generate_sound_effect`) from the `elevenlabs-sfx` library.
    -   Pass the necessary parameters:
        -   The resolved API key.
        -   The text prompt.
        -   User-specified or default `duration_seconds`.
        -   User-specified or default `prompt_influence`.
        -   (The `elevenlabs-sfx` library will handle its own default for `output_format`).
-   Handle audio data (`bytes`) returned by the `elevenlabs-sfx` library.

### 2.3. API Key Management
-   **Primary Source:** Obtain the ElevenLabs API key from the `ELEVENLABS_API_KEY` environment variable.
-   **Fallback:** Offer a CLI argument (`--api-key TEXT`) if the environment variable is not set. This key will be passed to the `elevenlabs-sfx` library.
-   **Error Handling:** If no API key is available (neither via environment variable nor CLI argument), the tool should exit gracefully with a clear error message *before* attempting to use the `elevenlabs-sfx` library.

### 2.4. Output Management
-   **File Format:** Save each generated sound effect (received as `bytes` from `elevenlabs-sfx`) as an MP3 file.
-   **Output Directory:**
    -   Allow users to specify an output directory via a CLI argument (`--output-dir DIRECTORY`).
    -   Default: `./sfx_output/`.
    -   The script must create the output directory if it does not already exist.
-   **Filename Generation:**
    -   Derive filenames from the original text prompt.
    -   Sanitize prompts to create valid, filesystem-safe filenames:
        -   Replace spaces and common problematic characters (e.g., `/`, `\`, `:`, `*`, `?`, `"`, `<`, `>`, `|`) with underscores (`_`).
        -   Remove any remaining non-alphanumeric characters (except underscores and periods).
        -   Convert to lowercase.
        -   Truncate to a maximum length of 150 characters (before adding `.mp3` and any collision suffix).
    -   **Filename Collisions:** If a file with the target name already exists, append a unique sequential number before the extension (e.g., `sound.mp3`, `sound_1.mp3`, `sound_2.mp3`).

### 2.5. Command-Line Interface (CLI)
-   **Framework:** Implement the CLI using `typer` or `click` for a modern and user-friendly experience.
-   **Required Arguments:**
    -   `CSV_FILE`: Positional argument for the path to the input CSV file.
    -   `--prompt-column TEXT_COLUMN`: The name or 0-based integer index of the column in the CSV file that contains the text prompts.
-   **Optional Arguments:**
    -   `--api-key TEXT`: Your ElevenLabs API key. (Overrides `ELEVENLABS_API_KEY` env var if both are present).
    -   `--output-dir DIRECTORY`: Directory to save the generated MP3 files. (Default: `./sfx_output/`)
    -   `--duration FLOAT`: Duration of the sound effect in seconds (0.5-22.0). (Default: `5.0`). This will be passed to `elevenlabs-sfx`.
    -   `--prompt-influence FLOAT`: Influence of the prompt on the generation (0.0-1.0). (Default: `0.3`). This will be passed to `elevenlabs-sfx`.
    -   `--max-retries INTEGER`: Maximum number of retry attempts for API calls (this will configure the retry mechanism within `elevenlabs-sfx`). (Default: `3`, Range: 0-10).
    -   `--verbose` / `-v`: Enable verbose logging for progress and detailed information.
    -   `--debug`: Enable debug level logging for troubleshooting.

## 3. Technical Specifications

-   **Language:** Python 3.8 or higher.
-   **Key Dependencies:**
    -   `elevenlabs-sfx`: The core library for ElevenLabs API interaction. During development, this library is assumed to be located at `../elevenlabs-sfx` relative to the `sfx-batch` project directory and should be installable from that local path. For distribution, it will be a versioned dependency from PyPI.
    -   `typer` (or `click`): For building the CLI.
-   **Interaction with `elevenlabs-sfx`:**
    ```python
    # Example of how sfx-batch might use elevenlabs-sfx
    import elevenlabs_sfx # Assuming the library is installed and importable
    # ... (resolve API key, get parameters from CLI) ...

    try:
        # Assuming elevenlabs_sfx provides a client or functions to be called.
        # The exact instantiation will depend on elevenlabs_sfx's API design.
        # For example, if it has a client:
        sfx_client = elevenlabs_sfx.SFXClient(api_key=resolved_api_key, max_retries=cli_max_retries) 
        audio_bytes = sfx_client.generate_sound_effect(
            text=prompt_text,
            duration_seconds=duration_val,
            prompt_influence=influence_val
        )
        # Or if it's a direct function call:
        # audio_bytes = elevenlabs_sfx.generate_sound_effect(
        # api_key=resolved_api_key,
        # text=prompt_text,
        # duration_seconds=duration_val,
        # prompt_influence=influence_val,
        # max_retries=cli_max_retries
        # )
        # ... then write audio_bytes to an MP3 file ...
    except elevenlabs_sfx.ElevenLabsAPIKeyError as e:
        # Log user-friendly error: Invalid API Key
        # Exit gracefully
    except elevenlabs_sfx.ElevenLabsRateLimitError as e:
        # Log user-friendly error: Rate limit hit, try again later or reduce batch size.
        # Potentially suggest adjusting --max-retries if applicable
    except elevenlabs_sfx.ElevenLabsParameterError as e:
        # Log user-friendly error: Invalid parameter for sound generation (e.g. duration out of range)
    except elevenlabs_sfx.ElevenLabsGenerationError as e:
        # Log user-friendly error: Failed to generate sound for prompt X.
    except Exception as e:
        # Log generic error for unexpected issues.
    ```

## 4. Error Handling and Logging (CLI Tool Specifics)

-   **User-Friendly Error Messages:** Translate exceptions from `elevenlabs-sfx` into clear, actionable messages for the end-user.
-   **File System Errors:** Handle `FileNotFoundError` for the input CSV file and permission errors for the output directory.
-   **CSV Processing Errors:**
    -   Validate that the specified `--prompt-column` exists in the CSV.
    -   Handle malformed CSV rows gracefully (e.g., skip and warn, or halt with an error, configurable behavior might be an advanced feature).
-   **CLI Argument Validation:** Validate inputs provided via CLI arguments (e.g., ensure `--duration` is a float) before passing them to `elevenlabs-sfx` if the library itself doesn't do initial type checks.
-   **Logging:**
    -   Use the standard Python `logging` module.
    -   **INFO Level (Default):**
        -   "Processing CSV: [filename.csv]"
        -   "Generating sound for prompt: '[prompt_text_snippet]'"
        -   "Saved: [./path/to/output_file.mp3]"
        -   Summary at the end (e.g., "Successfully generated X sound effects. Y failures.").
    -   **VERBOSE Level (`-v`):** More detailed progress, e.g., which row is being processed.
    -   **DEBUG Level (`--debug`):** Detailed logs, potentially including parameters passed to `elevenlabs-sfx` and raw responses if helpful for debugging `sfx-batch` itself.
-   **Exit Codes:** Return appropriate non-zero exit codes on critical errors that prevent the tool from completing its task.

## 5. Packaging and Distribution

-   **Project Structure:** Follow standard Python project layout.
-   **`pyproject.toml`:**
    -   Include a `pyproject.toml` file (using Poetry, PDM, Hatch, or standard setuptools).
    -   List dependencies:
        -   For development: `elevenlabs-sfx = {path = "../elevenlabs-sfx", develop = true}` (adjust based on your chosen build tool, e.g., Poetry).
        -   For distribution: `elevenlabs-sfx >= X.Y.Z` (versioned dependency from PyPI).
        -   `typer` (or `click`)
-   **Console Script Entry Point:** Configure the project so it can be installed (e.g., via `pip install .` or `pip install sfx-batch`) and the `sfx-batch` command can be run directly.
-   **Publishable to PyPI:** Structure the project to be potentially publishable to PyPI.

## 6. Documentation (README.md for `sfx-batch`)

Create a comprehensive `README.md` file including:
-   **Project Overview:** What `sfx-batch` does and its reliance on `elevenlabs-sfx`.
-   **Features:** Bullet list of key functionalities.
-   **Installation:**
    -   **For users:** How to install `sfx-batch` (e.g., `pip install sfx-batch`). This should also install `elevenlabs-sfx` as a dependency from PyPI.
    -   **For developers:** "Clone both `sfx-batch` and `elevenlabs-sfx` repositories. Ensure `elevenlabs-sfx` is located at `../elevenlabs-sfx` relative to the `sfx-batch` project directory. Install `sfx-batch` in editable mode (e.g., `pip install -e .` from within the `sfx-batch` directory), which should pick up the local `elevenlabs-sfx` if specified correctly in `pyproject.toml`."
    -   Python version requirements.
-   **API Key Setup:**
    -   Clear instructions on obtaining an ElevenLabs API key.
    -   How to set the `ELEVENLABS_API_KEY` environment variable (recommended).
    -   Mention the `--api-key` CLI option.
-   **Usage:**
    -   Detailed explanation of all CLI arguments and options.
    -   Multiple usage examples:
        ```bash
        # Example 1: Basic usage (API key via env var)
        export ELEVENLABS_API_KEY="your_api_key"
        sfx-batch prompts.csv --prompt-column "description"

        # Example 2: Specifying output, duration, and influence
        sfx-batch input_data.csv --prompt-column 0 --output-dir "my_sounds" --duration 3.5 --prompt-influence 0.75

        # Example 3: Using --api-key argument
        sfx-batch sound_list.csv --prompt-column "SFX_Prompt" --api-key "your_api_key_here" --verbose
        ```
-   **CSV File Format:**
    -   Explain that the input must be a semicolon-delimited CSV.
    -   Mention that the first row is treated as a header and skipped.
    -   Provide a small example of a valid CSV file structure:
        ```csv
        SFX_Prompt;Notes;TargetFile
        "A loud thunder clap with rain";For storm scene;"thunder_clap.mp3"
        "Gentle wind blowing through trees";Ambient background;"forest_wind.mp3"
        ```
-   **Troubleshooting:** Common issues and solutions (e.g., API key errors, CSV format issues).
-   **Contributing (Optional):** If open to contributions.
-   **License:** Specify the license.

## 7. Testing (for `sfx-batch`)

-   **Testing Framework:** Use `pytest` or `unittest`.
-   **Unit Tests:**
    -   Test CSV parsing logic.
    -   Test CLI argument parsing and validation.
    -   Test filename sanitization and output directory creation.
-   **Integration Tests:**
    -   **Mock `elevenlabs-sfx`:** Extensively mock the `elevenlabs-sfx` library to simulate its behavior (successful sound generation, various exceptions it might raise). This allows testing `sfx-batch`'s orchestration and error handling logic without making actual API calls.
    -   Test that `sfx-batch` correctly passes parameters to the mocked `elevenlabs-sfx`.
-   **End-to-End Tests (Minimal & Controlled):**
    -   Use sample CSV files.
    -   Test the full flow with a thoroughly mocked `elevenlabs-sfx` that returns predictable byte data for "generated" sounds.
    -   Verify correct MP3 file creation, naming, and that the (mocked) content is written.

## 8. Deliverables

-   A fully functional Python CLI tool named `sfx-batch`.
-   A comprehensive `README.md` file as specified above.
-   Well-commented, clean, and maintainable Python code adhering to PEP 8 guidelines.
-   The `pyproject.toml` file and any other necessary packaging files for `sfx-batch`.
-   A robust suite of unit and integration tests for `sfx-batch`.

## 9. Reference to Core Library

This `sfx-batch` tool depends on the `elevenlabs-sfx` Python library, which handles all direct communication with the ElevenLabs API. Ensure `elevenlabs-sfx` is developed and available as a dependency, ideally from `../elevenlabs-sfx` during local development.

---

Please proceed with the development of the `sfx-batch` CLI tool following these specifications, assuming the `elevenlabs-sfx` library is or will be available.
