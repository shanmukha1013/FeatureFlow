# Contributing to FeatureFlow

Thank you for your interest in contributing to FeatureFlow! This guide covers the process for reporting bugs, proposing features, and submitting pull requests.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and professional environment for all contributors.

## Getting Started

### 1. Fork & Clone

```bash
git clone https://github.com/<your-username>/FeatureFlow.git
cd FeatureFlow
```

### 2. Set Up the Development Environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.development .env
```

### 3. Run the Test Suite

Before starting any work, confirm all tests pass:

```bash
pytest tests/ -v
flake8 app tests scripts
```

## Branching Convention

| Branch | Purpose |
|---|---|
| `main` | Stable production-ready code |
| `feature/<name>` | New features |
| `fix/<name>` | Bug fixes |
| `docs/<name>` | Documentation improvements |
| `chore/<name>` | Dependency updates, refactoring |

## Commit Message Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add gRPC feature serving endpoint
fix: correct Redis TTL expiry in prediction cache
docs: update DEPLOYMENT.md with Kubernetes section
chore: bump SQLAlchemy to 2.0.52
test: add integration tests for /ready endpoint
```

## Pull Request Checklist

Before submitting a PR, ensure:

- [ ] All 78 tests still pass (`pytest tests/ -v`)
- [ ] `flake8` returns zero issues
- [ ] `scripts/certify_production.py` scores **100/100**
- [ ] New code includes docstrings and type hints
- [ ] Relevant documentation is updated

## Reporting Issues

When opening an issue:
1. Describe the expected vs actual behavior
2. Include steps to reproduce
3. Include relevant logs or error messages
4. Specify your Python version, OS, and Docker version

## Architecture Guidance

Before submitting a significant feature:
1. Read [docs/ARCHITECTURE.md](ARCHITECTURE.md) to understand the layer boundaries
2. New business logic belongs in the **service layer** (not in routers or repositories)
3. All new API endpoints must include Pydantic request/response models
4. New database models require an Alembic migration

## Contact

For questions, reach out via GitHub Issues or [LinkedIn](https://linkedin.com/in/marellashanmukhareddy).
