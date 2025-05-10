import re
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def sanitize_filename(prompt_text: str, max_length: int = 150) -> str:
    """
    Sanitizes a text prompt to create a valid, filesystem-safe filename.
    - Replaces spaces and common problematic characters with underscores.
    - Removes any remaining non-alphanumeric characters (except underscores and periods).
    - Converts to lowercase.
    - Truncates to a maximum length (before adding .mp3 and collision suffix).
    """
    if not prompt_text:
        return "unnamed_sfx"

    # Replace spaces and problematic characters with underscores
    # Problematic characters: / \ : * ? " < > |
    no_spaces = prompt_text.replace(" ", "_")
    sanitized = re.sub(r'[\\/:*?"<>|]', "_", no_spaces)

    # Remove any remaining non-alphanumeric characters (except underscores and periods)
    # \w matches alphanumeric characters and underscore. We also want to keep periods.
    sanitized = re.sub(r'[^\w._]', "", sanitized)
    
    # Convert to lowercase
    sanitized = sanitized.lower()

    # Remove leading/trailing underscores or periods that might have resulted
    sanitized = sanitized.strip('_.-')
    
    # Replace multiple consecutive underscores with a single underscore
    sanitized = re.sub(r'_{2,}', '_', sanitized)
    
    # If after sanitization the string is empty (e.g., prompt was only "???"), provide a default
    if not sanitized:
        sanitized = "generated_sfx"

    # Truncate to maximum length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
        # Ensure it doesn't end with a partial character or underscore if possible
        sanitized = sanitized.rsplit('_', 1)[0] if '_' in sanitized[max_length-10:max_length] else sanitized 
        sanitized = sanitized.strip('_.-') # Clean up again after potential truncation

    if not sanitized: # If truncation resulted in empty string
        sanitized = "generated_sfx_truncated"
        
    return sanitized


def get_unique_filepath(output_dir: Path, base_filename: str, extension: str = ".mp3") -> Path:
    """
    Generates a unique filepath by appending a sequential number if a file with
    the target name already exists.
    e.g., sound.mp3, sound_1.mp3, sound_2.mp3
    """
    output_filename = f"{base_filename}{extension}"
    output_file_path = output_dir / output_filename
    
    counter = 1
    while output_file_path.exists():
        output_filename = f"{base_filename}_{counter}{extension}"
        output_file_path = output_dir / output_filename
        counter += 1
        if counter > 1000: # Safety break for extreme cases
            logger.warning(f"More than 1000 filename collisions for {base_filename}. Check output directory.")
            # Fallback to a more unique name if something is very wrong
            import uuid
            output_filename = f"{base_filename}_{uuid.uuid4().hex[:8]}{extension}"
            output_file_path = output_dir / output_filename
            break 
            
    return output_file_path
