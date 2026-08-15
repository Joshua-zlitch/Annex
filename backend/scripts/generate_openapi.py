#!/usr/bin/env python
"""Generate OpenAPI spec from FastAPI app and validate it."""

import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import create_app
from app.core.config import Settings


def generate_openapi_spec(output_path: Path) -> dict:
    """Generate OpenAPI spec from the FastAPI app."""
    settings = Settings(_env_file=None, app_env="test")
    app = create_app(settings)

    openapi_spec = app.openapi()

    # Write to file
    output_path.write_text(json.dumps(openapi_spec, indent=2))
    print(f"OpenAPI spec written to {output_path}")

    return openapi_spec


def validate_openapi_spec(spec: dict) -> bool:
    """Validate OpenAPI spec structure."""
    from openapi_spec_validator import validate_spec

    try:
        validate_spec(spec)
        print("OpenAPI spec validation: PASSED")
        return True
    except Exception as e:
        print(f"OpenAPI spec validation: FAILED - {e}")
        return False


def check_breaking_changes(current_spec: dict, previous_spec_path: Path) -> bool:
    """Check for breaking changes compared to previous spec."""
    if not previous_spec_path.exists():
        print("No previous spec found, skipping breaking change check")
        return True

    previous_spec = json.loads(previous_spec_path.read_text())

    # Check for removed paths
    current_paths = set(current_spec.get("paths", {}).keys())
    previous_paths = set(previous_spec.get("paths", {}).keys())
    removed_paths = previous_paths - current_paths

    if removed_paths:
        print(f"BREAKING: Removed paths: {removed_paths}")
        return False

    # Check for removed operations in existing paths
    for path in current_paths & previous_paths:
        current_ops = set(current_spec["paths"][path].keys())
        previous_ops = set(previous_spec["paths"][path].keys())
        removed_ops = previous_ops - current_ops
        if removed_ops:
            print(f"BREAKING: Removed operations in {path}: {removed_ops}")
            return False

    # Check for removed schemas
    current_schemas = set(current_spec.get("components", {}).get("schemas", {}).keys())
    previous_schemas = set(previous_spec.get("components", {}).get("schemas", {}).keys())
    removed_schemas = previous_schemas - current_schemas

    if removed_schemas:
        print(f"BREAKING: Removed schemas: {removed_schemas}")
        return False

    # Check for required field additions in schemas
    for schema_name in current_schemas & previous_schemas:
        current_schema = current_spec["components"]["schemas"][schema_name]
        previous_schema = previous_spec["components"]["schemas"][schema_name]

        current_required = set(current_schema.get("required", []))
        previous_required = set(previous_schema.get("required", []))
        added_required = current_required - previous_required

        if added_required:
            print(f"BREAKING: Added required fields in {schema_name}: {added_required}")
            return False

    print("Breaking change check: PASSED")
    return True


def main():
    """Main entry point."""
    spec_dir = Path(__file__).parent.parent / "openapi"
    spec_dir.mkdir(exist_ok=True)

    current_spec_path = spec_dir / "openapi.json"
    previous_spec_path = spec_dir / "openapi.previous.json"

    # Generate current spec
    current_spec = generate_openapi_spec(current_spec_path)

    # Validate spec
    if not validate_openapi_spec(current_spec):
        sys.exit(1)

    # Check for breaking changes
    if not check_breaking_changes(current_spec, previous_spec_path):
        sys.exit(1)

    # Update previous spec for next run
    current_spec_path.replace(previous_spec_path)
    print("Previous spec updated")

    print("All contract checks PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()