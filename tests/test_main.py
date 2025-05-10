import pytest
from typer.testing import CliRunner
from pathlib import Path
from unittest import mock
import os
import csv # Added missing import based on previous attempt's SEARCH block
import shutil # Added missing import based on previous attempt's SEARCH block

from sfx_batch.main import app, SFXClient as MockSFXClient # Import the app and the mock client
from sfx_batch.main import ElevenLabsAPIKeyError, ElevenLabsParameterError, ElevenLabsGenerationError, ElevenLabsRateLimitError

runner = CliRunner()

# Fixture for a temporary CSV file
@pytest.fixture
def temp_csv_file(tmp_path: Path) -> Path:
    csv_content = (
        "SFX_Prompt;Notes;TargetFile\n"
        '"A loud thunder clap with rain";For storm scene;"thunder_clap.mp3"\n'
        "Gentle wind blowing through trees;Ambient background for forest;forest_wind.mp3\n"
        '"Spaceship door hissing open";Sci-fi project;sfx_door_open.mp3\n'
        "A single, clear bell toll;;bell.mp3\n"
        "Prompt for param error;causes;parameter_error_sfx\n" # For testing mock client errors
        "Prompt for gen error;causes;generation_error_sfx\n"
        "Prompt for rate limit;causes;rate_limit_sfx\n"
        ";Empty prompt line test;empty.mp3\n" # Empty prompt
        "Valid prompt but too few columns\n" # Malformed row
    )
    csv_file = tmp_path / "test_prompts.csv"
    # Write with utf-8-sig to simulate BOM
    with open(csv_file, "w", encoding="utf-8-sig") as f:
        f.write(csv_content)
    return csv_file

@pytest.fixture
def temp_output_dir_for_cli(tmp_path: Path) -> Path:
    output_dir = tmp_path / "cli_test_output"
    # No need to mkdir here, the app should do it.
    return output_dir

# Mock environment variable for API key
@pytest.fixture(autouse=True)
def mock_env_api_key(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test_env_api_key")

# To capture logs
@pytest.fixture
def log_capture(caplog):
    import logging
    caplog.set_level(logging.INFO, logger="sfx_batch.main")
    caplog.set_level(logging.DEBUG, logger="sfx_batch.main") # Capture debug from app's logger
    return caplog


class TestCliMain:
    def test_help_message(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "sfx-batch CLI tool for batch sound effects generation" in result.stdout # Changed sfxbatch to sfx-batch
        assert "CSV_FILE" in result.stdout
        assert "--prompt-column" in result.stdout

    def test_missing_csv_file(self):
        result = runner.invoke(app, ["non_existent.csv", "--prompt-column", "0"])
        assert result.exit_code != 0 # Typer handles this, exit code is 2 for invalid param
        assert "Invalid value for 'CSV_FILE'" in result.stderr
        assert "File 'non_existent.csv' does not exist" in result.stderr

    def test_missing_prompt_column_arg(self, temp_csv_file: Path):
        result = runner.invoke(app, [str(temp_csv_file)])
        assert result.exit_code != 0 # Typer handles this, exit code is 2
        assert "Missing option '--prompt-column'" in result.stderr

    def test_api_key_missing(self, temp_csv_file: Path, monkeypatch):
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False) # Remove env key
        result = runner.invoke(app, [str(temp_csv_file), "--prompt-column", "0"]) # No --api-key arg
        assert result.exit_code == 1
        assert "ElevenLabs API key not found" in result.stdout # Logged as error
        assert "Exiting due to missing API key." in result.stdout

    def test_api_key_from_cli_arg(self, temp_csv_file: Path, temp_output_dir_for_cli: Path, monkeypatch, log_capture):
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False) # Ensure env key is not used
        
        # Mock the SFXClient to check how it's initialized
        with mock.patch("sfx_batch.main.SFXClient") as MockedSFXClientInstance: # Changed sfxbatch to sfx_batch
            mock_sfx_instance = MockedSFXClientInstance.return_value
            mock_sfx_instance.generate_sound_effect.return_value = b"mock_audio"

            result = runner.invoke(app, [
                str(temp_csv_file),
                "--prompt-column", "0",
                "--api-key", "test_cli_api_key",
                "--output-dir", str(temp_output_dir_for_cli)
            ])

        assert result.exit_code == 0
        MockedSFXClientInstance.assert_called_once_with(api_key="test_cli_api_key", max_retries=3)
        assert "Using API key from --api-key argument." in log_capture.text
        assert temp_output_dir_for_cli.exists()

    def test_successful_run_with_column_name(self, temp_csv_file: Path, temp_output_dir_for_cli: Path, log_capture):
        result = runner.invoke(app, [
            str(temp_csv_file),
            "--prompt-column", "SFX_Prompt", # Use column name
            "--output-dir", str(temp_output_dir_for_cli)
        ])
        assert result.exit_code == 0
        assert "sfx-batch processing finished." in result.stdout # Changed sfxbatch to sfx-batch
        assert temp_output_dir_for_cli.exists()
        
        # Expected files based on CSV content (excluding error prompts and empty/malformed)
        # "A loud thunder clap with rain" -> a_loud_thunder_clap_with_rain.mp3
        # "Gentle wind blowing through trees" -> gentle_wind_blowing_through_trees.mp3
        # "Spaceship door hissing open" -> spaceship_door_hissing_open.mp3
        # "A single, clear bell toll" -> a_single_clear_bell_toll.mp3
        # Total 4 valid files from the main prompts.
        # The error prompts will be processed but log errors.
        
        # Check number of "Saved:" messages
        saved_logs = [line for line in log_capture.text.splitlines() if "Saved:" in line]
        # Mock client generates for all, even error ones, unless error is in client init
        # The mock client raises errors for specific prompt texts
        # "Prompt for param error" -> logs error, failed_count++
        # "Prompt for gen error" -> logs error, failed_count++
        # "Prompt for rate limit" -> logs error, failed_count++
        # So, 4 successful, 3 failed.
        assert len(saved_logs) == 4 
        assert (temp_output_dir_for_cli / "a_loud_thunder_clap_with_rain.mp3").exists()
        assert (temp_output_dir_for_cli / "gentle_wind_blowing_through_trees.mp3").exists()
        assert (temp_output_dir_for_cli / "spaceship_door_hissing_open.mp3").exists()
        assert (temp_output_dir_for_cli / "a_single_clear_bell_toll.mp3").exists()

        assert "Successfully generated 4 sound effects." in result.stdout
        assert "Failed to generate 3 sound effects." in result.stdout # Due to mock client errors

        # Check for warnings about empty/malformed rows
        assert "Skipping row 8 due to empty prompt" in log_capture.text # Row 8 in CSV (1-indexed)
        assert "Skipping malformed row 9" in log_capture.text # Row 9 in CSV

    def test_invalid_prompt_column_name(self, temp_csv_file: Path, temp_output_dir_for_cli: Path):
        result = runner.invoke(app, [
            str(temp_csv_file),
            "--prompt-column", "NonExistentColumn",
            "--output-dir", str(temp_output_dir_for_cli)
        ])
        assert result.exit_code == 1
        assert "Prompt column name 'NonExistentColumn' not found in CSV header" in result.stdout

    def test_invalid_prompt_column_index(self, temp_csv_file: Path, temp_output_dir_for_cli: Path):
        result = runner.invoke(app, [
            str(temp_csv_file),
            "--prompt-column", "10", # Index out of bounds
            "--output-dir", str(temp_output_dir_for_cli)
        ])
        assert result.exit_code == 1
        assert "Prompt column index 10 is out of range" in result.stdout
        
    def test_output_dir_creation(self, temp_csv_file: Path, temp_output_dir_for_cli: Path):
        assert not temp_output_dir_for_cli.exists() # Ensure it doesn't exist before run
        result = runner.invoke(app, [
            str(temp_csv_file),
            "--prompt-column", "0",
            "--output-dir", str(temp_output_dir_for_cli)
        ])
        assert result.exit_code == 0
        assert temp_output_dir_for_cli.exists()
        assert temp_output_dir_for_cli.is_dir()

    def test_verbose_and_debug_logging(self, temp_csv_file: Path, temp_output_dir_for_cli: Path, log_capture):
        # Test verbose
        runner.invoke(app, [
            str(temp_csv_file), "--prompt-column", "0", "--output-dir", str(temp_output_dir_for_cli), "-v"
        ])
        assert "Verbose logging enabled (INFO level)." in log_capture.text
        
        log_capture.clear() # Clear logs for next run

        # Test debug
        # Need to mock SFXClient init to avoid API key error if env var is somehow unset by other tests
        with mock.patch("sfx_batch.main.SFXClient") as MockedSFXClientInstance:
            mock_sfx_instance = MockedSFXClientInstance.return_value
            mock_sfx_instance.generate_sound_effect.return_value = b"mock_audio"
            
            runner.invoke(app, [
                str(temp_csv_file), "--prompt-column", "0", "--output-dir", str(temp_output_dir_for_cli), "--debug", "--api-key", "debugkey"
            ])
        assert "Debug logging enabled." in log_capture.text
        assert "Mock SFXClient initialized with API key: *****key" in log_capture.text # Debug log from mock client
        assert "CSV Header:" in log_capture.text # Debug log from CSV processing

    def test_mock_sfx_client_errors(self, temp_csv_file: Path, temp_output_dir_for_cli: Path, log_capture):
        result = runner.invoke(app, [
            str(temp_csv_file),
            "--prompt-column", "SFX_Prompt", # This column contains "Prompt for param error", etc.
            "--output-dir", str(temp_output_dir_for_cli)
        ])
        assert result.exit_code == 0 # App finishes, but logs errors
        
        assert "Parameter Error for prompt from row 5 ('Prompt for param error'): Invalid parameter for prompt: Prompt for param error" in log_capture.text
        assert "Generation Error for prompt from row 6 ('Prompt for gen error'): Failed to generate sound for prompt: Prompt for gen error" in log_capture.text
        assert "Rate Limit Error for prompt from row 7 ('Prompt for rate limit'): Rate limit exceeded." in log_capture.text
        assert "Failed to generate 3 sound effects." in result.stdout

    def test_empty_csv(self, tmp_path: Path, temp_output_dir_for_cli: Path):
        empty_csv = tmp_path / "empty.csv"
        empty_csv.write_text("Header1;Header2\n", encoding="utf-8-sig") # Only header
        
        result = runner.invoke(app, [
            str(empty_csv),
            "--prompt-column", "Header1",
            "--output-dir", str(temp_output_dir_for_cli)
        ])
        assert result.exit_code == 0 # Exits cleanly
        assert "No valid prompts found in the CSV file." in result.stdout

        only_header_no_nl = tmp_path / "only_header.csv"
        only_header_no_nl.write_text("Header1;Header2", encoding="utf-8-sig")
        result = runner.invoke(app, [
            str(only_header_no_nl),
            "--prompt-column", "Header1",
            "--output-dir", str(temp_output_dir_for_cli)
        ])
        assert result.exit_code == 0 # Exits cleanly
        assert "No valid prompts found in the CSV file." in result.stdout


    def test_csv_no_header(self, tmp_path: Path, temp_output_dir_for_cli: Path):
        no_header_csv = tmp_path / "no_header.csv"
        no_header_csv.write_text("", encoding="utf-8-sig") # Completely empty
        
        result = runner.invoke(app, [
            str(no_header_csv),
            "--prompt-column", "0",
            "--output-dir", str(temp_output_dir_for_cli)
        ])
        assert result.exit_code == 1
        assert "CSV file 'no_header.csv' is empty or has no header." in result.stdout

    # --- Tests for new CSV features (delimiter, per-prompt duration/influence) ---

    @pytest.fixture
    def csv_for_options_test(self, tmp_path: Path) -> Path:
        # Comma-delimited, with duration and influence columns
        content = (
            "prompt_text,notes,custom_duration,custom_influence\n"
            '"Prompt A","Note A",2.5,0.7\n' # Valid duration and influence
            '"Prompt B","Note B",,0.2\n'      # Empty duration (use global), valid influence
            '"Prompt C","Note C",3.0,\n'      # Valid duration, empty influence (use global)
            '"Prompt D","Note D",invalid,0.9\n' # Invalid duration (use global), valid influence
            '"Prompt E","Note E",7.5,invalid\n' # Valid duration, invalid influence (use global)
            '"Prompt F","Note F",0.1,0.5\n'    # Duration out of range (use global)
            '"Prompt G","Note G",10.0,1.5\n'   # Influence out of range (use global)
            '"Prompt H","Note H",\n'          # Empty duration and influence (use globals)
        )
        csv_file = tmp_path / "options_test.csv"
        csv_file.write_text(content, encoding="utf-8")
        return csv_file

    def test_custom_delimiter(self, csv_for_options_test: Path, temp_output_dir_for_cli: Path, log_capture):
        with mock.patch("sfx_batch.main.ElevenLabsSFXClient") as MockedSFXClientInstance:
            mock_sfx_instance = MockedSFXClientInstance.return_value
            mock_sfx_instance.generate_sound_effect.return_value = b"mock_audio"

            result = runner.invoke(app, [
                str(csv_for_options_test),
                "--prompt-column", "prompt_text",
                "--delimiter", ",",
                "--api-key", "testkey", # Provide API key to pass that check
                "--output-dir", str(temp_output_dir_for_cli)
            ])
        assert result.exit_code == 0, result.stdout
        assert "CSV Delimiter: ','" in log_capture.text
        # Check if prompts were processed (implies correct delimiter)
        # 8 prompts in csv_for_options_test
        assert "Found 8 prompts to process." in log_capture.text
        assert MockedSFXClientInstance.return_value.generate_sound_effect.call_count == 8


    def test_per_prompt_duration_and_influence(self, csv_for_options_test: Path, temp_output_dir_for_cli: Path, log_capture):
        with mock.patch("sfx_batch.main.ElevenLabsSFXClient") as MockedSFXClientInstance:
            mock_sfx_instance = MockedSFXClientInstance.return_value
            mock_sfx_instance.generate_sound_effect.return_value = b"mock_audio"

            result = runner.invoke(app, [
                str(csv_for_options_test),
                "--prompt-column", "0", # Use index for prompt
                "--delimiter", ",",
                "--duration-column", "custom_duration", # Use name for duration col
                "--influence-column", "3", # Use index for influence col
                "--api-key", "testkey",
                "--output-dir", str(temp_output_dir_for_cli),
                "--duration", "5.0", # Global duration
                "--prompt-influence", "0.3" # Global influence
            ])

        assert result.exit_code == 0, result.stdout
        
        calls = MockedSFXClientInstance.return_value.generate_sound_effect.call_args_list
        assert len(calls) == 8

        # Expected durations and influences (global defaults: duration=5.0, influence=0.3)
        # Prompt A: duration=2.5, influence=0.7
        # Prompt B: duration=5.0 (global), influence=0.2
        # Prompt C: duration=3.0, influence=0.3 (global)
        # Prompt D: duration=5.0 (global, invalid str), influence=0.9
        # Prompt E: duration=7.5, influence=0.3 (global, invalid str)
        # Prompt F: duration=5.0 (global, out of range), influence=0.5
        # Prompt G: duration=10.0, influence=0.3 (global, out of range)
        # Prompt H: duration=5.0 (global), influence=0.3 (global)

        expected_params = [
            {"text": "Prompt A", "duration_seconds": 2.5, "prompt_influence": 0.7},
            {"text": "Prompt B", "duration_seconds": 5.0, "prompt_influence": 0.2},
            {"text": "Prompt C", "duration_seconds": 3.0, "prompt_influence": 0.3},
            {"text": "Prompt D", "duration_seconds": 5.0, "prompt_influence": 0.9},
            {"text": "Prompt E", "duration_seconds": 7.5, "prompt_influence": 0.3},
            {"text": "Prompt F", "duration_seconds": 5.0, "prompt_influence": 0.5},
            {"text": "Prompt G", "duration_seconds": 10.0, "prompt_influence": 0.3},
            {"text": "Prompt H", "duration_seconds": 5.0, "prompt_influence": 0.3},
        ]

        for i, call in enumerate(calls):
            args, kwargs = call
            assert kwargs['text'] == expected_params[i]['text']
            assert kwargs['duration_seconds'] == expected_params[i]['duration_seconds']
            assert kwargs['prompt_influence'] == expected_params[i]['prompt_influence']

        # Check for warnings in logs
        assert "Duration 'invalid' from CSV column 'custom_duration' is out of range" not in log_capture.text # Should be "Invalid duration value"
        assert "Invalid duration value 'invalid' in CSV column 'custom_duration'" in log_capture.text # For Prompt D
        assert "Invalid influence value 'invalid' in CSV column 'custom_influence'" in log_capture.text # For Prompt E
        assert "Duration '0.1' from CSV column 'custom_duration' is out of range" in log_capture.text # For Prompt F
        assert "Influence '1.5' from CSV column 'custom_influence' is out of range" in log_capture.text # For Prompt G
        
        # Check log messages for fallback
        assert "Using global duration: 5.0s." in log_capture.text
        assert "Using global influence: 0.3." in log_capture.text


    def test_duration_influence_cols_not_found(self, csv_for_options_test: Path, temp_output_dir_for_cli: Path, log_capture):
         with mock.patch("sfx_batch.main.ElevenLabsSFXClient") as MockedSFXClientInstance:
            mock_sfx_instance = MockedSFXClientInstance.return_value
            mock_sfx_instance.generate_sound_effect.return_value = b"mock_audio"
            result = runner.invoke(app, [
                str(csv_for_options_test),
                "--prompt-column", "prompt_text",
                "--delimiter", ",",
                "--duration-column", "NonExistentDurationCol",
                "--influence-column", "NonExistentInfluenceCol",
                "--api-key", "testkey",
                "--output-dir", str(temp_output_dir_for_cli),
                "--duration", "6.0", # Different global duration
                "--prompt-influence", "0.6" # Different global influence
            ])
            assert result.exit_code == 0, result.stdout
            assert "Duration column name 'NonExistentDurationCol' not found in CSV header. Will use global --duration." in log_capture.text
            assert "Influence column name 'NonExistentInfluenceCol' not found in CSV header. Will use global --prompt-influence." in log_capture.text

            # Verify all calls used global values
            calls = MockedSFXClientInstance.return_value.generate_sound_effect.call_args_list
            assert len(calls) == 8
            for call in calls:
                args, kwargs = call
                assert kwargs['duration_seconds'] == 6.0
                assert kwargs['prompt_influence'] == 0.6


    # Tests for .env file handling
    def test_api_key_from_dotenv_file(self, temp_csv_file: Path, temp_output_dir_for_cli: Path, monkeypatch, tmp_path, log_capture):
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False) # Remove shell env var
        
        # Create a .env file in the temporary test execution directory (which pytest sets as CWD for the test)
        dot_env_file = tmp_path / ".env" 
        dot_env_file.write_text('ELEVENLABS_API_KEY="dotenv_api_key"')
        
        original_cwd = os.getcwd()
        os.chdir(tmp_path) # Change CWD so .env is found by load_dotenv()

        try:
            with mock.patch("sfx_batch.main.SFXClient") as MockedSFXClientInstance:
                mock_sfx_instance = MockedSFXClientInstance.return_value
                mock_sfx_instance.generate_sound_effect.return_value = b"mock_audio"

                result = runner.invoke(app, [
                    str(temp_csv_file), # Use the one from tmp_path fixture, ensure path is correct
                    "--prompt-column", "0",
                    "--output-dir", str(temp_output_dir_for_cli) 
                    # No --api-key CLI arg, no shell env var
                ])
            
            assert result.exit_code == 0, result.stdout
            MockedSFXClientInstance.assert_called_once_with(api_key="dotenv_api_key", max_retries=3)
            assert ".env file loaded." in log_capture.text # Check if load_dotenv reported success
            assert "Using API key from ELEVENLABS_API_KEY environment variable." in log_capture.text # get_api_key logs this
        finally:
            os.chdir(original_cwd) # Restore CWD
            if dot_env_file.exists():
                dot_env_file.unlink()


    def test_cli_overrides_dotenv_and_shell_env(
        self, temp_csv_file: Path, temp_output_dir_for_cli: Path, monkeypatch, tmp_path, log_capture
    ):
        # Set shell env var
        monkeypatch.setenv("ELEVENLABS_API_KEY", "shell_env_api_key")
        
        # Create .env file
        dot_env_file = tmp_path / ".env"
        dot_env_file.write_text('ELEVENLABS_API_KEY="dotenv_api_key"')
        
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            with mock.patch("sfx_batch.main.SFXClient") as MockedSFXClientInstance: # Changed sfxbatch to sfx_batch
                mock_sfx_instance = MockedSFXClientInstance.return_value
                mock_sfx_instance.generate_sound_effect.return_value = b"mock_audio"

                result = runner.invoke(app, [
                    str(temp_csv_file),
                    "--prompt-column", "0",
                    "--api-key", "cli_api_key", # CLI key should win
                    "--output-dir", str(temp_output_dir_for_cli)
                ])
            
            assert result.exit_code == 0, result.stdout
            MockedSFXClientInstance.assert_called_once_with(api_key="cli_api_key", max_retries=3)
            assert "Using API key from --api-key argument." in log_capture.text
        finally:
            os.chdir(original_cwd)
            if dot_env_file.exists():
                dot_env_file.unlink()

    def test_shell_env_overrides_dotenv(
        self, temp_csv_file: Path, temp_output_dir_for_cli: Path, monkeypatch, tmp_path, log_capture
    ):
        # Set shell env var
        monkeypatch.setenv("ELEVENLABS_API_KEY", "shell_env_api_key")
        
        # Create .env file
        dot_env_file = tmp_path / ".env"
        dot_env_file.write_text('ELEVENLABS_API_KEY="dotenv_api_key"')
        
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            with mock.patch("sfx_batch.main.SFXClient") as MockedSFXClientInstance: # Changed sfxbatch to sfx_batch
                mock_sfx_instance = MockedSFXClientInstance.return_value
                mock_sfx_instance.generate_sound_effect.return_value = b"mock_audio"

                result = runner.invoke(app, [
                    str(temp_csv_file),
                    "--prompt-column", "0",
                    # No CLI key
                    "--output-dir", str(temp_output_dir_for_cli)
                ])
            
            assert result.exit_code == 0, result.stdout
            # python-dotenv's load_dotenv by default does NOT override existing shell env vars.
            MockedSFXClientInstance.assert_called_once_with(api_key="shell_env_api_key", max_retries=3)
            assert "Using API key from ELEVENLABS_API_KEY environment variable." in log_capture.text
        finally:
            os.chdir(original_cwd)
            if dot_env_file.exists():
                dot_env_file.unlink()
    
    def test_no_dotenv_file_found(self, temp_csv_file: Path, temp_output_dir_for_cli: Path, monkeypatch, log_capture):
        # Ensure no shell env var for API key that could be picked up
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        # Ensure no .env file exists in CWD (tmp_path for this test)
        
        # We expect this to fail because no API key is provided by any means
        result = runner.invoke(app, [
            str(temp_csv_file),
            "--prompt-column", "0",
            "--output-dir", str(temp_output_dir_for_cli)
        ])
        
        assert result.exit_code == 1 # Should fail due to missing API key
        assert "No .env file found or it is empty." in log_capture.text
        assert "ElevenLabs API key not found" in log_capture.text # Error from get_api_key
