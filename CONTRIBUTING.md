# 🤝 Contributing to Tiger MCP

Thank you for considering contributing to the Tiger MCP project! We welcome contributions from the community and are excited to work with you.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Guidelines](#contributing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Community Support](#community-support)

## 📜 Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. We are committed to providing a welcoming and inspiring community for all.

### Our Standards

- **Be respectful**: Treat everyone with respect and kindness
- **Be inclusive**: Welcome newcomers and help them succeed
- **Be constructive**: Focus on what's best for the community
- **Be patient**: Help others learn and grow

## 🚀 Getting Started

### Prerequisites

Before contributing, ensure you have:

- **Python 3.11+** installed
- **[UV package manager](https://docs.astral.sh/uv/)** for dependency management
- **Git** for version control
- **Docker & Docker Compose** (recommended for testing)
- **Tiger Brokers API access** for testing (sandbox recommended)

### Fork and Clone

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/yourusername/tiger-mcp.git
   cd tiger-mcp
   ```

3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/original-owner/tiger-mcp.git
   ```

## 🔧 Development Setup

### Environment Setup

1. **Copy environment template**:
   ```bash
   cp .env.template .env
   # Edit .env with your Tiger API credentials (sandbox recommended)
   ```

2. **Install dependencies**:
   ```bash
   # Install UV if not already installed
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Sync workspace dependencies
   uv sync
   ```

3. **Start development environment**:
   ```bash
   # Using Docker (recommended)
   docker-compose -f docker-compose.dev.yml up -d
   
   # Or run components individually
   uv run --package mcp-server python -m mcp_server
   ```

4. **Verify setup**:
   ```bash
   # Test MCP server
   curl http://localhost:8000/health
   
   # Run tests
   uv run pytest
   ```

## 📝 Contributing Guidelines

### Types of Contributions

We welcome various types of contributions:

- **🐛 Bug Reports**: Help us identify and fix issues
- **💡 Feature Requests**: Suggest new features or improvements
- **📖 Documentation**: Improve our documentation
- **🔧 Code Contributions**: Fix bugs or implement new features
- **🧪 Testing**: Add tests or improve test coverage
- **🎨 UI/UX**: Improve user experience and interface design

### Before You Start

1. **Check existing issues**: Look for existing issues or discussions
2. **Create an issue**: For significant changes, create an issue first
3. **Discuss approach**: Get feedback on your proposed solution
4. **Assign yourself**: Comment on the issue to avoid duplicate work

## 🔄 Pull Request Process

### 1. Create a Feature Branch

```bash
git checkout -b feature/amazing-feature
# or
git checkout -b fix/important-bug
# or  
git checkout -b docs/improve-readme
```

### 2. Make Your Changes

- **Follow coding standards** (see below)
- **Add tests** for new functionality
- **Update documentation** as needed
- **Keep changes focused** and atomic

### 3. Test Your Changes

```bash
# Run all tests
uv run pytest

# Run linting
uv run black .
uv run isort .
uv run mypy packages/

# Run security checks
uv run bandit -r packages/

# Test with Docker
docker-compose -f docker-compose.dev.yml build
docker-compose -f docker-compose.dev.yml up --abort-on-container-exit
```

### 4. Commit Your Changes

Use conventional commit messages:

```bash
# Format: <type>(<scope>): <description>
git commit -m "feat(mcp-server): add multi-account portfolio aggregation"
git commit -m "fix(auth): resolve Tiger API authentication timeout"
git commit -m "docs(readme): improve installation instructions"
```

**Commit Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Formatting, missing semicolons, etc.
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `test`: Adding missing tests
- `chore`: Changes to build process or auxiliary tools

### 5. Push and Create Pull Request

```bash
git push origin feature/amazing-feature
```

Create a pull request on GitHub with:

- **Clear title** describing the change
- **Detailed description** of what was changed and why
- **Link to related issues**
- **Screenshots** for UI changes
- **Testing instructions** for reviewers

## 📏 Coding Standards

### Python Code Style

- **Black** for code formatting
- **isort** for import sorting
- **Type hints** for all functions and methods
- **Docstrings** for all public functions (Google style)
- **Max line length**: 88 characters (Black default)

### Code Quality

```python
# Good example
async def get_portfolio(
    self, 
    account_id: str, 
    include_positions: bool = True
) -> Portfolio:
    """Get portfolio information for the specified account.
    
    Args:
        account_id: The Tiger Brokers account ID
        include_positions: Whether to include position details
        
    Returns:
        Portfolio object with account information
        
    Raises:
        TigerAuthError: If authentication fails
        TigerAPIError: If API request fails
    """
    try:
        client = await self.get_tiger_client(account_id)
        portfolio_data = await client.get_portfolio()
        return Portfolio.from_tiger_data(portfolio_data)
    except Exception as e:
        logger.error(f"Failed to get portfolio for {account_id}: {e}")
        raise
```

### Package Structure

- Follow the existing package structure
- Keep related functionality together
- Use clear, descriptive names
- Add `__init__.py` files for packages

## 🧪 Testing Requirements

### Test Coverage

- **Minimum 80% test coverage** required
- **Unit tests** for all new functions
- **Integration tests** for API endpoints
- **Multi-account tests** for account-specific functionality

### Test Categories

1. **Unit Tests**:
   ```bash
   # Test individual components
   uv run pytest packages/mcp-server/tests/
   ```

2. **Integration Tests**:
   ```bash
   # Test component interactions
   uv run pytest tests/test_integration_scenarios.py
   ```

3. **Performance Tests**:
   ```bash
   # Test performance and scalability
   uv run pytest tests/test_performance_compatibility.py
   ```

### Writing Tests

```python
import pytest
from packages.mcp_server.tools.account_tools import get_account_info

@pytest.mark.asyncio
async def test_get_account_info_success():
    """Test successful account info retrieval."""
    # Arrange
    account_id = "test_account"
    
    # Act
    result = await get_account_info(account_id)
    
    # Assert
    assert result.account_id == account_id
    assert result.balance > 0

@pytest.mark.asyncio
async def test_get_account_info_invalid_account():
    """Test account info retrieval with invalid account."""
    with pytest.raises(TigerAccountError):
        await get_account_info("invalid_account")
```

## 📖 Documentation

### Documentation Types

1. **Code Documentation**: Docstrings and inline comments
2. **API Documentation**: OpenAPI/Swagger specs
3. **User Documentation**: README, setup guides
4. **Developer Documentation**: Architecture, contributing guides

### Documentation Standards

- **Clear and concise** language
- **Code examples** for complex features  
- **Screenshots** for UI features
- **Up-to-date** with code changes

## 🚨 Security Considerations

### Security Guidelines

- **Never commit secrets** or API keys
- **Use environment variables** for configuration
- **Validate all inputs** to prevent injection attacks
- **Follow OWASP guidelines** for web security
- **Test with sandbox accounts** only

### Security Testing

```bash
# Run security scans
uv run bandit -r packages/
uv run safety check
```

## 🐛 Bug Reports

When reporting bugs, please include:

- **Environment details** (OS, Python version, UV version)
- **Steps to reproduce** the issue
- **Expected behavior** vs actual behavior
- **Error messages** and stack traces
- **Configuration details** (sanitized, no secrets)

### Bug Report Template

```markdown
## Bug Description
Brief description of the bug

## Environment
- OS: [e.g., macOS 12.6]
- Python: [e.g., 3.11.5]  
- UV: [e.g., 0.1.0]
- Tiger MCP: [e.g., 1.0.0]

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen

## Actual Behavior  
What actually happens

## Error Messages
```
Paste error messages here
```

## Additional Context
Any other relevant information
```

## 💡 Feature Requests

When requesting features, please include:

- **Use case description** and motivation
- **Proposed solution** or approach
- **Alternative solutions** considered
- **Implementation complexity** estimate
- **Breaking changes** considerations

## 🎉 Recognition

We appreciate all contributors! Contributors will be:

- **Listed** in our README contributors section
- **Mentioned** in release notes for significant contributions
- **Invited** to join our contributor community
- **Credited** in project documentation

## 📞 Community Support

### Getting Help

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and community discussion
- **Documentation**: Check our comprehensive docs first
- **Code Review**: Learn from pull request feedback

### Communication Guidelines

- **Be patient**: Maintainers are volunteers with limited time
- **Be specific**: Provide details and context
- **Be respectful**: We're all learning together
- **Be helpful**: Help others when you can

## 🏷️ Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

## 📄 License

By contributing, you agree that your contributions will be licensed under the same [MIT License](LICENSE) that covers the project.

---

Thank you for contributing to Tiger MCP! Your efforts help make trading and AI integration more accessible to everyone. 🚀

**Questions?** Feel free to reach out through GitHub issues or discussions.