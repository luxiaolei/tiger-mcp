"""
TigerAccountManager for managing Tiger Broker accounts.

Provides CRUD operations for Tiger accounts with integrated encryption,
credential management, and database operations using async/await patterns.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

from loguru import logger
from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Note: These imports assume the database package is available in the Python path
# In a real deployment, you may need to adjust these import paths
try:
    from database.engine import get_session
    from database.models.accounts import (
        AccountStatus,
        AccountType,
        MarketPermission,
        TigerAccount,
        TigerLicense,
        TigerEnvironment,
    )
    from database.models.token_status import TokenStatus
except ImportError:
    # Fallback for development/testing - these would need to be properly configured
    print(
        "Warning: Database imports not available. Please ensure database package is in Python path."
    )
    # You can define mock classes here for testing, or raise an error
    raise ImportError("Database package required but not found in Python path")

from .config import get_config
from .encryption import (
    EncryptedData,
    encrypt_tiger_credentials,
    get_encryption_service,
)
from .tiger_config import (
    TigerConfig,
    TigerPropertiesManager,
    create_tiger_config_from_dict,
    validate_tiger_credentials,
)


class AccountManagerError(Exception):
    """Base exception for account manager operations."""


class AccountNotFoundError(AccountManagerError):
    """Exception raised when account is not found."""


class AccountValidationError(AccountManagerError):
    """Exception raised when account validation fails."""


class DefaultAccountError(AccountManagerError):
    """Exception raised when default account operations fail."""


class TigerAccountManager:
    """
    Comprehensive Tiger account management service.

    Handles CRUD operations for Tiger accounts with integrated encryption,
    credential management, default account handling, and error tracking.
    """

    def __init__(self):
        """Initialize account manager."""
        self._config = get_config()
        self._encryption_service = get_encryption_service()
        logger.info("TigerAccountManager initialized")

    async def create_account(
        self,
        account_name: str,
        account_number: str,
        tiger_id: str,
        private_key: str,
        license: TigerLicense,
        account_type: AccountType = AccountType.STANDARD,
        environment: TigerEnvironment = TigerEnvironment.SANDBOX,
        private_key_format: str = "PK1",
        market_permissions: Optional[List[MarketPermission]] = None,
        description: Optional[str] = None,
        tags: Optional[Dict] = None,
        is_default_trading: bool = False,
        is_default_data: bool = False,
        server_url: Optional[str] = None,
    ) -> TigerAccount:
        """
        Create a new Tiger account with encrypted credentials.

        Args:
            account_name: User-friendly account name
            account_number: Tiger account number
            tiger_id: Tiger developer ID for API access
            private_key: RSA private key for Tiger API
            license: Tiger broker license (TBHK, TBSG, TBNZ, etc.)
            account_type: Type of account (standard/paper/prime)
            environment: Tiger environment (PROD/SANDBOX)
            private_key_format: Format of private key (PK1 or PK8)
            market_permissions: List of market permissions
            description: Optional account description
            tags: Optional account tags
            is_default_trading: Set as default trading account
            is_default_data: Set as default data account
            server_url: Custom server URL

        Returns:
            Created TigerAccount instance

        Raises:
            AccountValidationError: If validation fails
            AccountManagerError: If creation fails
        """
        try:
            # Validate input using Tiger validation
            tiger_config = TigerConfig(
                tiger_id=tiger_id,
                account=account_number,
                license=license.value,
                environment=environment.value,
                private_key_pk1=private_key if private_key_format == "PK1" else "",
                private_key_pk8=private_key if private_key_format == "PK8" else "",
            )
            
            is_valid, errors = validate_tiger_credentials(tiger_config)
            if not is_valid:
                raise AccountValidationError(f"Tiger validation failed: {'; '.join(errors)}")
            
            # Additional basic validation
            if not account_name or len(account_name.strip()) == 0:
                raise AccountValidationError("Account name is required")
            
            if private_key_format not in ["PK1", "PK8"]:
                raise AccountValidationError("Private key format must be PK1 or PK8")

            # Check for duplicate account number
            async with get_session() as session:
                existing = await self._get_account_by_number(session, account_number)
                if existing:
                    raise AccountValidationError(
                        f"Account number {account_number} already exists"
                    )

                # Handle default account logic
                if is_default_trading:
                    await self._clear_default_trading_account(session)
                if is_default_data:
                    await self._clear_default_data_account(session)

                # Encrypt credentials
                encrypted_credentials = encrypt_tiger_credentials(tiger_id, private_key)

                # Create account instance
                account = TigerAccount(
                    account_name=account_name,
                    account_number=account_number,
                    account_type=account_type,
                    tiger_id=encrypted_credentials["tiger_id"].json(),
                    private_key=encrypted_credentials["private_key"].json(),
                    license=license,
                    environment=environment,
                    private_key_format=private_key_format,
                    server_url=server_url,
                    is_default_trading=is_default_trading,
                    is_default_data=is_default_data,
                    description=description,
                    tags=tags or {},
                    market_permissions={"permissions": []},
                )

                # Set market permissions
                if market_permissions:
                    for permission in market_permissions:
                        account.add_market_permission(permission)

                # Add to session and flush to get ID
                session.add(account)
                await session.flush()

                # Create initial token status for scheduling
                initial_token_status = TokenStatus.create_scheduled_refresh(
                    tiger_account_id=account.id,
                    next_refresh_at=datetime.utcnow() + timedelta(hours=1),
                )
                session.add(initial_token_status)

                await session.commit()

                logger.info(
                    f"Created Tiger account: {account_name} ({account_number}) "
                    f"in {environment} environment"
                )

                return account

        except Exception as e:
            logger.error(f"Failed to create account {account_name}: {e}")
            if isinstance(e, AccountManagerError):
                raise
            raise AccountManagerError(f"Failed to create account: {e}")

    async def get_account_by_id(self, account_id: uuid.UUID) -> Optional[TigerAccount]:
        """
        Get account by ID with relationships loaded.

        Args:
            account_id: Account UUID

        Returns:
            TigerAccount instance or None if not found
        """
        try:
            async with get_session() as session:
                stmt = (
                    select(TigerAccount)
                    .options(
                        selectinload(TigerAccount.token_statuses),
                        selectinload(TigerAccount.api_keys),
                    )
                    .where(TigerAccount.id == account_id)
                )
                result = await session.execute(stmt)
                return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Failed to get account by ID {account_id}: {e}")
            raise AccountManagerError(f"Failed to get account: {e}")

    async def get_account_by_number(
        self, account_number: str
    ) -> Optional[TigerAccount]:
        """
        Get account by account number.

        Args:
            account_number: Tiger account number

        Returns:
            TigerAccount instance or None if not found
        """
        try:
            async with get_session() as session:
                return await self._get_account_by_number(session, account_number)

        except Exception as e:
            logger.error(f"Failed to get account by number {account_number}: {e}")
            raise AccountManagerError(f"Failed to get account: {e}")

    async def list_accounts(
        self,
        account_type: Optional[AccountType] = None,
        status: Optional[AccountStatus] = None,
        environment: Optional[TigerEnvironment] = None,
        license: Optional[TigerLicense] = None,
        include_inactive: bool = False,
    ) -> List[TigerAccount]:
        """
        List accounts with optional filtering.

        Args:
            account_type: Filter by account type
            status: Filter by account status
            environment: Filter by environment (PROD/SANDBOX)
            license: Filter by license (TBHK, TBSG, TBNZ, etc.)
            include_inactive: Include inactive accounts

        Returns:
            List of TigerAccount instances
        """
        try:
            async with get_session() as session:
                stmt = select(TigerAccount).options(
                    selectinload(TigerAccount.token_statuses),
                    selectinload(TigerAccount.api_keys),
                )

                # Build filters
                filters = []

                if account_type:
                    filters.append(TigerAccount.account_type == account_type)

                if status:
                    filters.append(TigerAccount.status == status)
                elif not include_inactive:
                    filters.append(TigerAccount.status == AccountStatus.ACTIVE)

                if environment:
                    filters.append(TigerAccount.environment == environment)
                    
                if license:
                    filters.append(TigerAccount.license == license)

                if filters:
                    stmt = stmt.where(and_(*filters))

                stmt = stmt.order_by(TigerAccount.created_at.desc())

                result = await session.execute(stmt)
                return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Failed to list accounts: {e}")
            raise AccountManagerError(f"Failed to list accounts: {e}")

    async def update_account(
        self, account_id: uuid.UUID, updates: Dict[str, Union[str, bool, Dict, List]]
    ) -> TigerAccount:
        """
        Update account with validation and credential encryption.

        Args:
            account_id: Account UUID
            updates: Dictionary of fields to update

        Returns:
            Updated TigerAccount instance

        Raises:
            AccountNotFoundError: If account not found
            AccountValidationError: If validation fails
        """
        try:
            async with get_session() as session:
                account = await self._get_account_by_id_for_update(session, account_id)
                if not account:
                    raise AccountNotFoundError(f"Account {account_id} not found")

                # Handle credential updates with encryption
                if "tiger_id" in updates or "private_key" in updates:
                    # Decrypt current credentials to get complete set
                    current_credentials = await self.decrypt_credentials(account)

                    tiger_id = updates.get(
                        "tiger_id", current_credentials.get("tiger_id")
                    )
                    private_key = updates.get(
                        "private_key", current_credentials.get("private_key")
                    )

                    if tiger_id and private_key:
                        encrypted_credentials = encrypt_tiger_credentials(
                            tiger_id, private_key
                        )
                        updates["tiger_id"] = encrypted_credentials["tiger_id"].json()
                        updates["private_key"] = encrypted_credentials[
                            "private_key"
                        ].json()

                # Handle default account logic
                if updates.get("is_default_trading"):
                    await self._clear_default_trading_account(
                        session, exclude_id=account_id
                    )
                if updates.get("is_default_data"):
                    await self._clear_default_data_account(
                        session, exclude_id=account_id
                    )

                # Apply updates
                for field, value in updates.items():
                    if hasattr(account, field):
                        setattr(account, field, value)

                # Update timestamp
                account.updated_at = datetime.utcnow()

                await session.commit()

                logger.info(f"Updated account {account.account_name} ({account_id})")
                return account

        except AccountManagerError:
            raise
        except Exception as e:
            logger.error(f"Failed to update account {account_id}: {e}")
            raise AccountManagerError(f"Failed to update account: {e}")

    async def delete_account(self, account_id: uuid.UUID, force: bool = False) -> bool:
        """
        Delete account with safety checks.

        Args:
            account_id: Account UUID
            force: Force deletion even if account has dependencies

        Returns:
            True if deleted successfully

        Raises:
            AccountNotFoundError: If account not found
            AccountValidationError: If account has dependencies and force=False
        """
        try:
            async with get_session() as session:
                account = await self._get_account_by_id_for_update(session, account_id)
                if not account:
                    raise AccountNotFoundError(f"Account {account_id} not found")

                # Check for dependencies if not forcing
                if not force:
                    if account.api_keys:
                        raise AccountValidationError(
                            f"Cannot delete account {account.account_name}: has {len(account.api_keys)} API keys"
                        )

                # Remove from session
                await session.delete(account)
                await session.commit()

                logger.info(f"Deleted account {account.account_name} ({account_id})")
                return True

        except AccountManagerError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete account {account_id}: {e}")
            raise AccountManagerError(f"Failed to delete account: {e}")

    async def get_default_trading_account(self) -> Optional[TigerAccount]:
        """Get the default trading account."""
        try:
            async with get_session() as session:
                stmt = select(TigerAccount).where(
                    and_(
                        TigerAccount.is_default_trading == True,
                        TigerAccount.status == AccountStatus.ACTIVE,
                    )
                )
                result = await session.execute(stmt)
                return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Failed to get default trading account: {e}")
            raise AccountManagerError(f"Failed to get default trading account: {e}")

    async def get_default_data_account(self) -> Optional[TigerAccount]:
        """Get the default data account."""
        try:
            async with get_session() as session:
                stmt = select(TigerAccount).where(
                    and_(
                        TigerAccount.is_default_data == True,
                        TigerAccount.status == AccountStatus.ACTIVE,
                    )
                )
                result = await session.execute(stmt)
                return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Failed to get default data account: {e}")
            raise AccountManagerError(f"Failed to get default data account: {e}")

    async def set_default_trading_account(self, account_id: uuid.UUID) -> TigerAccount:
        """
        Set an account as the default trading account.

        Args:
            account_id: Account UUID

        Returns:
            Updated account

        Raises:
            AccountNotFoundError: If account not found
        """
        try:
            async with get_session() as session:
                # Clear current default
                await self._clear_default_trading_account(session)

                # Set new default
                account = await self._get_account_by_id_for_update(session, account_id)
                if not account:
                    raise AccountNotFoundError(f"Account {account_id} not found")

                account.is_default_trading = True
                await session.commit()

                logger.info(f"Set {account.account_name} as default trading account")
                return account

        except AccountManagerError:
            raise
        except Exception as e:
            logger.error(f"Failed to set default trading account: {e}")
            raise AccountManagerError(f"Failed to set default trading account: {e}")

    async def set_default_data_account(self, account_id: uuid.UUID) -> TigerAccount:
        """
        Set an account as the default data account.

        Args:
            account_id: Account UUID

        Returns:
            Updated account

        Raises:
            AccountNotFoundError: If account not found
        """
        try:
            async with get_session() as session:
                # Clear current default
                await self._clear_default_data_account(session)

                # Set new default
                account = await self._get_account_by_id_for_update(session, account_id)
                if not account:
                    raise AccountNotFoundError(f"Account {account_id} not found")

                account.is_default_data = True
                await session.commit()

                logger.info(f"Set {account.account_name} as default data account")
                return account

        except AccountManagerError:
            raise
        except Exception as e:
            logger.error(f"Failed to set default data account: {e}")
            raise AccountManagerError(f"Failed to set default data account: {e}")

    async def update_account_status(
        self, account_id: uuid.UUID, status: AccountStatus, reason: Optional[str] = None
    ) -> TigerAccount:
        """
        Update account status with optional reason.

        Args:
            account_id: Account UUID
            status: New status
            reason: Optional reason for status change

        Returns:
            Updated account
        """
        updates = {"status": status}
        if reason:
            updates["tags"] = {
                "status_change_reason": reason,
                "status_changed_at": datetime.utcnow().isoformat(),
            }

        return await self.update_account(account_id, updates)

    async def increment_error_count(
        self, account_id: uuid.UUID, error_message: str
    ) -> TigerAccount:
        """
        Increment error count for an account.

        Args:
            account_id: Account UUID
            error_message: Error message

        Returns:
            Updated account
        """
        try:
            async with get_session() as session:
                account = await self._get_account_by_id_for_update(session, account_id)
                if not account:
                    raise AccountNotFoundError(f"Account {account_id} not found")

                account.increment_error_count(error_message)

                # Auto-suspend if too many errors
                if account.error_count >= 10:
                    account.status = AccountStatus.SUSPENDED
                    logger.warning(
                        f"Account {account.account_name} suspended due to {account.error_count} consecutive errors"
                    )

                await session.commit()
                return account

        except AccountManagerError:
            raise
        except Exception as e:
            logger.error(f"Failed to increment error count: {e}")
            raise AccountManagerError(f"Failed to increment error count: {e}")

    async def reset_error_count(self, account_id: uuid.UUID) -> TigerAccount:
        """
        Reset error count for an account.

        Args:
            account_id: Account UUID

        Returns:
            Updated account
        """
        try:
            async with get_session() as session:
                account = await self._get_account_by_id_for_update(session, account_id)
                if not account:
                    raise AccountNotFoundError(f"Account {account_id} not found")

                account.reset_error_count()

                # Reactivate if was suspended due to errors
                if account.status == AccountStatus.SUSPENDED:
                    account.status = AccountStatus.ACTIVE
                    logger.info(f"Reactivated account {account.account_name}")

                await session.commit()
                return account

        except AccountManagerError:
            raise
        except Exception as e:
            logger.error(f"Failed to reset error count: {e}")
            raise AccountManagerError(f"Failed to reset error count: {e}")

    async def update_tokens(
        self,
        account_id: uuid.UUID,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        token_expires_at: Optional[datetime] = None,
    ) -> TigerAccount:
        """
        Update account tokens with encryption.

        Args:
            account_id: Account UUID
            access_token: New access token
            refresh_token: New refresh token
            token_expires_at: Token expiration time

        Returns:
            Updated account
        """
        try:
            async with get_session() as session:
                account = await self._get_account_by_id_for_update(session, account_id)
                if not account:
                    raise AccountNotFoundError(f"Account {account_id} not found")

                # Encrypt tokens if provided
                if access_token:
                    encrypted_access = self._encryption_service.encrypt(access_token)
                    account.access_token = encrypted_access.json()

                if refresh_token:
                    encrypted_refresh = self._encryption_service.encrypt(refresh_token)
                    account.refresh_token = encrypted_refresh.json()

                if token_expires_at:
                    account.token_expires_at = token_expires_at

                await session.commit()

                logger.info(f"Updated tokens for account {account.account_name}")
                return account

        except AccountManagerError:
            raise
        except Exception as e:
            logger.error(f"Failed to update tokens: {e}")
            raise AccountManagerError(f"Failed to update tokens: {e}")

    async def decrypt_credentials(self, account: TigerAccount) -> Dict[str, str]:
        """
        Decrypt account credentials.

        Args:
            account: TigerAccount instance

        Returns:
            Dictionary with decrypted credentials

        Raises:
            AccountManagerError: If decryption fails
        """
        try:
            credentials = {}

            # Decrypt tiger_id
            if account.tiger_id:
                encrypted_tiger_id = EncryptedData.parse_raw(account.tiger_id)
                credentials["tiger_id"] = self._encryption_service.decrypt_to_string(
                    encrypted_tiger_id
                )

            # Decrypt private_key
            if account.private_key:
                encrypted_private_key = EncryptedData.parse_raw(account.private_key)
                credentials["private_key"] = self._encryption_service.decrypt_to_string(
                    encrypted_private_key
                )

            # Decrypt access_token if available
            if account.access_token:
                encrypted_access_token = EncryptedData.parse_raw(account.access_token)
                credentials["access_token"] = (
                    self._encryption_service.decrypt_to_string(encrypted_access_token)
                )

            # Decrypt refresh_token if available
            if account.refresh_token:
                encrypted_refresh_token = EncryptedData.parse_raw(account.refresh_token)
                credentials["refresh_token"] = (
                    self._encryption_service.decrypt_to_string(encrypted_refresh_token)
                )

            return credentials

        except Exception as e:
            logger.error(
                f"Failed to decrypt credentials for account {account.account_name}: {e}"
            )
            raise AccountManagerError(f"Failed to decrypt credentials: {e}")

    async def get_accounts_needing_token_refresh(self) -> List[TigerAccount]:
        """
        Get accounts that need token refresh.

        Returns:
            List of accounts needing refresh
        """
        try:
            async with get_session() as session:
                stmt = select(TigerAccount).where(
                    and_(
                        TigerAccount.status == AccountStatus.ACTIVE,
                        or_(
                            TigerAccount.token_expires_at.is_(None),
                            TigerAccount.token_expires_at
                            < datetime.utcnow() + timedelta(hours=1),
                        ),
                    )
                )
                result = await session.execute(stmt)
                return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Failed to get accounts needing token refresh: {e}")
            raise AccountManagerError(
                f"Failed to get accounts needing token refresh: {e}"
            )
    
    async def create_account_from_properties(
        self, 
        account_name: str, 
        properties_path: Optional[str] = None,
        account_type: AccountType = AccountType.STANDARD,
        is_default_trading: bool = False,
        is_default_data: bool = False,
        description: Optional[str] = None,
        tags: Optional[Dict] = None,
    ) -> TigerAccount:
        """
        Create account from Tiger .properties file.
        
        Args:
            account_name: User-friendly account name
            properties_path: Path to .properties file directory
            account_type: Type of account
            is_default_trading: Set as default trading account
            is_default_data: Set as default data account
            description: Optional description
            tags: Optional tags
            
        Returns:
            Created TigerAccount instance
            
        Raises:
            AccountValidationError: If properties file invalid or not found
            AccountManagerError: If creation fails
        """
        try:
            props_manager = TigerPropertiesManager(properties_path)
            tiger_config = props_manager.load_config()
            
            if not tiger_config:
                raise AccountValidationError(
                    f"Could not load Tiger configuration from {properties_path or 'current directory'}"
                )
            
            return await self.create_account(
                account_name=account_name,
                account_number=tiger_config.account,
                tiger_id=tiger_config.tiger_id,
                private_key=tiger_config.private_key,
                license=TigerLicense(tiger_config.license),
                account_type=account_type,
                environment=TigerEnvironment(tiger_config.environment),
                private_key_format=tiger_config.private_key_format,
                description=description,
                tags=tags,
                is_default_trading=is_default_trading,
                is_default_data=is_default_data,
            )
            
        except (ValueError, KeyError) as e:
            raise AccountValidationError(f"Invalid Tiger configuration: {e}")
        except AccountManagerError:
            raise
        except Exception as e:
            logger.error(f"Failed to create account from properties: {e}")
            raise AccountManagerError(f"Failed to create account from properties: {e}")
    
    async def export_account_to_properties(
        self, 
        account_id: uuid.UUID,
        properties_path: Optional[str] = None,
        include_token: bool = True,
    ) -> bool:
        """
        Export account configuration to Tiger .properties files.
        
        Args:
            account_id: Account UUID
            properties_path: Path to save .properties files
            include_token: Whether to include token in export
            
        Returns:
            True if export successful
            
        Raises:
            AccountNotFoundError: If account not found
            AccountManagerError: If export fails
        """
        try:
            async with get_session() as session:
                account = await self._get_account_by_id_for_update(session, account_id)
                if not account:
                    raise AccountNotFoundError(f"Account {account_id} not found")
                
                # Decrypt credentials
                credentials = await self.decrypt_credentials(account)
                
                # Create Tiger config
                tiger_config = TigerConfig(
                    tiger_id=credentials["tiger_id"],
                    account=account.account_number,
                    license=account.license.value,
                    environment=account.environment.value,
                    private_key_pk1=credentials["private_key"] if account.private_key_format == "PK1" else "",
                    private_key_pk8=credentials["private_key"] if account.private_key_format == "PK8" else "",
                )
                
                # Save to properties file
                props_manager = TigerPropertiesManager(properties_path)
                config_saved = props_manager.save_config(tiger_config)
                
                if not config_saved:
                    raise AccountManagerError("Failed to save configuration file")
                
                # Save token if requested and available
                if include_token and "access_token" in credentials:
                    props_manager.save_token(credentials["access_token"])
                
                logger.info(f"Exported account {account.account_name} to properties files")
                return True
                
        except AccountManagerError:
            raise
        except Exception as e:
            logger.error(f"Failed to export account to properties: {e}")
            raise AccountManagerError(f"Failed to export account to properties: {e}")

    # Private helper methods

    async def _validate_account_data(
        self,
        account_name: str,
        account_number: str,
        tiger_id: str,
        private_key: str,
        environment: TigerEnvironment,
    ) -> None:
        """Validate basic account data before creation/update."""
        if not account_name or len(account_name.strip()) == 0:
            raise AccountValidationError("Account name is required")

        if not account_number or len(account_number.strip()) == 0:
            raise AccountValidationError("Account number is required")

        if not tiger_id or len(tiger_id.strip()) == 0:
            raise AccountValidationError("Tiger ID is required")

        if not private_key or len(private_key.strip()) == 0:
            raise AccountValidationError("Private key is required")

    async def _get_account_by_number(
        self, session: AsyncSession, account_number: str
    ) -> Optional[TigerAccount]:
        """Get account by number within a session."""
        stmt = select(TigerAccount).where(TigerAccount.account_number == account_number)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_account_by_id_for_update(
        self, session: AsyncSession, account_id: uuid.UUID
    ) -> Optional[TigerAccount]:
        """Get account by ID for update within a session."""
        stmt = (
            select(TigerAccount)
            .options(selectinload(TigerAccount.api_keys))
            .where(TigerAccount.id == account_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _clear_default_trading_account(
        self, session: AsyncSession, exclude_id: Optional[uuid.UUID] = None
    ) -> None:
        """Clear the current default trading account."""
        stmt = (
            update(TigerAccount)
            .where(TigerAccount.is_default_trading == True)
            .values(is_default_trading=False)
        )
        if exclude_id:
            stmt = stmt.where(TigerAccount.id != exclude_id)

        await session.execute(stmt)

    async def _clear_default_data_account(
        self, session: AsyncSession, exclude_id: Optional[uuid.UUID] = None
    ) -> None:
        """Clear the current default data account."""
        stmt = (
            update(TigerAccount)
            .where(TigerAccount.is_default_data == True)
            .values(is_default_data=False)
        )
        if exclude_id:
            stmt = stmt.where(TigerAccount.id != exclude_id)

        await session.execute(stmt)


# Global account manager instance
_account_manager: Optional[TigerAccountManager] = None


def get_account_manager() -> TigerAccountManager:
    """Get global account manager instance."""
    global _account_manager
    if _account_manager is None:
        _account_manager = TigerAccountManager()
    return _account_manager
