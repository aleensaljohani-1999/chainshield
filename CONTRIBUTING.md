# Contributing

## Setup

```bash
git clone https://github.com/yourusername/chainshield
cd chainshield
pip install -e ".[dev]"
```

## Development workflow

```bash
# Run tests
pytest tests/ -v

# Format
black chainshield/ tests/

# Lint
ruff check chainshield/ tests/

# Type check
mypy chainshield/

# All checks
black chainshield/ tests/ && ruff check chainshield/ tests/ && mypy chainshield/ && pytest tests/ --cov=chainshield
```

## Adding a storage backend

1. Create `chainshield/storage/your_backend.py`
2. Implement all methods in `BaseStorage`
3. Add tests in `tests/test_your_backend.py`
4. Document in `docs/`

## Pull Request guidelines

- One logical change per PR
- All tests must pass
- Coverage must not drop below 90%
- Type annotations on all public functions
- No new dependencies for the core package
