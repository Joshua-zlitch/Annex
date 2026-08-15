# Contract Testing Setup

This document describes the contract testing implementation for the ANNEX monorepo.

## Overview

Contract testing ensures that the API contract (OpenAPI spec) between the backend and frontend clients remains consistent. It prevents breaking changes from being deployed without corresponding frontend updates.

## Architecture

```
┌─────────────────┐     OpenAPI Spec      ┌──────────────────┐
│    Backend      │ ────────────────────► │  Shared Models   │
│  (FastAPI)      │   (single source      │  (Dart/Flutter)  │
│                 │    of truth)          │                  │
└─────────────────┘                       └──────────────────┘
        │                                          │
        │                                          ▼
        │                                 ┌──────────────────┐
        │                                 │   Web/Mobile     │
        │                                 │   Apps           │
        │                                 └──────────────────┘
        │
        ▼
┌─────────────────┐                       ┌──────────────────┐
│  Browser Ext.   │ ◄──────────────────── │  TypeScript      │
│  (React/TS)     │   Generated Types    │  Types           │
└─────────────────┘                       └──────────────────┘
```

## Components

### 1. Backend OpenAPI Generation (`backend/scripts/generate_openapi.py`)

Generates and validates the OpenAPI spec from the FastAPI app:

- **Validation**: Uses `openapi-spec-validator` to ensure spec is valid OpenAPI 3.x
- **Breaking Change Detection**: Compares against previous spec to detect:
  - Removed paths/operations
  - Removed schemas
  - Added required fields
- **Artifact Storage**: Uploads spec as CI artifact for downstream jobs

### 2. Dart Model Generation (`packages/shared_models/scripts/generate_dart_models.py`)

Generates Dart models from OpenAPI spec using `openapi-generator`:

- **Generator**: `dart-dio` with `json_serializable`
- **Validation**: Runs `dart analyze` on generated code
- **Integration**: Models committed to `packages/shared_models/lib/api/`

### 3. TypeScript Type Generation (`apps/extension/scripts/generate_typescript_types.py`)

Generates TypeScript types for the browser extension:

- **Generator**: `typescript-axios` with interfaces
- **Validation**: Runs `tsc --noEmit` on generated types
- **Integration**: Types committed to `apps/extension/src/shared/api/`

## CI Pipeline

The contract testing runs in the `contract-test` job (depends on `backend`):

```yaml
contract-test:
  needs: [backend]
  steps:
    1. Generate OpenAPI spec from backend
    2. Validate spec structure
    3. Check for breaking changes vs previous run
    4. Generate Dart models (verify they compile)
    5. Generate TypeScript types (verify they compile)
```

## Local Development

### Generate OpenAPI Spec

```bash
cd backend
python scripts/generate_openapi.py
```

Output: `backend/openapi/openapi.json`

### Generate Dart Models

```bash
cd packages/shared_models
# Requires Node.js and @openapitools/openapi-generator-cli
npx @openapitools/openapi-generator-cli generate \
  -i ../../backend/openapi/openapi.json \
  -g dart-dio \
  -o generated \
  --additional-properties "pubName=shared_models,pubVersion=0.1.0,useDio=true,serializationLibrary=json_serializable"
```

### Generate TypeScript Types

```bash
cd apps/extension
npx @openapitools/openapi-generator-cli generate \
  -i ../../backend/openapi/openapi.json \
  -g typescript-axios \
  -o generated-types \
  --additional-properties "npmName=@annex/api-client,npmVersion=0.1.0,supportsES6=true,withInterfaces=true"
```

## Breaking Change Policy

The following changes are considered **BREAKING** and will fail CI:

| Change | Example |
|--------|---------|
| Remove path | `DELETE /api/v1/analysis/{id}` removed |
| Remove operation | `GET /api/v1/claims` removed |
| Remove schema | `AnalysisRequest` schema deleted |
| Add required field | `new_field` added to `required` in `AnalysisRequest` |
| Change field type | `status: string` → `status: integer` |
| Change enum values | `["pending", "done"]` → `["pending", "processing", "done"]` |

The following are **NON-BREAKING** (allowed):

| Change | Example |
|--------|---------|
| Add new path | `POST /api/v1/new-endpoint` added |
| Add new operation | `PATCH /api/v1/analysis/{id}` added |
| Add optional field | `metadata?: object` added to schema |
| Add new enum value | `["pending", "done"]` → `["pending", "done", "archived"]` |
| Deprecate field | Add `deprecated: true` to field |

## Updating Contracts

When making intentional breaking changes:

1. **Backend**: Update FastAPI models/endpoints
2. **Generate**: Run `python backend/scripts/generate_openapi.py`
3. **Frontend**: Regenerate Dart/TypeScript types
4. **Update**: Commit all changes together in one PR
5. **CI**: Will pass as new spec becomes the baseline

## Artifacts

CI stores these artifacts (7-day retention):

- `openapi-spec`: Current OpenAPI spec (`openapi.json`)
- `pip-audit-results`: Python dependency vulnerabilities
- `trivy-results.sarif`: Container/filesystem vulnerabilities

## Troubleshooting

### "OpenAPI spec validation failed"
- Check that all Pydantic models have valid OpenAPI schemas
- Ensure no circular references in models
- Run `python -m openapi_spec_validator backend/openapi/openapi.json` for details

### "Breaking change detected"
- Review the error message for specific breaking change
- If intentional: regenerate frontend types and commit together
- If accidental: fix the backend change

### "Dart/TypeScript generation failed"
- Ensure `@openapitools/openapi-generator-cli` is installed
- Check OpenAPI spec is valid (run validation first)
- Verify generator version compatibility

## Version Compatibility

| Tool | Version |
|------|---------|
| openapi-spec-validator | 0.7.3 |
| @openapitools/openapi-generator-cli | Latest (via npx) |
| dart-dio generator | Built into openapi-generator |
| typescript-axios generator | Built into openapi-generator |

## Future Enhancements

- [ ] Add Pact contract testing for consumer-driven contracts
- [ ] Add GraphQL schema validation (if GraphQL added)
- [ ] Add automated PR comments with breaking change summary
- [ ] Add contract testing for gRPC/protobuf (if adopted)