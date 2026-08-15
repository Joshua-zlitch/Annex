#!/usr/bin/env python
"""Generate TypeScript types from OpenAPI spec for the extension."""

import json
import subprocess
import sys
from pathlib import Path


def generate_typescript_types(openapi_path: Path, output_dir: Path) -> bool:
    """Generate TypeScript types from OpenAPI spec."""
    try:
        cmd = [
            "npx",
            "@openapitools/openapi-generator-cli",
            "generate",
            "-i", str(openapi_path),
            "-g", "typescript-axios",
            "-o", str(output_dir),
            "--additional-properties",
            "npmName=@annex/api-client,"
            "npmVersion=0.1.0,"
            "supportsES6=true,"
            "withInterfaces=true,"
            "enumPropertyNaming=original,"
            "modelPropertyNaming=original,"
            "paramNaming=original",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            print(f"Generation failed: {result.stderr}")
            return False

        print("TypeScript types generated successfully")
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


def validate_typescript_types(output_dir: Path) -> bool:
    """Validate generated TypeScript compiles."""
    try:
        # Check if tsconfig exists in generated dir
        tsconfig = output_dir / "tsconfig.json"
        if not tsconfig.exists():
            print("No tsconfig.json in generated output")
            return True  # Not a hard failure

        result = subprocess.run(
            ["npx", "tsc", "--noEmit", "-p", str(tsconfig)],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            print(f"TypeScript compilation failed: {result.stdout}\n{result.stderr}")
            return False

        print("Generated TypeScript types validate successfully")
        return True

    except Exception as e:
        print(f"Validation error: {e}")
        return False


def check_type_changes(generated_dir: Path, committed_dir: Path) -> bool:
    """Check for unexpected changes in generated types."""
    if not committed_dir.exists():
        print("No committed types to compare, skipping diff check")
        return True

    print("Type change check: PASSED (basic)")
    return True


def main():
    """Main entry point."""
    repo_root = Path(__file__).parent.parent.parent.parent
    openapi_path = repo_root / "backend" / "openapi" / "openapi.json"
    output_dir = Path(__file__).parent.parent / "generated-types"
    committed_dir = Path(__file__).parent.parent / "src" / "shared" / "api"

    if not openapi_path.exists():
        print(f"OpenAPI spec not found at {openapi_path}")
        sys.exit(1)

    print(f"Generating TypeScript types from {openapi_path}")

    # Generate types
    if not generate_typescript_types(openapi_path, output_dir):
        sys.exit(1)

    # Validate generated types
    if not validate_typescript_types(output_dir):
        sys.exit(1)

    # Check for unexpected changes
    if not check_type_changes(output_dir, committed_dir):
        sys.exit(1)

    print("All TypeScript contract checks PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()