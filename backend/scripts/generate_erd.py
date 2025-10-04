#!/usr/bin/env python3
"""
CLI script for ERD generation.
"""

import argparse
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Import after path modification for script execution
from erd import ERDGenerator  # noqa: E402


def _is_ci_environment() -> bool:
    """Check if we're running in a CI environment."""
    ci_indicators = [
        "CI",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "JENKINS_URL",
        "BUILDKITE",
        "CIRCLECI",
        "TRAVIS",
        "APPVEYOR",
        "DRONE",
        "SEMAPHORE",
    ]
    return any(os.getenv(indicator) for indicator in ci_indicators)


def main():
    """Main CLI entry point for ERD generation."""
    # Configure logging to output to stdout for CLI
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)

    parser = argparse.ArgumentParser(
        description="Generate Mermaid ERD diagrams from SQLModel definitions"
    )
    parser.add_argument(
        "--models-path", default="app/models.py", help="Path to SQLModel definitions"
    )
    parser.add_argument(
        "--output-path", default=None, help="Path for generated ERD documentation"
    )
    parser.add_argument(
        "--validate", action="store_true", help="Run validation checks on generated ERD"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--force", action="store_true", help="Force overwrite of existing output file"
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create backup of existing ERD file before overwriting",
    )

    args = parser.parse_args()

    # Set default output path based on environment
    if args.output_path is None:
        if _is_ci_environment():
            # In CI, use a temporary directory that's guaranteed to be writable
            temp_dir = Path(tempfile.gettempdir()) / "erd_output"
            temp_dir.mkdir(exist_ok=True)
            args.output_path = str(temp_dir / "erd.mmd")
            # In CI, default to force mode to avoid conflicts
            args.force = True
        else:
            # In development, use the docs directory
            args.output_path = "../docs/database/erd.mmd"

    # If output path is explicitly provided and we're in CI, use force mode
    elif _is_ci_environment():
        args.force = True

    try:
        # Enhanced file system operations
        if not _validate_input_path(args.models_path):
            sys.stderr.write(f"Invalid models path: {args.models_path}\n")
            return 2

        if not _prepare_output_path(args.output_path, args.force, args.backup):
            sys.stderr.write(f"Failed to prepare output path: {args.output_path}\n")
            return 3

        # Initialize ERD generator
        generator = ERDGenerator(
            models_path=args.models_path, output_path=args.output_path
        )

        if args.verbose:
            logging.info(f"Models path: {args.models_path}")
            logging.info(f"Output path: {args.output_path}")
            logging.info("Starting ERD generation...")

        # Validate models if requested
        if args.validate:
            if args.verbose:
                logging.info("Validating models...")
            validation_result = _validate_models(generator, args.verbose)
            if not validation_result:
                return 2

        # Generate ERD
        mermaid_code = generator.generate_erd()

        if args.verbose:
            logging.info("ERD generation completed successfully")
            logging.info(
                f"Generated {len(mermaid_code.splitlines())} lines of Mermaid code"
            )
            _print_output_summary(args.output_path)

        return 0

    except FileNotFoundError as e:
        sys.stderr.write(f"File not found: {e}\n")
        return 2
    except PermissionError as e:
        sys.stderr.write(f"Permission denied: {e}\n")
        return 3
    except OSError as e:
        if "Read-only file system" in str(e) or "Permission denied" in str(e):
            sys.stderr.write(f"Permission denied: {e}\n")
            return 3
        else:
            sys.stderr.write(f"OS error: {e}\n")
            return 2
    except Exception as e:
        sys.stderr.write(f"ERD generation failed: {e}\n")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


def _validate_input_path(models_path: str) -> bool:
    """Validate that the models path exists and is accessible."""
    path = Path(models_path)

    if not path.exists():
        return False

    if not path.is_file() and not path.is_dir():
        return False

    # Check if it's readable
    try:
        with open(path) as f:
            f.read(1)  # Try to read one character
        return True
    except (PermissionError, UnicodeDecodeError):
        return False


def _prepare_output_path(output_path: str, force: bool, backup: bool) -> bool:
    """Prepare the output path, creating directories and handling existing files."""
    path = Path(output_path)

    # Create parent directories if they don't exist
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        return False

    # Handle existing file
    if path.exists():
        if not force:
            logging.error(f"Output file already exists: {output_path}")
            logging.error("Use --force to overwrite or --backup to create a backup")
            return False

        if backup:
            backup_path = path.with_suffix(f"{path.suffix}.backup.{int(time.time())}")
            try:
                path.rename(backup_path)
                logging.info(f"Created backup: {backup_path}")
            except PermissionError:
                logging.warning(f"Could not create backup of {output_path}")

    # Check if we can write to the output location
    try:
        path.touch()
        path.unlink()  # Remove the test file
        return True
    except PermissionError:
        return False


def _validate_models(generator: ERDGenerator, verbose: bool = False) -> bool:  # noqa: ARG001
    """Enhanced model validation with detailed reporting."""
    try:
        is_valid = generator.validate_models()

        if not is_valid:
            logging.warning("Model validation issues found:")
            # This could be enhanced to show specific validation errors
            logging.warning("- Check that all models have primary keys")
            logging.warning("- Verify field definitions are correct")
            logging.warning("- Ensure foreign key references are valid")
        else:
            logging.info("Model validation passed successfully")

        return is_valid
    except Exception as e:
        sys.stderr.write(f"Validation error: {e}\n")
        return False


def _print_output_summary(output_path: str) -> None:
    """Print summary information about the generated output."""
    path = Path(output_path)

    if path.exists():
        file_size = path.stat().st_size
        logging.info(f"Output file: {output_path}")
        logging.info(f"File size: {file_size} bytes")

        # Try to count lines
        try:
            with open(path) as f:
                line_count = sum(1 for _ in f)
            logging.info(f"Line count: {line_count}")
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
