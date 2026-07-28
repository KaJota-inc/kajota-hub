from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Dialect(str, Enum):
    CORE = "core"
    FINACLE = "finacle"
    FLEXCUBE = "flexcube"
    GTB = "gtb"
    POSTILION = "postilion"
    UBN = "ubn"


class Category(str, Enum):
    SUCCESS = "success"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    INVALID_ACCOUNT = "invalid_account"
    DORMANT_ACCOUNT = "dormant_account"
    CLOSED_ACCOUNT = "closed_account"
    BLOCKED_ACCOUNT = "blocked_account"
    LIMIT_EXCEEDED = "limit_exceeded"
    INVALID_AMOUNT = "invalid_amount"
    DUPLICATE = "duplicate"
    DUPLICATE_ACCOUNT = "duplicate_account"
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    SYSTEM_MALFUNCTION = "system_malfunction"
    FORMAT_ERROR = "format_error"
    NOT_PERMITTED = "not_permitted"
    AUTHENTICATION_ERROR = "authentication_error"
    ENCRYPTION_ERROR = "encryption_error"
    SECURITY_VIOLATION = "security_violation"
    FRAUD_SUSPECTED = "fraud_suspected"
    CARD_ISSUE = "card_issue"
    UNKNOWN_BANK = "unknown_bank"
    UNKNOWN = "unknown"


class Retryability(str, Enum):
    IMMEDIATE = "immediate"
    BACKOFF = "backoff"
    STATUS_QUERY = "status_query"
    REVERSAL = "reversal"
    NEVER = "never"


class ResponseCode(BaseModel):
    dialect: Dialect
    code: str
    raw_message: str = Field(..., description="Verbatim from source .properties file")
    category: Category
    retry: Retryability
    customer_message: str
    ops_action: str


class Envelope(BaseModel):
    source: str = Field(..., description="Where this envelope came from: soap | json | audit_trail")
    transaction_id: Optional[str] = None
    session_id: Optional[str] = None
    method: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    source_account: Optional[str] = None
    source_bank_code: Optional[str] = None
    dest_account: Optional[str] = None
    dest_bank_code: Optional[str] = None
    narration: Optional[str] = None
    request_timestamp: Optional[datetime] = None
    response_timestamp: Optional[datetime] = None
    response_code: Optional[str] = None
    response_message: Optional[str] = None
    dialect: Optional[Dialect] = None
    raw_request: Optional[str] = None
    raw_response: Optional[str] = None


class TriageResult(BaseModel):
    """Deterministic triage output. The LLM layer sits on top of this."""
    envelope: Envelope
    matched_code: Optional[ResponseCode] = None
    cause: str
    action: str
    evidence: list[str] = Field(default_factory=list)
    retryable: bool
    retry_strategy: Retryability
    confidence: Literal["high", "medium", "low"] = "medium"
