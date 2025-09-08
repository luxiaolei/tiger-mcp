# 🐅 Tiger MCP System

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-orange.svg)](https://modelcontextprotocol.org)
[![Docker Support](https://img.shields.io/badge/docker-supported-blue.svg)](https://docker.com)
[![UV Workspace](https://img.shields.io/badge/uv-workspace-purple.svg)](https://docs.astral.sh/uv/)

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](#)
[![Test Coverage](https://img.shields.io/badge/coverage-85%25-green.svg)](#)
[![Dependencies](https://img.shields.io/badge/dependencies-up%20to%20date-green.svg)](#)
[![Security Scan](https://img.shields.io/badge/security-bandit%20verified-green.svg)](#)

> **Professional-grade Model Context Protocol (MCP) server for Tiger Brokers API integration with Claude AI**

Connect [Claude AI](https://claude.ai) directly to [Tiger Brokers](https://www.tigerbrokers.com) for AI-powered trading, portfolio management, and market analysis. Features 22 MCP tools, REST API access, and enterprise-grade security.

---

## ⚡ **Quick Installation**

### Install from GitHub (Recommended)
```bash
# Install Tiger MCP
pip install git+https://github.com/your-username/tiger-mcp.git

# Setup configuration  
cp tiger_openapi_config.properties.example tiger_openapi_config.properties
cp .mcp.json.example .mcp.json

# Edit with your Tiger API credentials
nano tiger_openapi_config.properties
nano .mcp.json

# Ready to use!
```

### Use with Claude Code
1. Install: `pip install git+https://github.com/your-username/tiger-mcp.git`
2. Configure `.mcp.json` with your Tiger API credentials
3. Restart Claude Code  
4. Start trading: *"Show me my Tiger Brokers portfolio"*

### Use as REST API
```python
import requests

response = requests.post("http://server:9000/tiger/get_positions",
    headers={"Authorization": "Bearer your_api_key"}, 
    json={"account": "your_account_number"}
)
```

---

## ✨ Key Features

### 🤖 **AI-Native Trading**
- **Claude AI Integration**: Direct MCP protocol support for conversational trading
- **Natural Language Processing**: Execute trades using natural language commands
- **Intelligent Analysis**: AI-powered market analysis and portfolio optimization
- **Risk Management**: Automated risk assessment and position sizing

### 📊 **Real-Time Market Data**
- **Live Market Feeds**: Real-time quotes, order books, and market depth
- **Historical Analysis**: Comprehensive historical data with technical indicators
- **Market Scanning**: Advanced screening and filtering capabilities
- **Global Markets**: Support for US, HK, SG markets and more

### ⚡ **High-Performance Trading**
- **Sub-second Execution**: Optimized order routing and execution
- **Portfolio Management**: Real-time position tracking and P&L monitoring
- **Risk Controls**: Built-in risk management and compliance checks
- **Scalable Architecture**: UV workspace with modern async/await patterns

### 🛡️ **Enterprise Security**
- **Encrypted Communication**: TLS/SSL encryption for all data transmission
- **Secure Authentication**: Tiger Brokers OAuth2 with refresh token management
- **Audit Logging**: Comprehensive logging for compliance and debugging
- **Production Ready**: Docker containerization with health checks

## 🚀 Quick Start

### Prerequisites

- **Python** 3.11+ with [UV package manager](https://docs.astral.sh/uv/)
- **Docker** & Docker Compose for containerized deployment
- **Tiger Brokers Account** with API access ([Apply here](https://www.tigerbrokers.com/openapi))
- **Claude Desktop** or Claude API access

### ⚡ 30-Second Setup

```bash
# 1. Clone and setup
git clone <your-repository-url>
cd tiger-mcp
cp .env.template .env  # Configure your Tiger API credentials

# 2. Install dependencies
curl -LsSf https://astral.sh/uv/install.sh | sh  # Install UV
uv sync  # Install all workspace dependencies

# 3. Start with Docker
docker-compose up -d

# 4. Verify installation
curl http://localhost:8000/health
```

### 🔧 Configuration

Edit `.env` with your Tiger Brokers credentials:

```bash
# Tiger API Configuration
TIGER_CLIENT_ID=your_client_id_here
TIGER_PRIVATE_KEY=your_private_key_here
TIGER_ACCOUNT=your_account_id_here
TIGER_SANDBOX=true  # Set to false for live trading

# Database (using Docker defaults)
DATABASE_URL=postgresql://tiger:tiger@localhost:5432/tiger_mcp
```

> ⚠️ **Security Note**: Never commit real credentials to version control. Use `.env` file for local development and secure environment variables for production.

### 🤖 Claude AI Integration

Tiger MCP supports both **Claude Desktop** and **Claude Code** with comprehensive trading capabilities.

#### Claude Desktop Configuration

Add Tiger MCP to your Claude Desktop configuration (`~/.config/claude/config.json`):

```json
{
  "mcpServers": {
    "tiger-mcp": {
      "command": "uv",
      "args": ["run", "--package", "mcp-server", "python", "-m", "mcp_server.main"],
      "cwd": "/path/to/tiger-mcp",
      "env": {
        "TIGER_CLIENT_ID": "your_client_id",
        "TIGER_PRIVATE_KEY": "your_private_key", 
        "TIGER_ACCOUNT": "your_account_id"
      }
    }
  }
}
```

#### Claude Code Integration

For **Claude Code** users, Tiger MCP provides enhanced development and trading workflows:

```bash
# Configure Claude Code MCP server
cp config/claude_mcp.json ~/.config/claude-code/mcp-servers/

# Start the MCP server for Claude Code
uv run --package mcp-server python -m mcp_server --claude-code-mode

# Use with Claude Code commands
claude code analyze-portfolio --account=all
claude code backtest-strategy --symbol=AAPL --days=30
claude code risk-assessment --portfolio
```

**Claude Code Features:**
- **Code-Driven Trading**: Generate and execute trading algorithms
- **Portfolio Analysis**: Automated portfolio analysis and reporting
- **Strategy Development**: Backtest and optimize trading strategies
- **Risk Management**: Code-based risk analysis and position sizing
- **Multi-Account Operations**: Manage multiple Tiger accounts programmatically

#### 🎯 Example Conversations

**General Trading** (Claude Desktop & Claude Code):
```
💬 "Show me my portfolio performance this week"
💬 "What are the top gainers in tech stocks today?"
💬 "Buy 100 shares of AAPL when it drops below $180"
💬 "Analyze the risk of my current positions"
```

**Multi-Account Trading**:
```
💬 "Show portfolio for account account2_id"
💬 "Compare performance across all my accounts"
💬 "Switch to trading account account3_id and buy 100 TSLA"
💬 "What's the total portfolio value across all accounts?"
```

**Claude Code Advanced Usage**:
```
💬 "Generate a momentum trading strategy for NASDAQ stocks"
💬 "Backtest a mean reversion strategy on my current holdings"
💬 "Create a risk report for all accounts in PDF format"
💬 "Implement dollar-cost averaging for my portfolio"
```

---

## 🛠️ Available Tools & Capabilities

| Tool | Description | Use Case |
|------|-------------|----------|
| `get_account_info` | Account details and balances | Portfolio overview |
| `get_portfolio` | Holdings and P&L analysis | Performance tracking |
| `get_market_data` | Real-time quotes and data | Market analysis |
| `place_order` | Execute trading orders | Order management |
| `scan_market` | Market screening tools | Stock discovery |
| `get_historical_data` | Historical price data | Backtesting |
| `calculate_indicators` | Technical analysis | Chart analysis |

---

## 📖 Documentation

### 🚀 Getting Started
- **[Quick Start Guide](docs/QUICK_START_GUIDE.md)** - Get up and running in 30 minutes
- **[Claude Code Integration](docs/CLAUDE_CODE_INTEGRATION.md)** - Complete Claude setup guide
- **[Tiger Authentication](docs/TIGER_AUTHENTICATION_SETUP.md)** - API credential configuration

### 🔧 Development
- **[Development Guide](DEVELOPMENT.md)** - Technical details and workspace management
- **[Architecture Overview](ARCHITECTURE.md)** - System design and components
- **[API Reference](docs/API_REFERENCE.md)** - Complete MCP tools documentation

### 🚀 Deployment
- **[Production Deployment](docs/PRODUCTION_DEPLOYMENT.md)** - Production setup and best practices
- **[Docker Guide](docs/DOCKER.md)** - Containerization and orchestration
- **[Security Guide](docs/CLAUDE_CODE_SECURITY.md)** - Security guidelines and best practices

---

## 🎯 Use Cases

### 💼 **Portfolio Management**
- Real-time portfolio tracking and performance analysis
- Automated rebalancing and risk management
- Multi-account portfolio consolidation
- Tax-loss harvesting optimization

### 📈 **Algorithmic Trading**
- Strategy backtesting with historical data
- Automated order execution based on technical indicators
- Custom alert systems for market opportunities
- High-frequency trading with sub-second latency

### 🔍 **Market Research**
- Advanced market scanning and stock screening
- Fundamental and technical analysis automation
- Sector rotation and correlation analysis
- Options strategy analysis and optimization

### 🤖 **AI-Powered Insights**
- Natural language queries for market data
- Automated report generation and analysis
- Risk assessment and scenario modeling
- Intelligent trade recommendations

---

## 🏗️ Architecture

Tiger MCP is built using a modern, scalable architecture:

```mermaid
graph TB
    Claude[Claude AI] --> MCP[MCP Server]
    MCP --> Tiger[Tiger Brokers API]
    MCP --> DB[(PostgreSQL)]
    MCP --> Cache[(Redis)]
    
    Dashboard[Web Dashboard] --> API[FastAPI Backend]
    API --> DB
    API --> Tiger
    
    Docker[Docker Compose] --> MCP
    Docker --> API
    Docker --> DB
    Docker --> Cache
```

- **MCP Server**: FastMCP-based server with async/await patterns
- **Database**: PostgreSQL with async SQLAlchemy for data persistence
- **Caching**: Redis for high-performance data caching
- **Security**: JWT authentication with encrypted credentials storage
- **Monitoring**: Comprehensive logging and health check endpoints

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Process

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Code Standards

- **Python**: Black formatting, type hints, docstrings
- **Testing**: Minimum 80% test coverage required
- **Documentation**: Update docs for any new features
- **Security**: Follow security best practices

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer

**Important**: This software is for educational and research purposes. Trading financial instruments involves substantial risk and may not be suitable for all investors. Past performance does not guarantee future results. Always consult with financial professionals before making investment decisions.

---

## 🆘 Support & Community

- **📧 Issues**: [GitHub Issues](#)
- **📖 Documentation**: [Full Documentation](docs/)
- **🎯 Discussions**: [GitHub Discussions](#)
- **🐛 Bug Reports**: Use the bug report template
- **💡 Feature Requests**: Use the feature request template

---

## 🙏 Acknowledgments

- **[Tiger Brokers](https://www.tigerbrokers.com)** for providing robust API services
- **[Anthropic](https://anthropic.com)** for Claude AI and MCP protocol
- **[FastMCP](https://github.com/jlowin/fastmcp)** for the excellent MCP framework
- **[UV](https://docs.astral.sh/uv/)** for modern Python package management

---

<div align="center">

**⭐ Star this repository if you find it useful!**

**Built with ❤️ for the trading and AI community**

</div>

