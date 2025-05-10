import typer
from typing_extensions import Annotated
import logging
from pathlib import Path
import os
import csv
import codecs # For BOM handling
from dotenv import load_dotenv
# Import specific components from the actual elevenlabs_sfx library
from elevenlabs_sfx.client import ElevenLabsSFXClient
from elevenlabs_sfx.exceptions import (
    ElevenLabsAPIKeyError,
    ElevenLabsRateLimitError,
    ElevenLabsParameterError,
    ElevenLabsGenerationError,
    # ElevenLabsPermissionError, # Not explicitly handled by sfx-batch currently, will fall into generic Exception
    # ElevenLabsAPIError,      # Not explicitly handled by sfx-batch currently, will fall into generic Exception
)


from .utils import sanitize_filename, get_unique_filepath

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    name="sfx-batch",
    help="CLI tool for batch sound effects generation using the elevenlabs-sfx library.",
    add_completion=False,
)

# Mock definitions are now removed. We will use them from `elevenlabs_sfx` library.
# e.g., elevenlabs_sfx.SFXClient
# e.g., elevenlabs_sfx.ElevenLabsAPIKeyError

def setup_logging(verbose: bool, debug: bool):
    """Configures logging levels based on CLI flags."""
    if debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG) # Set root logger level for other libs if needed
        logger.debug("Debug logging enabled.")
    elif verbose:
        logger.setLevel(logging.INFO) # Default is INFO, but being explicit
        logging.getLogger().setLevel(logging.INFO)
        logger.info("Verbose logging enabled (INFO level).")
    # If neither, default INFO level is already set.


def get_api_key(api_key_arg: str | None) -> str | None:
    """
    Retrieves the ElevenLabs API key.
    Priority:
    1. --api-key CLI argument
    2. ELEVENLABS_API_KEY environment variable
    """
    if api_key_arg:
        logger.debug("Using API key from --api-key argument.")
        return api_key_arg
    
    env_api_key = os.getenv("ELEVENLABS_API_KEY")
    if env_api_key:
        logger.debug("Using API key from ELEVENLABS_API_KEY environment variable.")
        return env_api_key
    
    logger.error("ElevenLabs API key not found. Please set the ELEVENLABS_API_KEY environment variable or use the --api-key argument.")
    return None


@app.command()
def main(
    csv_file: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=False,
            writable=False,
            readable=True,
            resolve_path=True,
            help="Path to the input CSV file (semicolon-delimited, UTF-8).",
        ),
    ],
    prompt_column: Annotated[
        str,
        typer.Option(
            "--prompt-column",
            "-p",
            help="Name or 0-based index of the column in the CSV file containing text prompts.",
        ),
    ],
    delimiter: Annotated[
        str,
        typer.Option(
            "--delimiter",
            help="Delimiter character used in the CSV file.",
        ),
    ] = ";",
    duration_column: Annotated[
        str | None,
        typer.Option(
            "--duration-column",
            help="Optional: Name or 0-based index of the CSV column for per-prompt duration (seconds). Overrides global --duration.",
            show_default=False,
        ),
    ] = None,
    influence_column: Annotated[
        str | None,
        typer.Option(
            "--influence-column",
            help="Optional: Name or 0-based index of the CSV column for per-prompt influence (0.0-1.0). Overrides global --prompt-influence.",
            show_default=False,
        ),
    ] = None,
    api_key: Annotated[
        str | None,
        typer.Option(
            "--api-key",
            help="Your ElevenLabs API key. Overrides ELEVENLABS_API_KEY environment variable.",
            show_default=False, # Default is handled by logic
        ),
    ] = None,
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            "-o",
            help="Directory to save the generated MP3 files.",
            file_okay=False,
            dir_okay=True,
            writable=True,
            resolve_path=True,
        ),
    ] = Path("./sfx_output/"),
    duration: Annotated[
        float,
        typer.Option(
            "--duration",
            "-d",
            min=0.5,
            max=22.0,
            help="Duration of the sound effect in seconds (0.5-22.0).",
        ),
    ] = 5.0,
    prompt_influence: Annotated[
        float,
        typer.Option(
            "--prompt-influence",
            "-i",
            min=0.0,
            max=1.0,
            help="Influence of the prompt on the generation (0.0-1.0).",
        ),
    ] = 0.3,
    max_retries: Annotated[
        int,
        typer.Option(
            "--max-retries",
            "-r",
            min=0,
            max=10,
            help="Maximum number of retry attempts for API calls (0-10).",
        ),
    ] = 3,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose logging for progress and detailed information."),
    ] = False,
    debug: Annotated[
        bool,
        typer.Option("--debug", help="Enable debug level logging for troubleshooting."),
    ] = False,
):
    """
    Generates sound effects in batch from a CSV file using elevenlabs-sfx.
    """
    # Load environment variables from .env file if it exists
    # This will not override existing environment variables by default.
    if load_dotenv():
        logger.debug(".env file loaded.")
    else:
        logger.debug("No .env file found or it is empty.")

    setup_logging(verbose, debug)
    logger.info(f"sfx-batch CLI started. Processing CSV: {csv_file.name}")

    resolved_api_key = get_api_key(api_key)
    if not resolved_api_key:
        logger.error("Exiting due to missing API key.")
        raise typer.Exit(code=1)

    # Create output directory if it doesn't exist
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory: {output_dir.resolve()}")
    except OSError as e:
        logger.error(f"Could not create output directory {output_dir}: {e}")
        raise typer.Exit(code=1)

    # --- Log parameters ---
    logger.info(f"Prompt column specified: {prompt_column}")
    logger.info(f"CSV Delimiter: '{delimiter}'")
    if duration_column:
        logger.info(f"Duration column specified: {duration_column} (Global --duration: {duration}s will be fallback)")
    else:
        logger.info(f"Global sound effect duration: {duration}s (no per-prompt duration column)")
    if influence_column:
        logger.info(f"Influence column specified: {influence_column} (Global --prompt-influence: {prompt_influence} will be fallback)")
    else:
        logger.info(f"Global prompt influence: {prompt_influence} (no per-prompt influence column)")
    logger.info(f"Max retries for API calls: {max_retries}")

    # Initialize the actual SFX client
    try:
        sfx_client = ElevenLabsSFXClient(api_key=resolved_api_key, max_retries=max_retries)
    except ElevenLabsAPIKeyError as e: # Uses the direct import
        logger.error(f"API Key Error: {e}")
        raise typer.Exit(code=1)
    except ImportError: # If elevenlabs_sfx or its submodules are not found (should be caught by pip install)
        logger.error(
            "Failed to import from 'elevenlabs_sfx' library. Ensure it is installed correctly."
        )
        raise typer.Exit(code=1)
    except Exception as e: # Catch other potential initialization errors
        logger.error(f"Unexpected error initializing ElevenLabsSFXClient: {e}")
        if debug:
            logger.exception("Full traceback for SFXClient initialization error:")
        raise typer.Exit(code=1)
    
    generated_count = 0
    failed_count = 0
    
    prompts_data = []
    try:
        # Use 'utf-8-sig' to handle CSVs with BOM
        with open(csv_file, mode='r', encoding='utf-8-sig', newline='') as file:
            reader = csv.reader(file, delimiter=delimiter) # Use specified delimiter
            header = next(reader, None) # Skip header row
            if not header:
                logger.error(f"CSV file '{csv_file.name}' is empty or has no header.")
                raise typer.Exit(code=1)
            
            logger.debug(f"CSV Header: {header}")

            prompt_col_idx = -1
            if prompt_column.isdigit():
                try:
                    prompt_col_idx = int(prompt_column)
                    if not (0 <= prompt_col_idx < len(header)):
                        logger.error(
                            f"Prompt column index {prompt_col_idx} is out of range for CSV file "
                            f"with {len(header)} columns."
                        )
                        raise typer.Exit(code=1)
                except ValueError: # Should not happen due to isdigit(), but defensive
                    logger.error(f"Invalid prompt column index: {prompt_column}")
                    raise typer.Exit(code=1)
            else: # Column name
                try:
                    prompt_col_idx = header.index(prompt_column)
                except ValueError:
                    logger.error(
                        f"Prompt column name '{prompt_column}' not found in CSV header: {header}"
                    )
                    raise typer.Exit(code=1)
            
            logger.info(f"Extracting prompts from column: '{header[prompt_col_idx]}' (index {prompt_col_idx})")

            # Determine indices for optional duration and influence columns
            duration_col_idx = -1
            if duration_column:
                if duration_column.isdigit():
                    try:
                        idx = int(duration_column)
                        if 0 <= idx < len(header):
                            duration_col_idx = idx
                            logger.info(f"Extracting per-prompt duration from column: '{header[idx]}' (index {idx})")
                        else:
                            logger.warning(f"Duration column index {idx} out of range. Will use global --duration.")
                    except ValueError:
                        logger.warning(f"Invalid duration column index '{duration_column}'. Will use global --duration.")
                else: # Column name
                    try:
                        duration_col_idx = header.index(duration_column)
                        logger.info(f"Extracting per-prompt duration from column: '{header[duration_col_idx]}' (index {duration_col_idx})")
                    except ValueError:
                        logger.warning(f"Duration column name '{duration_column}' not found in CSV header. Will use global --duration.")
            
            influence_col_idx = -1
            if influence_column:
                if influence_column.isdigit():
                    try:
                        idx = int(influence_column)
                        if 0 <= idx < len(header):
                            influence_col_idx = idx
                            logger.info(f"Extracting per-prompt influence from column: '{header[idx]}' (index {idx})")
                        else:
                            logger.warning(f"Influence column index {idx} out of range. Will use global --prompt-influence.")
                    except ValueError:
                        logger.warning(f"Invalid influence column index '{influence_column}'. Will use global --prompt-influence.")
                else: # Column name
                    try:
                        influence_col_idx = header.index(influence_column)
                        logger.info(f"Extracting per-prompt influence from column: '{header[influence_col_idx]}' (index {influence_col_idx})")
                    except ValueError:
                        logger.warning(f"Influence column name '{influence_column}' not found in CSV header. Will use global --prompt-influence.")

            for i, row in enumerate(reader):
                current_row_num = i + 2 # 1-based for header, 1-based for rows
                if not row: # Skip empty rows
                    logger.warning(f"Skipping empty row {current_row_num} in {csv_file.name}.")
                    continue
                
                try:
                    text_prompt_raw = row[prompt_col_idx]
                    text_prompt = text_prompt_raw.strip('"')

                    if not text_prompt:
                        logger.warning(f"Skipping row {current_row_num} due to empty prompt in column '{header[prompt_col_idx]}'.")
                        continue

                    # Determine duration for this row
                    row_duration = duration # Start with global default
                    if duration_col_idx != -1:
                        try:
                            duration_str = row[duration_col_idx].strip()
                            if duration_str: # Only process if not empty
                                val = float(duration_str)
                                if 0.5 <= val <= 22.0:
                                    row_duration = val
                                    logger.debug(f"Row {current_row_num}: Using duration from CSV: {val}s")
                                else:
                                    logger.warning(
                                        f"Row {current_row_num}: Duration '{val}' from CSV column '{header[duration_col_idx]}' is out of range (0.5-22.0). "
                                        f"Using global duration: {duration}s."
                                    )
                        except IndexError:
                            logger.warning(f"Row {current_row_num}: Duration column '{header[duration_col_idx]}' missing. Using global duration: {duration}s.")
                        except ValueError:
                            logger.warning(
                                f"Row {current_row_num}: Invalid duration value '{row[duration_col_idx]}' in CSV column '{header[duration_col_idx]}'. "
                                f"Using global duration: {duration}s."
                            )
                    
                    # Determine influence for this row
                    row_influence = prompt_influence # Start with global default
                    if influence_col_idx != -1:
                        try:
                            influence_str = row[influence_col_idx].strip()
                            if influence_str: # Only process if not empty
                                val = float(influence_str)
                                if 0.0 <= val <= 1.0:
                                    row_influence = val
                                    logger.debug(f"Row {current_row_num}: Using influence from CSV: {val}")
                                else:
                                    logger.warning(
                                        f"Row {current_row_num}: Influence '{val}' from CSV column '{header[influence_col_idx]}' is out of range (0.0-1.0). "
                                        f"Using global influence: {prompt_influence}."
                                    )
                        except IndexError:
                            logger.warning(f"Row {current_row_num}: Influence column '{header[influence_col_idx]}' missing. Using global influence: {prompt_influence}.")
                        except ValueError:
                            logger.warning(
                                f"Row {current_row_num}: Invalid influence value '{row[influence_col_idx]}' in CSV column '{header[influence_col_idx]}'. "
                                f"Using global influence: {prompt_influence}."
                            )
                    
                    prompts_data.append({
                        "text": text_prompt, 
                        "row_num": current_row_num,
                        "duration": row_duration,
                        "influence": row_influence
                    })

                except IndexError:
                    logger.warning(
                        f"Skipping malformed row {i+2} in {csv_file.name} (expected at least {prompt_col_idx + 1} columns, found {len(row)})."
                    )
                    continue
    
    except FileNotFoundError: # Should be caught by Typer, but good practice
        logger.error(f"Input CSV file not found: {csv_file}")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(f"Error processing CSV file {csv_file.name}: {e}")
        if debug:
            logger.exception("Full traceback for CSV processing error:")
        raise typer.Exit(code=1)

    if not prompts_data:
        logger.info("No valid prompts found in the CSV file.")
        raise typer.Exit(code=0)

    logger.info(f"Found {len(prompts_data)} prompts to process.")

    for item in prompts_data:
        text_prompt = item["text"]
        row_num = item["row_num"]
        current_duration = item["duration"]
        current_influence = item["influence"]
        
        log_prompt_snippet = f"'{text_prompt[:50]}{'...' if len(text_prompt) > 50 else ''}'"
        logger.info(
            f"Processing prompt from CSV row {row_num}: {log_prompt_snippet} "
            f"(Duration: {current_duration}s, Influence: {current_influence})"
        )
        
        try:
            audio_bytes = sfx_client.generate_sound_effect(
                text=text_prompt,
                duration_seconds=current_duration,
                prompt_influence=current_influence
            )
            
            base_filename = sanitize_filename(text_prompt)
            output_file_path = get_unique_filepath(output_dir, base_filename, extension=".mp3")

            with open(output_file_path, "wb") as f:
                # audio_bytes should now be real audio data from the actual elevenlabs-sfx library.
                f.write(audio_bytes)
                logger.info(f"Saved: {output_file_path.resolve()}")
                generated_count += 1

        # Catching specific exceptions from the elevenlabs_sfx library
        except ElevenLabsAPIKeyError as e: # Uses the direct import
            logger.error(f"API Key Error during generation for prompt from row {row_num} ('{text_prompt}'): {e}")
            failed_count +=1
        except ElevenLabsRateLimitError as e: # Uses the direct import
            logger.error(f"Rate Limit Error for prompt from row {row_num} ('{text_prompt}'): {e}. Try again later or reduce batch size.")
            failed_count +=1
        except ElevenLabsParameterError as e: # Uses the direct import
            logger.error(f"Parameter Error for prompt from row {row_num} ('{text_prompt}'): {e}")
            failed_count +=1
        except ElevenLabsGenerationError as e: # Uses the direct import
            logger.error(f"Generation Error for prompt from row {row_num} ('{text_prompt}'): {e}")
            failed_count +=1
        # Note: ElevenLabsPermissionError and ElevenLabsAPIError from the sfx library
        # would currently be caught by the generic Exception handler below if not listed explicitly.
        # This matches the original sfx-batch spec's error handling detail.
        except Exception as e: # Catch any other unexpected errors
            logger.error(f"An unexpected error occurred while processing prompt from row {row_num} ('{text_prompt}'): {e}")
            failed_count +=1
            if debug:
                logger.exception("Full traceback for unexpected error:")

    logger.info("--- Batch Processing Summary ---")
    logger.info(f"Successfully generated {generated_count} sound effects.")
    logger.info(f"Failed to generate {failed_count} sound effects.")
    logger.info("sfx-batch processing finished.")


if __name__ == "__main__":
    # This allows running the script directly for development/testing,
    # e.g., python sfx-batch/main.py prompts.csv --prompt-column "description"
    # However, the primary entry point will be the `sfx-batch` command installed via pyproject.toml
    app()
