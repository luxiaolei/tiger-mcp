"""
Database utility functions and common operations.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from sqlalchemy import and_, asc, desc, func, or_, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .base import BaseModel
from .models import APIKey, AuditLog, TigerAccount, TokenStatus
from .models.accounts import AccountStatus
from .models.api_keys import APIKeyScope, APIKeyStatus
from .models.audit_logs import AuditAction, AuditResult, AuditSeverity
from .models.token_status import RefreshTrigger, TokenRefreshStatus

T = TypeVar("T", bound=BaseModel)


class DatabaseUtils:
    """Utility class for common database operations."""

    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        self.session = session

    async def get_by_id(
        self,
        model_class: Type[T],
        obj_id: Union[str, uuid.UUID],
        load_relations: Optional[List[str]] = None,
    ) -> Optional[T]:
        """
        Get object by ID with optional relationship loading.

        Args:
            model_class: SQLAlchemy model class
            obj_id: Object ID (UUID or string)
            load_relations: List of relationship names to load

        Returns:
            Model instance or None if not found
        """
        query = select(model_class).where(model_class.id == obj_id)

        # Add relationship loading
        if load_relations:
            for relation in load_relations:
                query = query.options(selectinload(getattr(model_class, relation)))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_field(
        self,
        model_class: Type[T],
        field_name: str,
        field_value: Any,
        load_relations: Optional[List[str]] = None,
    ) -> Optional[T]:
        """
        Get object by field value.

        Args:
            model_class: SQLAlchemy model class
            field_name: Field name to search by
            field_value: Value to search for
            load_relations: List of relationship names to load

        Returns:
            Model instance or None if not found
        """
        field = getattr(model_class, field_name)
        query = select(model_class).where(field == field_value)

        # Add relationship loading
        if load_relations:
            for relation in load_relations:
                query = query.options(selectinload(getattr(model_class, relation)))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_with_pagination(
        self,
        model_class: Type[T],
        page: int = 1,
        page_size: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        load_relations: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        List objects with pagination and filtering.

        Args:
            model_class: SQLAlchemy model class
            page: Page number (1-based)
            page_size: Number of items per page
            filters: Dictionary of field filters
            order_by: Field name to order by
            order_desc: Whether to order descending
            load_relations: List of relationship names to load

        Returns:
            Dictionary with items, total count, and pagination info
        """
        query = select(model_class)

        # Apply filters
        if filters:
            for field_name, value in filters.items():
                field = getattr(model_class, field_name)
                if isinstance(value, list):
                    query = query.where(field.in_(value))
                else:
                    query = query.where(field == value)

        # Get total count
        count_query = select(func.count(model_class.id))
        if filters:
            for field_name, value in filters.items():
                field = getattr(model_class, field_name)
                if isinstance(value, list):
                    count_query = count_query.where(field.in_(value))
                else:
                    count_query = count_query.where(field == value)

        total_result = await self.session.execute(count_query)
        total_count = total_result.scalar()

        # Apply ordering
        if order_by:
            order_field = getattr(model_class, order_by)
            if order_desc:
                query = query.order_by(desc(order_field))
            else:
                query = query.order_by(asc(order_field))
        else:
            # Default order by created_at desc
            query = query.order_by(desc(model_class.created_at))

        # Add relationship loading
        if load_relations:
            for relation in load_relations:
                query = query.options(selectinload(getattr(model_class, relation)))

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        items = result.scalars().all()

        # Calculate pagination info
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1

        return {
            "items": items,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev,
        }

    async def create(self, model_class: Type[T], **kwargs) -> T:
        """
        Create new object.

        Args:
            model_class: SQLAlchemy model class
            **kwargs: Field values

        Returns:
            Created model instance
        """
        obj = model_class(**kwargs)
        self.session.add(obj)
        await self.session.flush()  # Get ID without committing
        return obj

    async def update(self, obj: BaseModel, **kwargs) -> BaseModel:
        """
        Update object with new values.

        Args:
            obj: Model instance to update
            **kwargs: Field values to update

        Returns:
            Updated model instance
        """
        for key, value in kwargs.items():
            if hasattr(obj, key):
                setattr(obj, key, value)

        await self.session.flush()
        return obj

    async def delete(self, obj: BaseModel) -> None:
        """
        Delete object.

        Args:
            obj: Model instance to delete
        """
        await self.session.delete(obj)
        await self.session.flush()


class TigerAccountUtils(DatabaseUtils):
    """Utility functions for Tiger account operations."""

    async def get_default_trading_account(self) -> Optional[TigerAccount]:
        """Get the default trading account."""
        return await self.get_by_field(
            TigerAccount, "is_default_trading", True, load_relations=["api_keys"]
        )

    async def get_default_data_account(self) -> Optional[TigerAccount]:
        """Get the default data account."""
        return await self.get_by_field(
            TigerAccount, "is_default_data", True, load_relations=["api_keys"]
        )

    async def get_by_account_number(
        self, account_number: str
    ) -> Optional[TigerAccount]:
        """Get account by Tiger account number."""
        return await self.get_by_field(
            TigerAccount,
            "account_number",
            account_number,
            load_relations=["api_keys", "token_statuses"],
        )

    async def get_active_accounts(self) -> List[TigerAccount]:
        """Get all active accounts."""
        query = (
            select(TigerAccount)
            .where(TigerAccount.status == AccountStatus.ACTIVE)
            .options(selectinload(TigerAccount.api_keys))
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_accounts_needing_token_refresh(self) -> List[TigerAccount]:
        """Get accounts that need token refresh."""
        now = datetime.utcnow()
        query = select(TigerAccount).where(
            and_(
                TigerAccount.status == AccountStatus.ACTIVE,
                or_(
                    TigerAccount.token_expires_at.is_(None),
                    TigerAccount.token_expires_at <= now,
                ),
            )
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def set_default_trading_account(self, account_id: uuid.UUID) -> TigerAccount:
        """Set account as default for trading."""
        # Clear existing default
        await self.session.execute(
            select(TigerAccount)
            .where(TigerAccount.is_default_trading == True)
            .update({TigerAccount.is_default_trading: False})
        )

        # Set new default
        account = await self.get_by_id(TigerAccount, account_id)
        if not account:
            raise NoResultFound(f"Account {account_id} not found")

        account.is_default_trading = True
        await self.session.flush()
        return account

    async def set_default_data_account(self, account_id: uuid.UUID) -> TigerAccount:
        """Set account as default for data fetching."""
        # Clear existing default
        await self.session.execute(
            select(TigerAccount)
            .where(TigerAccount.is_default_data == True)
            .update({TigerAccount.is_default_data: False})
        )

        # Set new default
        account = await self.get_by_id(TigerAccount, account_id)
        if not account:
            raise NoResultFound(f"Account {account_id} not found")

        account.is_default_data = True
        await self.session.flush()
        return account


class APIKeyUtils(DatabaseUtils):
    """Utility functions for API key operations."""

    @staticmethod
    def generate_api_key() -> str:
        """Generate a new API key."""
        return f"tmcp_{secrets.token_urlsafe(32)}"

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash API key for storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()

    @staticmethod
    def get_key_prefix(api_key: str) -> str:
        """Get the first 8 characters for identification."""
        return api_key[:8]

    async def get_by_hash(self, key_hash: str) -> Optional[APIKey]:
        """Get API key by hash."""
        return await self.get_by_field(
            APIKey, "key_hash", key_hash, load_relations=["tiger_account"]
        )

    async def get_active_keys(self) -> List[APIKey]:
        """Get all active API keys."""
        now = datetime.utcnow()
        query = (
            select(APIKey)
            .where(
                and_(
                    APIKey.status == APIKeyStatus.ACTIVE,
                    or_(APIKey.expires_at.is_(None), APIKey.expires_at > now),
                )
            )
            .options(selectinload(APIKey.tiger_account))
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_keys_for_account(self, account_id: uuid.UUID) -> List[APIKey]:
        """Get all keys for a specific account."""
        query = (
            select(APIKey)
            .where(APIKey.tiger_account_id == account_id)
            .options(selectinload(APIKey.tiger_account))
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_api_key(
        self,
        name: str,
        scopes: List[APIKeyScope],
        tiger_account_id: Optional[uuid.UUID] = None,
        expires_at: Optional[datetime] = None,
        **kwargs,
    ) -> tuple[APIKey, str]:
        """
        Create new API key.

        Returns:
            Tuple of (APIKey object, raw API key string)
        """
        # Generate key
        raw_key = self.generate_api_key()
        key_hash = self.hash_api_key(raw_key)
        key_prefix = self.get_key_prefix(raw_key)

        # Create API key object
        api_key = await self.create(
            APIKey,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=[scope.value for scope in scopes],
            tiger_account_id=tiger_account_id,
            expires_at=expires_at,
            **kwargs,
        )

        return api_key, raw_key

    async def verify_api_key(self, raw_key: str) -> Optional[APIKey]:
        """
        Verify API key and return the key object if valid.

        Args:
            raw_key: The raw API key string

        Returns:
            APIKey object if valid, None otherwise
        """
        key_hash = self.hash_api_key(raw_key)
        api_key = await self.get_by_hash(key_hash)

        if not api_key or not api_key.is_active:
            return None

        # Record usage
        api_key.record_usage()
        await self.session.flush()

        return api_key


class AuditLogUtils(DatabaseUtils):
    """Utility functions for audit log operations."""

    async def log_event(
        self,
        action: AuditAction,
        result: AuditResult = AuditResult.SUCCESS,
        severity: AuditSeverity = AuditSeverity.LOW,
        tiger_account_id: Optional[uuid.UUID] = None,
        api_key_id: Optional[uuid.UUID] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict] = None,
        **kwargs,
    ) -> AuditLog:
        """
        Log an audit event.

        Args:
            action: Type of action performed
            result: Result of the action
            severity: Severity level
            tiger_account_id: Related Tiger account ID
            api_key_id: Related API key ID
            user_id: User who performed the action
            ip_address: IP address of the request
            details: Additional event details
            **kwargs: Additional fields

        Returns:
            Created AuditLog object
        """
        return await self.create(
            AuditLog,
            action=action,
            result=result,
            severity=severity,
            tiger_account_id=tiger_account_id,
            api_key_id=api_key_id,
            user_id=user_id,
            ip_address=ip_address,
            details=details or {},
            **kwargs,
        )

    async def get_recent_events(
        self,
        limit: int = 50,
        severity: Optional[AuditSeverity] = None,
        tiger_account_id: Optional[uuid.UUID] = None,
        actions: Optional[List[AuditAction]] = None,
    ) -> List[AuditLog]:
        """Get recent audit events with optional filtering."""
        query = select(AuditLog).order_by(desc(AuditLog.created_at))

        if severity:
            query = query.where(AuditLog.severity == severity)

        if tiger_account_id:
            query = query.where(AuditLog.tiger_account_id == tiger_account_id)

        if actions:
            query = query.where(AuditLog.action.in_(actions))

        query = query.limit(limit)
        query = query.options(
            selectinload(AuditLog.tiger_account), selectinload(AuditLog.api_key)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_security_events(self, hours: int = 24) -> List[AuditLog]:
        """Get security-related events from the last N hours."""
        security_actions = [
            AuditAction.SECURITY_AUTH_FAIL,
            AuditAction.SECURITY_ACCESS_DENIED,
            AuditAction.SECURITY_BREACH_DETECTED,
            AuditAction.API_KEY_CREATE,
            AuditAction.API_KEY_REVOKE,
            AuditAction.ACCOUNT_LOGIN,
        ]

        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        query = (
            select(AuditLog)
            .where(
                and_(
                    AuditLog.action.in_(security_actions), AuditLog.created_at >= since
                )
            )
            .order_by(desc(AuditLog.created_at))
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())


class TokenStatusUtils(DatabaseUtils):
    """Utility functions for token status operations."""

    async def get_latest_status(
        self, tiger_account_id: uuid.UUID
    ) -> Optional[TokenStatus]:
        """Get the latest token status for an account."""
        query = (
            select(TokenStatus)
            .where(TokenStatus.tiger_account_id == tiger_account_id)
            .order_by(desc(TokenStatus.created_at))
            .limit(1)
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_pending_refreshes(self) -> List[TokenStatus]:
        """Get all pending token refresh operations."""
        query = (
            select(TokenStatus)
            .where(TokenStatus.status == TokenRefreshStatus.PENDING)
            .options(selectinload(TokenStatus.tiger_account))
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_failed_refreshes(
        self, tiger_account_id: Optional[uuid.UUID] = None, hours: int = 24
    ) -> List[TokenStatus]:
        """Get failed refresh operations."""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        query = select(TokenStatus).where(
            and_(
                TokenStatus.status == TokenRefreshStatus.FAILED,
                TokenStatus.created_at >= since,
            )
        )

        if tiger_account_id:
            query = query.where(TokenStatus.tiger_account_id == tiger_account_id)

        query = query.order_by(desc(TokenStatus.created_at))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_refresh_operation(
        self,
        tiger_account_id: uuid.UUID,
        trigger: RefreshTrigger,
        current_token_expires_at: Optional[datetime] = None,
        current_token_hash: Optional[str] = None,
    ) -> TokenStatus:
        """Create a new token refresh operation."""
        return await self.create(
            TokenStatus,
            tiger_account_id=tiger_account_id,
            trigger=trigger,
            old_token_expires_at=current_token_expires_at,
            old_token_hash=current_token_hash,
        )


# Convenience function to create utils instance
def create_utils(session: AsyncSession) -> Dict[str, DatabaseUtils]:
    """Create utility instances for a database session."""
    return {
        "base": DatabaseUtils(session),
        "accounts": TigerAccountUtils(session),
        "api_keys": APIKeyUtils(session),
        "audit_logs": AuditLogUtils(session),
        "token_status": TokenStatusUtils(session),
    }
