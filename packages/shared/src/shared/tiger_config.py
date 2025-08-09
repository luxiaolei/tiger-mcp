"""
Tiger-specific configuration handling for Tiger MCP system.

This module provides utilities for handling Tiger Broker's .properties file format
configuration, which is the standard way Tiger SDK expects configuration.

Format:
- tiger_openapi_config.properties: Main configuration (private keys, credentials)
- tiger_openapi_token.properties: Access token (auto-managed by Tiger SDK)
"""

import os
import base64
import time
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass

from loguru import logger

try:
    from jproperties import Properties
except ImportError:
    logger.warning("jproperties not installed. Properties file support will be limited.")
    Properties = None


@dataclass
class TigerConfig:
    """Tiger API configuration data class."""
    
    tiger_id: str
    account: str
    license: str  # TBHK, TBSG, TBNZ, etc.
    environment: str  # PROD or SANDBOX
    private_key_pk1: str = ""
    private_key_pk8: str = ""
    
    @property
    def private_key(self) -> str:
        """Get the private key, preferring PK8 format."""
        return self.private_key_pk8 or self.private_key_pk1
    
    @property
    def private_key_format(self) -> str:
        """Get the format of the available private key."""
        if self.private_key_pk8:
            return "PK8"
        elif self.private_key_pk1:
            return "PK1"
        return "NONE"
    
    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        required_fields = [self.tiger_id, self.account, self.license, self.environment]
        return all(field.strip() for field in required_fields) and bool(self.private_key)


class TigerPropertiesManager:
    """Manager for Tiger .properties files."""
    
    DEFAULT_CONFIG_FILE = "tiger_openapi_config.properties"
    DEFAULT_TOKEN_FILE = "tiger_openapi_token.properties"
    
    def __init__(self, props_path: Optional[str] = None):
        """
        Initialize properties manager.
        
        Args:
            props_path: Directory containing .properties files, or None for current directory
        """
        self.props_path = Path(props_path) if props_path else Path.cwd()
        
    def _get_properties_path(self, filename: str) -> Path:
        """Get full path for properties file."""
        if self.props_path.is_file():
            # props_path is a specific file, use its directory
            return self.props_path.parent / filename
        else:
            # props_path is a directory
            return self.props_path / filename
    
    def load_config(self, config_file: Optional[str] = None) -> Optional[TigerConfig]:
        """
        Load Tiger configuration from .properties file.
        
        Args:
            config_file: Name of config file (defaults to tiger_openapi_config.properties)
            
        Returns:
            TigerConfig object or None if file doesn't exist or can't be parsed
        """
        if Properties is None:
            logger.error("jproperties not installed. Cannot load .properties files.")
            return None
            
        config_file = config_file or self.DEFAULT_CONFIG_FILE
        config_path = self._get_properties_path(config_file)
        
        if not config_path.exists():
            logger.debug(f"Config file not found: {config_path}")
            return None
        
        try:
            props = Properties()
            with open(config_path, "rb") as f:
                props.load(f, "utf-8")
            
            def get_prop(key: str, default: str = "") -> str:
                """Get property value safely."""
                prop = props.get(key)
                return prop.data if prop else default
            
            config = TigerConfig(
                tiger_id=get_prop("tiger_id"),
                account=get_prop("account"),
                license=get_prop("license"),
                environment=get_prop("env", "SANDBOX"),
                private_key_pk1=get_prop("private_key_pk1"),
                private_key_pk8=get_prop("private_key_pk8"),
            )
            
            if config.is_valid():
                logger.info(f"Loaded Tiger config from {config_path}")
                return config
            else:
                logger.error(f"Invalid Tiger config in {config_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading Tiger config from {config_path}: {e}")
            return None
    
    def save_config(self, config: TigerConfig, config_file: Optional[str] = None) -> bool:
        """
        Save Tiger configuration to .properties file.
        
        Args:
            config: TigerConfig to save
            config_file: Name of config file (defaults to tiger_openapi_config.properties)
            
        Returns:
            True if saved successfully, False otherwise
        """
        if Properties is None:
            logger.error("jproperties not installed. Cannot save .properties files.")
            return False
            
        config_file = config_file or self.DEFAULT_CONFIG_FILE
        config_path = self._get_properties_path(config_file)
        
        try:
            # Ensure directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            props = Properties()
            props["tiger_id"] = config.tiger_id
            props["account"] = config.account
            props["license"] = config.license
            props["env"] = config.environment
            
            if config.private_key_pk1:
                props["private_key_pk1"] = config.private_key_pk1
            if config.private_key_pk8:
                props["private_key_pk8"] = config.private_key_pk8
            
            with open(config_path, "wb") as f:
                props.store(f, encoding="utf-8")
            
            logger.info(f"Saved Tiger config to {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving Tiger config to {config_path}: {e}")
            return False
    
    def load_token(self, token_file: Optional[str] = None) -> Optional[str]:
        """
        Load Tiger access token from .properties file.
        
        Args:
            token_file: Name of token file (defaults to tiger_openapi_token.properties)
            
        Returns:
            Access token string or None if not found
        """
        if Properties is None:
            logger.error("jproperties not installed. Cannot load .properties files.")
            return None
            
        token_file = token_file or self.DEFAULT_TOKEN_FILE
        token_path = self._get_properties_path(token_file)
        
        if not token_path.exists():
            logger.debug(f"Token file not found: {token_path}")
            return None
        
        try:
            props = Properties()
            with open(token_path, "rb") as f:
                props.load(f, "utf-8")
            
            token_prop = props.get("token")
            token = token_prop.data if token_prop else None
            
            if token:
                logger.debug(f"Loaded Tiger token from {token_path}")
            return token
            
        except Exception as e:
            logger.error(f"Error loading Tiger token from {token_path}: {e}")
            return None
    
    def save_token(self, token: str, token_file: Optional[str] = None) -> bool:
        """
        Save Tiger access token to .properties file.
        
        Args:
            token: Access token to save
            token_file: Name of token file (defaults to tiger_openapi_token.properties)
            
        Returns:
            True if saved successfully, False otherwise
        """
        if Properties is None:
            logger.error("jproperties not installed. Cannot save .properties files.")
            return False
            
        token_file = token_file or self.DEFAULT_TOKEN_FILE
        token_path = self._get_properties_path(token_file)
        
        try:
            # Ensure directory exists
            token_path.parent.mkdir(parents=True, exist_ok=True)
            
            props = Properties()
            # Load existing properties if file exists
            if token_path.exists():
                with open(token_path, "rb") as f:
                    props.load(f, "utf-8")
            
            props["token"] = token
            
            with open(token_path, "wb") as f:
                props.store(f, encoding="utf-8")
            
            logger.debug(f"Saved Tiger token to {token_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving Tiger token to {token_path}: {e}")
            return False
    
    def is_token_expired(self, token: Optional[str] = None) -> bool:
        """
        Check if Tiger token is expired.
        
        Args:
            token: Token to check, or None to load from file
            
        Returns:
            True if token is expired or invalid, False otherwise
        """
        if token is None:
            token = self.load_token()
        
        if not token:
            return True
        
        try:
            # Tiger token format: base64(timestamp_gen,timestamp_exp+signature)
            decoded = base64.b64decode(token)
            timestamp_part = decoded[:27].decode('utf-8')  # First 27 characters
            gen_ts, expire_ts = timestamp_part.split(',')
            
            current_time_ms = int(time.time() * 1000)
            expire_time_ms = int(expire_ts)
            
            return current_time_ms >= expire_time_ms
            
        except Exception as e:
            logger.error(f"Error checking token expiry: {e}")
            return True
    
    def get_token_info(self, token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get information about Tiger token.
        
        Args:
            token: Token to analyze, or None to load from file
            
        Returns:
            Dictionary with token info or None if invalid
        """
        if token is None:
            token = self.load_token()
        
        if not token:
            return None
        
        try:
            decoded = base64.b64decode(token)
            timestamp_part = decoded[:27].decode('utf-8')
            gen_ts, expire_ts = timestamp_part.split(',')
            
            gen_time = int(gen_ts) / 1000  # Convert to seconds
            expire_time = int(expire_ts) / 1000  # Convert to seconds
            current_time = time.time()
            
            return {
                "generated_at": gen_time,
                "expires_at": expire_time,
                "current_time": current_time,
                "is_expired": current_time >= expire_time,
                "time_to_expiry": expire_time - current_time,
            }
            
        except Exception as e:
            logger.error(f"Error analyzing token: {e}")
            return None


def create_tiger_config_from_dict(config_dict: Dict[str, str]) -> TigerConfig:
    """
    Create TigerConfig from dictionary (e.g., from database).
    
    Args:
        config_dict: Dictionary with Tiger configuration
        
    Returns:
        TigerConfig object
    """
    return TigerConfig(
        tiger_id=config_dict.get("tiger_id", ""),
        account=config_dict.get("account", ""),
        license=config_dict.get("license", ""),
        environment=config_dict.get("environment", "SANDBOX"),
        private_key_pk1=config_dict.get("private_key_pk1", ""),
        private_key_pk8=config_dict.get("private_key_pk8", ""),
    )


def validate_tiger_credentials(config: TigerConfig) -> Tuple[bool, list[str]]:
    """
    Validate Tiger credentials.
    
    Args:
        config: TigerConfig to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if not config.tiger_id.strip():
        errors.append("Tiger ID is required")
    
    if not config.account.strip():
        errors.append("Account number is required")
    
    if not config.license.strip():
        errors.append("License is required")
    elif config.license not in ["TBHK", "TBSG", "TBNZ", "TBAU", "TBUK"]:
        errors.append(f"Invalid license: {config.license}. Must be one of: TBHK, TBSG, TBNZ, TBAU, TBUK")
    
    if not config.environment.strip():
        errors.append("Environment is required")
    elif config.environment not in ["PROD", "SANDBOX"]:
        errors.append(f"Invalid environment: {config.environment}. Must be PROD or SANDBOX")
    
    if not config.private_key.strip():
        errors.append("Private key is required")
    else:
        # Basic private key validation
        key = config.private_key.strip()
        if not (key.startswith("-----BEGIN") and key.endswith("-----")):
            errors.append("Private key must be in PEM format")
    
    return len(errors) == 0, errors


# Convenience functions for common operations

def load_tiger_config_from_properties(props_path: Optional[str] = None) -> Optional[TigerConfig]:
    """Load Tiger configuration from .properties file in specified directory."""
    manager = TigerPropertiesManager(props_path)
    return manager.load_config()


def save_tiger_config_to_properties(config: TigerConfig, props_path: Optional[str] = None) -> bool:
    """Save Tiger configuration to .properties file in specified directory."""
    manager = TigerPropertiesManager(props_path)
    return manager.save_config(config)


def get_tiger_token_info(props_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get Tiger token information from .properties file."""
    manager = TigerPropertiesManager(props_path)
    return manager.get_token_info()