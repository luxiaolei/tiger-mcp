#!/usr/bin/env python3
"""
Migration script to import Tiger account configuration from the existing dashboard.

This script reads the tiger_openapi_config.properties and tiger_openapi_token.properties
files from the old dashboard and imports them into the new Tiger MCP system.

Usage:
    python scripts/migrate_from_dashboard.py --dashboard-path /path/to/tiger_dashboard
    python scripts/migrate_from_dashboard.py --config-path /path/to/config/files
    python scripts/migrate_from_dashboard.py --help
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add the parent directory to Python path to import our packages
sys.path.insert(0, str(Path(__file__).parent.parent / "packages"))

from shared.src.shared.tiger_config import TigerPropertiesManager
from shared.src.shared.account_manager import TigerAccountManager
from database.src.database.engine import get_async_session


async def migrate_from_dashboard(config_path: str, account_name: str = None):
    """
    Migrate Tiger configuration from existing dashboard to new MCP system.
    
    Args:
        config_path: Path to directory containing .properties files
        account_name: Name for the imported account (optional)
    """
    config_file = os.path.join(config_path, "tiger_openapi_config.properties")
    token_file = os.path.join(config_path, "tiger_openapi_token.properties")
    
    if not os.path.exists(config_file):
        print(f"❌ Configuration file not found: {config_file}")
        return False
    
    print(f"📁 Reading configuration from: {config_path}")
    
    try:
        # Load configuration using Tiger properties manager
        props_manager = TigerPropertiesManager(config_path)
        tiger_config = props_manager.load_config()
        
        if not tiger_config:
            print("❌ Failed to load Tiger configuration from properties files")
            return False
            
        print(f"✅ Successfully loaded configuration for Tiger ID: {tiger_config.tiger_id}")
        print(f"   Account: {tiger_config.account}")
        print(f"   License: {tiger_config.license}")
        print(f"   Environment: {tiger_config.environment}")
        
        # Load token if available
        token = None
        if os.path.exists(token_file):
            token = props_manager.load_token()
            if token:
                print(f"✅ Token loaded and validated")
            else:
                print("⚠️  Token file exists but token is invalid or expired")
        else:
            print("⚠️  No token file found - will need to authenticate later")
        
        # Create account name if not provided
        if not account_name:
            account_name = f"{tiger_config.license}_{tiger_config.account}"
            
        print(f"📝 Creating account with name: {account_name}")
        
        # Initialize account manager and create account
        async with get_async_session() as session:
            account_manager = TigerAccountManager(session)
            
            account = await account_manager.create_account_from_properties(
                name=account_name,
                tiger_config=tiger_config,
                token=token,
                is_default_trading=True,  # First migrated account becomes default
                is_default_data=True
            )
            
            if account:
                print(f"🎉 Successfully created account: {account.name}")
                print(f"   Account ID: {account.id}")
                print(f"   Status: {account.status}")
                print(f"   Default Trading: {account.is_default_trading}")
                print(f"   Default Data: {account.is_default_data}")
                return True
            else:
                print("❌ Failed to create account in database")
                return False
                
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(
        description="Migrate Tiger account configuration from existing dashboard to MCP system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Migrate from dashboard directory
    python scripts/migrate_from_dashboard.py --dashboard-path ./references/tiger_dashboard
    
    # Migrate from specific config directory
    python scripts/migrate_from_dashboard.py --config-path /path/to/config --account-name MyTigerAccount
    
    # List what will be migrated (dry run)
    python scripts/migrate_from_dashboard.py --dashboard-path ./references/tiger_dashboard --dry-run
        """
    )
    
    parser.add_argument(
        "--dashboard-path",
        help="Path to the existing tiger_dashboard directory"
    )
    
    parser.add_argument(
        "--config-path", 
        help="Path to directory containing .properties files"
    )
    
    parser.add_argument(
        "--account-name",
        help="Name for the imported account (default: auto-generated)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes"
    )
    
    args = parser.parse_args()
    
    # Determine config path
    config_path = None
    if args.dashboard_path:
        config_path = args.dashboard_path
    elif args.config_path:
        config_path = args.config_path
    else:
        print("❌ Must specify either --dashboard-path or --config-path")
        parser.print_help()
        return 1
    
    if not os.path.exists(config_path):
        print(f"❌ Path does not exist: {config_path}")
        return 1
    
    print("🚀 Tiger Dashboard Migration Tool")
    print("=" * 50)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print()
        
        # Check what files exist
        config_file = os.path.join(config_path, "tiger_openapi_config.properties")
        token_file = os.path.join(config_path, "tiger_openapi_token.properties")
        
        if os.path.exists(config_file):
            print(f"✅ Found config file: {config_file}")
            try:
                props_manager = TigerPropertiesManager(config_path)
                tiger_config = props_manager.load_config()
                if tiger_config:
                    print(f"   Tiger ID: {tiger_config.tiger_id}")
                    print(f"   Account: {tiger_config.account}")
                    print(f"   License: {tiger_config.license}")
                    print(f"   Environment: {tiger_config.environment}")
                else:
                    print("   ⚠️  Failed to parse configuration")
            except Exception as e:
                print(f"   ❌ Error reading config: {e}")
        else:
            print(f"❌ Config file not found: {config_file}")
            
        if os.path.exists(token_file):
            print(f"✅ Found token file: {token_file}")
        else:
            print(f"⚠️  Token file not found: {token_file}")
            
        print("\nTo perform the actual migration, run without --dry-run")
        return 0
    
    # Perform migration
    try:
        success = asyncio.run(migrate_from_dashboard(config_path, args.account_name))
        if success:
            print("\n🎉 Migration completed successfully!")
            print("\nNext steps:")
            print("1. Start the MCP server: tiger-mcp-server")
            print("2. Test the connection: tiger-mcp-server health")
            print("3. Use MCP tools to verify account is working")
            return 0
        else:
            print("\n❌ Migration failed. Please check the error messages above.")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️  Migration cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())