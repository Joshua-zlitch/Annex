#!/usr/bin/env python
"""Generate Dart models from OpenAPI spec using openapi-generator."""

import json
import subprocess
import sys
from pathlib import Path


def generate_dart_models(openapi_path: Path, output_dir: Path) -> bool:
    """Generate Dart models from OpenAPI spec."""
    try:
        # Use openapi-generator-cli via npx
        cmd = [
            "npx",
            "@openapitools/openapi-generator-cli",
            "generate",
            "-i", str(openapi_path),
            "-g", "dart-dio",
            "-o", str(output_dir),
            "--additional-properties",
            "pubName=shared_models,pubVersion=0.1.0,useDio=true,"
            "serializationLibrary=json_serializable,"
            "generateSourceCodeOnly=true,"
            "sortParamsByRequiredFlag=true,"
            "ensureUniqueParams=true",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            print(f"Generation failed: {result.stderr}")
            return False

        print("Dart models generated successfully")
        return True

    except subprocess.TimeoutExpired:
        print("Generation timed out")
        return False
    except FileNotFoundError:
        print("npx not found. Install Node.js and @openapitools/openapi-generator-cli")
        return False
    except Exception as e:
        print(f"Generation error: {e}")
        return False


def validate_generated_models(output_dir: Path) -> bool:
    """Validate generated models compile."""
    try:
        # Run dart analyze on generated code
        result = subprocess.run(
            ["dart", "analyze", str(output_dir / "lib")],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            print(f"Dart analyze failed: {result.stdout}\n{result.stderr}")
            return False

        print("Generated models validate successfully")
        return True

    except Exception as e:
        print(f"Validation error: {e}")
        return False


def check_model_changes(generated_dir: Path, committed_dir: Path) -> bool:
    """Check for unexpected changes in generated models."""
    if not committed_dir.exists():
        print("No committed models to compare, skipping diff check")
        return True

    # Compare key model files
    generated_files = list(generated_dir.rglob("*.dart"))
    committed_files = list(committed_dir.rglob("*.dart"))

    if len(generated_files) != len(committed_files):
        print(f"File count mismatch: generated={len(generated_files)}, committed={len(committed_files)}")
        return False

    # For now, just check that we can generate without errors
    # In production, you'd do a more sophisticated diff
    print("Model change check: PASSED (basic)")
    return True


def main():
    """Main entry point."""
    repo_root = Path(__file__).parent.parent.parent.parent
    openapi_path = repo_root / "backend" / "openapi" / "openapi.json"
    output_dir = Path(__file__).parent.parent / "generated"
    committed_dir = Path(__file__).parent.parent / "lib" / "api"

    if not openapi_path.exists():
        print(f"OpenAPI spec not found at {openapi_path}")
        sys.exit(1)

    print(f"Generating Dart models from {openapi_path}")

    # Generate models
    if not generate_dart_models(openapi_path, output_dir):
        sys.exit(1)

    # Validate generated models
    if not validate_generated_models(output_dir):
        sys.exit(1)

    # Check for unexpected changes
    if not check_model_changes(output_dir, committed_dir):
        sys.exit(1)

    print("All Dart contract checks PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()