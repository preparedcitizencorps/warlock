# WARLOCK Test Suite

Focused, resilient tests for the plugin system.

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_dependency_system.py

# Run specific test
pytest tests/test_dependency_system.py::TestTopologicalSort::test_circular_dependency_detected
```

## Test Philosophy

Tests validate **behavior and contracts**, not implementation details.

**What we test:**

- ✅ Dependency resolution logic
- ✅ Plugin interface contracts
- ✅ System integration (happy path)
- ✅ Circular dependency detection
- ✅ Load order vs render order separation

**What we don't test:**

- ❌ Specific pixel positions
- ❌ Exact colors or visual output
- ❌ Plugin-specific business logic
- ❌ Configuration file format details

This keeps tests stable as the system evolves.

## Test Structure

```
tests/
├── test_dependency_system.py     # Dependency graph & topological sort
├── test_plugin_contracts.py      # Plugin interface compliance
├── test_integration.py            # End-to-end smoke tests
└── fixtures/
    ├── mock_plugins.py            # Test plugins
    └── __init__.py
```

## Test Coverage

**Dependency System (9 tests)**

- Simple chains (A→B)
- Hard dependencies
- Soft dependency inference
- Diamond patterns (A→B,C→D)
- Circular dependency detection
- Missing dependency warnings

**Plugin Contracts (9 tests)**

- Interface implementation
- Metadata requirements
- Data sharing conventions
- Lifecycle management

**Integration (10 tests)**

- Plugin discovery
- Configuration loading
- Render pipeline
- Z-index ordering
- Event system

## Adding New Tests

When adding features, ask:

1. **Does this change a contract?** → Add contract test
2. **Does this affect dependency resolution?** → Add dependency test
3. **Does this break the happy path?** → Add integration test

Avoid testing implementation details that change frequently.
