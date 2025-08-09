# 🏗️ System Architecture

This document provides a comprehensive overview of the Tiger MCP system architecture, component interactions, and design decisions.

## 📋 Table of Contents

- [System Overview](#-system-overview)
- [Component Architecture](#-component-architecture)
- [Data Flow](#-data-flow)
- [Multi-Account Architecture](#-multi-account-architecture)
- [Security Architecture](#-security-architecture)
- [Deployment Architecture](#-deployment-architecture)
- [Scalability Considerations](#-scalability-considerations)

## 🎯 System Overview

Tiger MCP is a **professional-grade Model Context Protocol (MCP) server** that bridges the gap between Claude AI and Tiger Brokers trading platform. The system is designed with modern async/await patterns, enterprise security, and multi-account support.

### Core Design Principles

1. **Modularity**: Clear separation of concerns across packages
2. **Scalability**: Async/await patterns for high-throughput operations
3. **Security**: Multi-layer security with encrypted credentials and audit logging
4. **Reliability**: Comprehensive error handling and graceful degradation
5. **Maintainability**: Clean code architecture with type hints and documentation

## 🧩 Component Architecture

```mermaid
graph TB
    subgraph "External Systems"
        Claude[Claude AI Client]
        Tiger[Tiger Brokers API]
        Admin[Admin Dashboard]
    end
    
    subgraph "Tiger MCP System"
        subgraph "MCP Layer"
            MCP[MCP Server<br/>FastMCP Framework]
            Tools[MCP Tools<br/>Trading Operations]
        end
        
        subgraph "API Layer"
            API[Dashboard API<br/>FastAPI Backend]
            Auth[Authentication<br/>JWT + OAuth2]
        end
        
        subgraph "Business Logic"
            AccountMgr[Multi-Account Manager]
            TradeMgr[Trade Manager]
            DataMgr[Market Data Manager]
            RiskMgr[Risk Manager]
        end
        
        subgraph "Data Layer"
            DB[(PostgreSQL<br/>Primary Storage)]
            Cache[(Redis<br/>Cache Layer)]
        end
        
        subgraph "Infrastructure"
            Encryption[Encryption Service]
            Logging[Audit Logging]
            Monitoring[Health Checks]
        end
    end
    
    Claude --> MCP
    MCP --> Tools
    Tools --> AccountMgr
    Tools --> TradeMgr
    Tools --> DataMgr
    
    Admin --> API
    API --> Auth
    API --> AccountMgr
    API --> TradeMgr
    
    AccountMgr --> Tiger
    TradeMgr --> Tiger
    DataMgr --> Tiger
    DataMgr --> Cache
    
    TradeMgr --> DB
    AccountMgr --> DB
    Auth --> DB
    
    AccountMgr --> Encryption
    TradeMgr --> Logging
    API --> Monitoring
```

### Package Architecture

```
packages/
├── mcp-server/          # MCP Protocol Implementation
│   ├── tools/          # MCP tool implementations
│   ├── handlers/       # Request handlers
│   └── server.py       # FastMCP server
├── dashboard-api/      # REST API Backend
│   ├── routers/        # FastAPI routers
│   ├── middleware/     # Authentication & CORS
│   └── main.py         # FastAPI application
├── database/           # Data Persistence Layer
│   ├── models/         # SQLAlchemy models
│   ├── migrations/     # Alembic migrations
│   └── connection.py   # Database connection
└── shared/             # Shared Components
    ├── tiger_client.py # Tiger API client
    ├── encryption.py   # Encryption services
    ├── auth.py         # Authentication
    └── utils.py        # Common utilities
```

## 🔄 Data Flow

### 1. MCP Request Flow

```mermaid
sequenceDiagram
    participant C as Claude AI
    participant M as MCP Server
    participant A as Account Manager
    participant T as Tiger API
    participant D as Database
    
    C->>M: MCP Request (get_portfolio)
    M->>M: Parse & Validate Request
    M->>A: Route to Account Manager
    A->>A: Determine Target Account
    A->>T: Tiger API Call
    T->>A: Market Data Response
    A->>D: Cache & Store Data
    A->>M: Formatted Response
    M->>C: MCP Response
```

### 2. Multi-Account Request Flow

```mermaid
sequenceDiagram
    participant C as Claude AI
    participant M as MCP Server
    participant AM as Account Manager
    participant T1 as Tiger Account 1
    participant T2 as Tiger Account 2
    participant DB as Database
    
    C->>M: "Show portfolio for all accounts"
    M->>AM: Multi-account request
    
    par Account 1
        AM->>T1: Get Portfolio
        T1->>AM: Portfolio Data
    and Account 2
        AM->>T2: Get Portfolio
        T2->>AM: Portfolio Data
    end
    
    AM->>AM: Aggregate Results
    AM->>DB: Cache Aggregated Data
    AM->>M: Combined Response
    M->>C: Multi-account Portfolio
```

### 3. Trading Order Flow

```mermaid
sequenceDiagram
    participant C as Claude AI
    participant M as MCP Server
    participant TM as Trade Manager
    participant R as Risk Manager
    participant T as Tiger API
    participant L as Audit Logger
    
    C->>M: "Buy 100 AAPL"
    M->>TM: Parse Order Request
    TM->>R: Risk Assessment
    R->>TM: Risk Approval
    TM->>T: Submit Order
    T->>TM: Order Confirmation
    TM->>L: Log Trade Event
    TM->>M: Order Status
    M->>C: Trade Confirmation
```

## 🏢 Multi-Account Architecture

### Account Management System

The Tiger MCP system supports **multiple Tiger Brokers accounts** through a sophisticated account routing and management system.

```mermaid
graph TB
    subgraph "Account Configuration"
        Config[Environment Config]
        Primary[Primary Account]
        Additional[Additional Accounts]
        Permissions[Account Permissions]
    end
    
    subgraph "Account Manager"
        Router[Account Router]
        Validator[Account Validator]
        Aggregator[Data Aggregator]
        Switcher[Context Switcher]
    end
    
    subgraph "Tiger API Clients"
        Client1[Tiger Client 1<br/>Account A]
        Client2[Tiger Client 2<br/>Account B]
        Client3[Tiger Client 3<br/>Account C]
    end
    
    Config --> Router
    Router --> Validator
    Validator --> Client1
    Validator --> Client2
    Validator --> Client3
    
    Client1 --> Aggregator
    Client2 --> Aggregator
    Client3 --> Aggregator
```

### Account Configuration Schema

```yaml
# Primary account (default routing)
primary_account:
  account_id: "primary_account_id"
  client_id: "primary_client_id"
  private_key: "primary_private_key"
  permissions: ["read", "trade"]

# Additional accounts
additional_accounts:
  - account_id: "account_2_id"
    client_id: "account_2_client_id"
    private_key: "account_2_private_key"
    permissions: ["read", "trade"]
  
  - account_id: "account_3_id"
    client_id: "account_3_client_id"
    private_key: "account_3_private_key"
    permissions: ["read"]  # Read-only account

# Global settings
settings:
  default_account: "primary_account_id"
  trading_accounts: ["primary_account_id", "account_2_id"]
  max_accounts: 10
  account_validation: true
```

### Account Routing Logic

```python
class AccountRouter:
    def route_request(self, request: MCPRequest) -> str:
        """Route request to appropriate account."""
        # 1. Check for explicit account specification
        if account_id := request.params.get('account_id'):
            return self.validate_account(account_id)
        
        # 2. Use context-based routing
        if context_account := self.get_context_account():
            return context_account
        
        # 3. Fall back to default account
        return self.config.default_account
    
    def aggregate_accounts(self, operation: str) -> Dict[str, Any]:
        """Aggregate data across multiple accounts."""
        results = {}
        for account_id in self.get_accessible_accounts():
            try:
                client = self.get_tiger_client(account_id)
                data = getattr(client, operation)()
                results[account_id] = data
            except Exception as e:
                results[account_id] = {"error": str(e)}
        return results
```

## 🛡️ Security Architecture

### Multi-Layer Security Model

```mermaid
graph TB
    subgraph "Security Layers"
        subgraph "Transport Security"
            TLS[TLS 1.3 Encryption]
            Certs[SSL Certificates]
        end
        
        subgraph "Authentication Layer"
            JWT[JWT Tokens]
            OAuth[OAuth2 Flow]
            API[API Key Management]
        end
        
        subgraph "Authorization Layer"
            RBAC[Role-Based Access]
            Permissions[Account Permissions]
            Limits[Rate Limiting]
        end
        
        subgraph "Data Security"
            Encryption[Field-Level Encryption]
            Hashing[Password Hashing]
            Secrets[Secret Management]
        end
        
        subgraph "Audit & Monitoring"
            Logging[Audit Logging]
            Monitoring[Security Monitoring]
            Alerts[Security Alerts]
        end
    end
    
    TLS --> JWT
    JWT --> RBAC
    RBAC --> Encryption
    Encryption --> Logging
```

### Credential Management

```python
class SecureCredentialManager:
    """Secure credential storage and management."""
    
    def __init__(self):
        self.encryption_key = os.getenv('ENCRYPTION_KEY')
        self.fernet = Fernet(self.encryption_key)
    
    def store_credentials(self, account_id: str, credentials: Dict):
        """Store encrypted credentials."""
        encrypted_data = self.fernet.encrypt(
            json.dumps(credentials).encode()
        )
        return self.db.store_encrypted_credentials(
            account_id, encrypted_data
        )
    
    def get_credentials(self, account_id: str) -> Dict:
        """Retrieve and decrypt credentials."""
        encrypted_data = self.db.get_encrypted_credentials(account_id)
        decrypted_data = self.fernet.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode())
```

### Authentication Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant API as Dashboard API
    participant Auth as Auth Service
    participant DB as Database
    participant Tiger as Tiger API
    
    C->>API: Login Request
    API->>Auth: Validate Credentials
    Auth->>DB: Check User
    DB->>Auth: User Data
    Auth->>Tiger: Validate Tiger API Access
    Tiger->>Auth: API Validation
    Auth->>API: Generate JWT
    API->>C: JWT Token
    
    C->>API: API Request + JWT
    API->>Auth: Validate JWT
    Auth->>API: Token Valid
    API->>API: Process Request
    API->>C: Response
```

## 🚀 Deployment Architecture

### Container Architecture

```mermaid
graph TB
    subgraph "Load Balancer"
        LB[Nginx Load Balancer]
        SSL[SSL Termination]
    end
    
    subgraph "Application Layer"
        MCP1[MCP Server 1]
        MCP2[MCP Server 2]
        API1[Dashboard API 1]
        API2[Dashboard API 2]
    end
    
    subgraph "Data Layer"
        PG[(PostgreSQL Master)]
        PGR[(PostgreSQL Replica)]
        Redis[(Redis Cluster)]
    end
    
    subgraph "External Services"
        Tiger[Tiger Brokers API]
        Claude[Claude AI]
    end
    
    LB --> MCP1
    LB --> MCP2
    LB --> API1
    LB --> API2
    
    MCP1 --> PG
    MCP2 --> PG
    API1 --> PG
    API2 --> PGR
    
    MCP1 --> Redis
    MCP2 --> Redis
    API1 --> Redis
    API2 --> Redis
    
    MCP1 --> Tiger
    MCP2 --> Tiger
    Claude --> LB
```

### Docker Compose Structure

```yaml
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    depends_on: [mcp-server, dashboard-api]
  
  mcp-server:
    build: ./docker/mcp-server
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on: [postgres, redis]
    scale: 2
  
  dashboard-api:
    build: ./docker/dashboard-api
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on: [postgres, redis]
    scale: 2
  
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=${DB_NAME}
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
```

## 📈 Scalability Considerations

### Horizontal Scaling

```mermaid
graph TB
    subgraph "Scaling Strategies"
        subgraph "Application Scaling"
            MCPScale[MCP Server Scaling]
            APIScale[API Server Scaling]
            LoadBalance[Load Balancing]
        end
        
        subgraph "Data Scaling"
            DBReplicas[Database Read Replicas]
            RedisCluster[Redis Clustering]
            Caching[Multi-Level Caching]
        end
        
        subgraph "Account Scaling"
            AccountSharding[Account-Based Sharding]
            RegionDistribution[Regional Distribution]
            APIOptimization[API Call Optimization]
        end
    end
```

### Performance Optimization

1. **Connection Pooling**: Async connection pools for database and external APIs
2. **Caching Strategy**: Multi-level caching with Redis and in-memory caches
3. **Batch Processing**: Bulk operations for account aggregation
4. **Rate Limiting**: Smart rate limiting to respect Tiger API limits
5. **Circuit Breakers**: Fault tolerance for external service failures

### Multi-Account Scalability

```python
class ScalableAccountManager:
    """Scalable multi-account management."""
    
    def __init__(self):
        self.account_pool = AccountConnectionPool()
        self.cache = RedisCache()
        self.rate_limiter = RateLimiter()
    
    async def parallel_account_operation(
        self, operation: str, accounts: List[str]
    ) -> Dict[str, Any]:
        """Execute operation across accounts in parallel."""
        semaphore = asyncio.Semaphore(10)  # Limit concurrent operations
        
        async def execute_for_account(account_id: str):
            async with semaphore:
                await self.rate_limiter.wait(account_id)
                client = await self.account_pool.get_client(account_id)
                return await getattr(client, operation)()
        
        tasks = [
            execute_for_account(account_id) 
            for account_id in accounts
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            account_id: result 
            for account_id, result in zip(accounts, results)
        }
```

## 🔍 Monitoring & Observability

### Health Check Architecture

```python
class HealthCheckManager:
    """Comprehensive health monitoring."""
    
    async def get_system_health(self) -> Dict[str, Any]:
        return {
            "database": await self.check_database(),
            "redis": await self.check_redis(),
            "tiger_api": await self.check_tiger_api(),
            "accounts": await self.check_accounts(),
            "memory": self.get_memory_usage(),
            "cpu": self.get_cpu_usage(),
            "disk": self.get_disk_usage(),
        }
    
    async def check_accounts(self) -> Dict[str, str]:
        """Check health of all configured accounts."""
        results = {}
        for account_id in self.account_manager.get_accounts():
            try:
                client = self.account_manager.get_client(account_id)
                await client.get_account_info()
                results[account_id] = "healthy"
            except Exception as e:
                results[account_id] = f"unhealthy: {str(e)}"
        return results
```

### Metrics Collection

- **Application Metrics**: Request rates, response times, error rates
- **Business Metrics**: Trade volumes, account balances, P&L tracking
- **System Metrics**: CPU, memory, disk, network usage
- **Security Metrics**: Failed login attempts, API rate limiting events

This architecture provides a robust, scalable, and secure foundation for the Tiger MCP system, supporting multiple accounts while maintaining high performance and reliability.