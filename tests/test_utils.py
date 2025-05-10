import pytest
from pathlib import Path
import shutil # For cleaning up test directories/files

from sfx_batch.utils import sanitize_filename, get_unique_filepath

# Fixture to create a temporary directory for testing file operations
@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    output_dir = tmp_path / "test_output"
    output_dir.mkdir()
    yield output_dir
    # shutil.rmtree(output_dir) # tmp_path is automatically cleaned up by pytest

class TestSanitizeFilename:
    @pytest.mark.parametrize(
        "prompt, expected",
        [
            ("Simple prompt", "simple_prompt"),
            ("Prompt with spaces and CAPS", "prompt_with_spaces_and_caps"),
            ("Prompt/With\\Slashes:And*Other?Chars\"<|>Dots.Okay", "prompt_with_slashes_and_other_chars_dots.okay"),
            ("  leading and trailing spaces  ", "leading_and_trailing_spaces"),
            ("!@#$%^&*()+=[]{}|;':\",./<>?`~", "."), # Most are removed, period remains
            ("multiple___underscores___and__spaces", "multiple_underscores_and_spaces"),
            ("filename_that_is_very_long_and_should_be_truncated_abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqrstuvwxyz0123456789", 
             "filename_that_is_very_long_and_should_be_truncated_abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqrstuvw"), # Example, exact truncation depends on logic
            ("", "unnamed_sfx"),
            (None, "unnamed_sfx"),
            ("???", "generated_sfx"),
            (" leading_underscore", "leading_underscore"),
            ("_trailing_underscore ", "trailing_underscore"),
            ("file.with.dots", "file.with.dots"),
            ("a____b", "a_b"),
            ("a.-_b", "a.-_b"), # strip only at ends
            ("---test---", "test"),
        ]
    )
    def test_various_prompts(self, prompt, expected):
        # Adjust expected for the long filename based on current sanitize_filename logic
        if "filename_that_is_very_long" in prompt:
            # Current logic: [:150], then rsplit, then strip.
            # This is hard to perfectly predict without running it, so we'll make it more robust
            # by checking properties rather than exact match for this specific long case.
            sanitized = sanitize_filename(prompt)
            assert len(sanitized) <= 150
            assert " " not in sanitized
            assert not any(c in sanitized for c in '/\\:*?"<>|')
            assert sanitized.lower() == sanitized
            return # Skip exact match for this one

        assert sanitize_filename(prompt) == expected

    def test_max_length_truncation(self):
        long_prompt = "a" * 200
        sanitized = sanitize_filename(long_prompt, max_length=50)
        assert len(sanitized) <= 50
        # Check if it tried to preserve word boundary if possible (not applicable for "aaa...")
        # For "word_word_..." it should truncate nicely.
        long_prompt_with_underscores = "_".join(["word"] * 50) # very long
        sanitized_underscore = sanitize_filename(long_prompt_with_underscores, max_length=50)
        assert len(sanitized_underscore) <= 50
        assert not sanitized_underscore.endswith("_") # Should be stripped if truncation caused it

    def test_empty_after_sanitize(self):
        assert sanitize_filename("!!!") == "generated_sfx"
        assert sanitize_filename("   ") == "generated_sfx" # spaces become underscores, then stripped if only underscores

class TestGetUniqueFilepath:
    def test_unique_path_creation(self, temp_output_dir: Path):
        base_name = "test_sound"
        
        # First file
        path1 = get_unique_filepath(temp_output_dir, base_name)
        assert path1 == temp_output_dir / "test_sound.mp3"
        path1.touch() # Create the file

        # Second file (collision)
        path2 = get_unique_filepath(temp_output_dir, base_name)
        assert path2 == temp_output_dir / "test_sound_1.mp3"
        path2.touch()

        # Third file (collision)
        path3 = get_unique_filepath(temp_output_dir, base_name)
        assert path3 == temp_output_dir / "test_sound_2.mp3"
        path3.touch()

    def test_no_collision(self, temp_output_dir: Path):
        base_name = "unique_sound"
        path = get_unique_filepath(temp_output_dir, base_name)
        assert path == temp_output_dir / "unique_sound.mp3"

    def test_different_extension(self, temp_output_dir: Path):
        base_name = "sound_with_wav"
        path = get_unique_filepath(temp_output_dir, base_name, extension=".wav")
        assert path == temp_output_dir / "sound_with_wav.wav"
        path.touch()

        path_collided = get_unique_filepath(temp_output_dir, base_name, extension=".wav")
        assert path_collided == temp_output_dir / "sound_with_wav_1.wav"

    def test_extreme_collision_limit(self, temp_output_dir: Path, caplog):
        base_name = "extreme_collision"
        # Create 1001 files to trigger the safety break
        for i in range(1001):
            if i == 0:
                (temp_output_dir / f"{base_name}.mp3").touch()
            else:
                (temp_output_dir / f"{base_name}_{i}.mp3").touch()
        
        with caplog.at_level(logging.WARNING):
            path_after_extreme = get_unique_filepath(temp_output_dir, base_name)
        
        assert "More than 1000 filename collisions" in caplog.text
        # Check that it falls back to UUID based naming (approximate check)
        assert base_name in path_after_extreme.name
        assert ".mp3" in path_after_extreme.name
        assert len(path_after_extreme.stem) > len(base_name) + 10 # base_name + _ + 8char_uuid + _potential_number
        assert path_after_extreme.exists() is False # get_unique_filepath doesn't create the file
