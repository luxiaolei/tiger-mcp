# 🚀 Tiger MCP 安装使用指南

## 🎯 **快速安装 (从GitHub)**

### 1. 安装Tiger MCP
```bash
pip install git+https://github.com/your-username/tiger-mcp.git
```

### 2. 配置Tiger API credentials
```bash
# 复制配置文件模板
cp tiger_openapi_config.properties.example tiger_openapi_config.properties
cp tiger_openapi_token.properties.example tiger_openapi_token.properties

# 编辑配置文件，填入你的Tiger API信息
vim tiger_openapi_config.properties
```

### 3. 配置账户权限 (服务器管理员)
```bash
cp config/tiger_accounts.json.example config/tiger_accounts.json
# 编辑添加账户和API Key配置
```

## 📋 **配置说明**

### Tiger API配置 (`tiger_openapi_config.properties`)
```properties
# 从Tiger开发者平台获取这些信息:
# https://quant.itiger.com/openapi/info

private_key_pk1=YOUR_PRIVATE_KEY_PK1_HERE  # RSA私钥PK1格式
private_key_pk8=YOUR_PRIVATE_KEY_PK8_HERE  # RSA私钥PK8格式
tiger_id=YOUR_TIGER_ID_HERE                # 开发者ID
account=YOUR_ACCOUNT_NUMBER_HERE           # 账户号码
license=TBHK                               # 牌照 (TBHK/TBSG/TBNZ)
env=PROD                                   # 环境 (PROD/SANDBOX)
```

### 账户权限配置 (`config/tiger_accounts.json`)
```json
{
  "tiger_accounts": {
    "YOUR_DEMO_ACCOUNT": {
      "tiger_id": "YOUR_TIGER_ID",
      "account_type": "demo",
      "license": "TBHK"
    }
  },
  "api_keys": {
    "client_key_demo": {
      "allowed_accounts": ["YOUR_DEMO_ACCOUNT"],
      "permissions": ["read", "trade"]
    }
  }
}
```

## 🔧 **使用方式**

### 方式1: 服务器模式 (推荐)
```bash
# 启动Tiger MCP服务器
tiger-mcp-server --port 9000

# 客户端连接 (其他电脑)
pip install git+https://github.com/your-username/tiger-mcp.git
tiger-mcp-client --server http://your-server:9000 --api-key client_key_demo
```

### 方式2: Claude Code集成
```bash
# 1. 安装
pip install git+https://github.com/your-username/tiger-mcp.git

# 2. 配置Claude Code (.mcp.json)
cp .mcp.json.example .mcp.json
# 编辑填入你的配置

# 3. 重启Claude Code
```

### 方式3: Python程序调用
```python
import requests

# REST API调用
response = requests.post("http://your-server:9000/tiger/get_positions", 
    headers={"Authorization": "Bearer client_key_demo"},
    json={"account": "YOUR_DEMO_ACCOUNT"}
)

positions = response.json()
print(positions)
```

## 🔐 **安全须知**

### ⚠️ **敏感文件 (已gitignore, 不会提交)**
- `tiger_openapi_config.properties` - 包含私钥
- `tiger_openapi_token.properties` - 包含访问token  
- `config/tiger_accounts.json` - 包含API Key配置
- `.mcp.json` - 包含客户端配置

### ✅ **安全实践**
- 只在Demo账户测试
- Live账户谨慎使用
- API Key定期轮换
- 服务器端设置防火墙

## 🎯 **典型使用场景**

### 场景1: 算法交易开发者
```bash
pip install git+https://github.com/your-username/tiger-mcp.git
tiger-mcp-client --server http://trading-server:9000 --api-key my_key
```

### 场景2: Claude Code用户
```bash
pip install git+https://github.com/your-username/tiger-mcp.git
# 配置.mcp.json
# 重启Claude Code
# 在Claude中: "帮我查看持仓"
```

### 场景3: Python开发者
```python
# 直接API调用
import tiger_mcp_client as tiger
client = tiger.Client("http://server:9000", "api_key")
positions = client.get_positions("account_id")
```

---

## 🚀 **开始使用**

1. **服务器管理员**: 部署Tiger MCP服务器
2. **客户端用户**: `pip install git+https://github.com/...`
3. **配置credentials**: 复制example文件并填入信息  
4. **开始交易**: 连接到服务器开始使用

**简单、安全、开源！** 🎉