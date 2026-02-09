# Contributing to Observ

Thank you for your interest in contributing to Observ! This document provides guidelines for contributing to the project.

## Code of Conduct

Be respectful, constructive, and professional in all interactions.

## Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Git
- Basic understanding of deployment systems and monitoring

### Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/stygmund/observ.git
   cd observ
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # If available
   ```

4. **Setup test database:**
   ```bash
   createdb observ_test
   psql observ_test < fleet_hub/schema.sql
   export OBSERV_DB_URL="postgresql://localhost:5432/observ_test"
   ```

5. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

## Project Structure

```
observ/
├── deploy_paradigm/     # Core deployment system
├── fleet_hub/           # Fleet monitoring dashboard
│   ├── api.py          # FastAPI application
│   ├── queries.py      # Database queries
│   ├── schema.sql      # Database schema
│   └── templates/      # Dashboard HTML
├── obs_agent/          # Monitoring agent (runs on VPS)
├── logcore/            # Structured logging library
├── docs/               # Documentation
├── examples/           # Example configurations
├── tests/              # Test suite
└── README.md           # Main documentation
```

## How to Contribute

### Reporting Bugs

1. **Check existing issues** to avoid duplicates
2. **Create a new issue** with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, etc.)
   - Relevant logs/screenshots

### Suggesting Features

1. **Check existing issues** for similar suggestions
2. **Create a feature request** with:
   - Clear use case and motivation
   - Proposed solution or API
   - Potential alternatives considered
   - Willingness to implement (optional)

### Submitting Code

1. **Create a branch:**
   ```bash
   git checkout -b feature/my-feature
   # or
   git checkout -b fix/bug-description
   ```

2. **Make your changes:**
   - Write clean, readable code
   - Follow existing code style
   - Add tests for new functionality
   - Update documentation

3. **Test your changes:**
   ```bash
   # Run all tests
   pytest tests/ -v

   # Run specific test
   pytest tests/test_deployment.py -v

   # Check code style (if configured)
   flake8 .
   black --check .
   ```

4. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

   Use conventional commit format:
   - `feat:` new feature
   - `fix:` bug fix
   - `docs:` documentation changes
   - `style:` formatting, no code change
   - `refactor:` code refactoring
   - `test:` adding tests
   - `chore:` maintenance tasks

5. **Push and create pull request:**
   ```bash
   git push origin feature/my-feature
   ```

   Then create a PR on GitHub with:
   - Clear description of changes
   - Link to related issues
   - Screenshots (if UI changes)
   - Testing steps

## Development Guidelines

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and small
- Use type hints where beneficial

**Example:**
```python
def get_vps_metrics(conn, vps_name: str, since: datetime) -> List[dict]:
    """
    Get time-series metrics for a specific VPS

    Args:
        conn: Database connection
        vps_name: VPS hostname
        since: Start timestamp for metrics

    Returns:
        List of metric data points
    """
    # Implementation
```

### Testing

- Write tests for new features
- Maintain or improve test coverage
- Test edge cases and error conditions
- Use descriptive test names

**Example:**
```python
def test_deployment_with_invalid_health_check():
    """Test that deployment rolls back when health check fails"""
    # Test implementation
```

### Documentation

- Update README.md for user-facing changes
- Update docs/ for detailed documentation
- Add inline comments for complex logic
- Include examples where helpful

### Git Workflow

1. Keep commits atomic and focused
2. Write clear commit messages
3. Rebase on main before submitting PR
4. Squash commits if requested during review

## Areas for Contribution

### High Priority

- [ ] Authentication system for Fleet Hub
- [ ] Alerting and notifications (email, Slack, webhooks)
- [ ] Data retention policies and cleanup
- [ ] Node.js deployment support
- [ ] Test coverage improvements

### Medium Priority

- [ ] Real-time updates (WebSocket)
- [ ] Custom dashboard configurations
- [ ] More chart types in analytics
- [ ] Export/import configurations
- [ ] Multi-tenancy support

### Documentation

- [ ] Video tutorials
- [ ] Architecture diagrams
- [ ] More example configurations
- [ ] Troubleshooting guide expansion
- [ ] API usage examples

### Good First Issues

Look for issues labeled `good-first-issue` on GitHub. These are typically:
- Documentation improvements
- Small bug fixes
- Test additions
- Example configurations

## Review Process

1. **Automated checks** must pass (tests, linting)
2. **Code review** by maintainer(s)
3. **Feedback addressed** through discussion or updates
4. **Approval and merge** once ready

## Questions?

- **Issues**: Create a GitHub issue with the `question` label
- **Discussions**: Use GitHub Discussions for open-ended topics
- **Email**: [Maintainer email if applicable]

## Recognition

Contributors will be recognized in:
- GitHub contributors list
- Release notes for significant contributions
- README acknowledgments (for major features)

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

---

Thank you for contributing to Observ! 🚀
