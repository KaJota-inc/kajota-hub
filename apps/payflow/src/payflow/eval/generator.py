import json
import random

from payflow.eval.fixture import Fixture, FixtureKind
from payflow.kb import KB, load_kb
from payflow.models import Category, Dialect, ResponseCode, Retryability

# Bank codes drawn from real NIBSS institution codes so envelopes look believable.
BANK_CODES = ["000014", "000013", "000016", "000015", "000012", "000023", "000033", "000058"]
CURRENCIES = ["NGN"]
METHODS = ["FundsTransfer", "NameEnquiry", "BalanceEnquiry"]

# Message-pattern → correct verdict. Used to mint out_of_kb fixtures whose message
# hints at the right category even though the code is not in the KB.
MESSAGE_HINT_TO_VERDICT: list[tuple[str, Retryability, Category, bool]] = [
    ("Insufficient Funds", Retryability.NEVER, Category.INSUFFICIENT_FUNDS, False),
    ("Not Sufficient Funds", Retryability.NEVER, Category.INSUFFICIENT_FUNDS, False),
    ("Invalid Account", Retryability.NEVER, Category.INVALID_ACCOUNT, False),
    ("Account Closed", Retryability.NEVER, Category.CLOSED_ACCOUNT, False),
    ("Dormant Account", Retryability.NEVER, Category.DORMANT_ACCOUNT, False),
    ("Response Timeout", Retryability.STATUS_QUERY, Category.TIMEOUT, True),
    ("Connection Timeout", Retryability.STATUS_QUERY, Category.TIMEOUT, True),
    ("Bank Offline", Retryability.STATUS_QUERY, Category.CONNECTION_ERROR, True),
    ("System Malfunction", Retryability.BACKOFF, Category.SYSTEM_MALFUNCTION, True),
    ("Duplicate Transaction", Retryability.STATUS_QUERY, Category.DUPLICATE, True),
    ("Withdrawal Limit Exceeded", Retryability.NEVER, Category.LIMIT_EXCEEDED, False),
]

# Adversarial: contradictory or ambiguous. Verifier should force status_query.
ADVERSARIAL_PATTERNS: list[tuple[str, str]] = [
    ("Successful", "Failed"),
    ("Transaction posted successfully", "Please retry"),
    ("Unknown status", ""),
    ("Operation completed", "Reversal required"),
    ("", "Processing"),
    ("Undefined error", "Contact support"),
    ("System says OK but ledger says otherwise", ""),
]


def _mint_session_id(rng: random.Random) -> str:
    return f"099999{rng.randint(10**24, 10**25 - 1)}"


def _mint_reference(rng: random.Random, prefix: str = "PAY") -> str:
    return f"{prefix}-{rng.randint(10**10, 10**11 - 1)}"


def _mint_account(rng: random.Random) -> str:
    return str(rng.randint(1_000_000_000, 9_999_999_999))


def _mint_soap_envelope(
    rng: random.Random,
    method: str,
    response_code: str,
    response_message: str,
    dest_bank_code: str | None = None,
) -> str:
    session_id = _mint_session_id(rng)
    reference = _mint_reference(rng)
    dest_account = _mint_account(rng)
    orig_account = _mint_account(rng)
    amount = round(rng.uniform(500, 500_000), 2)
    dest_bank_code = dest_bank_code or rng.choice(BANK_CODES)

    return f"""<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ns:{method}Response xmlns:ns="http://nibss.com/nip/">
      <SessionID>{session_id}</SessionID>
      <PaymentReference>{reference}</PaymentReference>
      <DestinationInstitutionCode>{dest_bank_code}</DestinationInstitutionCode>
      <BeneficiaryAccountNumber>{dest_account}</BeneficiaryAccountNumber>
      <OriginatorAccountNumber>{orig_account}</OriginatorAccountNumber>
      <Amount>{amount}</Amount>
      <NarrationTruncated>Payflow synthetic fixture</NarrationTruncated>
      <ResponseCode>{response_code}</ResponseCode>
      <ResponseMessage>{response_message}</ResponseMessage>
    </ns:{method}Response>
  </soap:Body>
</soap:Envelope>
"""


def _mint_json_envelope(
    rng: random.Random,
    method: str,
    response_code: str,
    response_message: str,
) -> str:
    payload = {
        "sessionId": _mint_session_id(rng),
        "paymentReference": _mint_reference(rng),
        "method": method,
        "originatorAccountNumber": _mint_account(rng),
        "beneficiaryAccountNumber": _mint_account(rng),
        "destinationInstitutionCode": rng.choice(BANK_CODES),
        "amount": round(rng.uniform(500, 500_000), 2),
        "narration": "Payflow synthetic fixture",
        "responseCode": response_code,
        "responseMessage": response_message,
    }
    return json.dumps(payload, indent=2)


def _mint_audit_trail(
    rng: random.Random,
    method: str,
    response_code: str,
    response_message: str,
) -> str:
    raw_request = _mint_soap_envelope(rng, method, response_code, response_message).replace(
        f"{method}Response", f"{method}Request"
    )
    raw_response = _mint_soap_envelope(rng, method, response_code, response_message)
    row = {
        "id": rng.randint(1, 10**9),
        "method": method,
        "raw_request": raw_request,
        "raw_response": raw_response,
        "request_ip": f"10.0.{rng.randint(0, 255)}.{rng.randint(1, 255)}",
    }
    return json.dumps(row, indent=2)


def generate_in_kb_fixtures(kb: KB, per_code_variants: int = 3, seed: int = 42) -> list[Fixture]:
    """One fixture per (code, format) triple: exercise every KB entry across all envelope formats."""
    rng = random.Random(seed)
    formats = ["soap", "json", "audit_trail"]
    out: list[Fixture] = []
    for (dialect, code), entry in sorted(kb.items()):
        for i in range(per_code_variants):
            fmt = formats[i % len(formats)]
            method = rng.choice(METHODS)
            content = _render(rng, fmt, method, entry)
            out.append(Fixture(
                id=f"in_kb-{dialect.value}-{code}-{fmt}-{i}",
                kind=FixtureKind.IN_KB,
                envelope_format=fmt,
                envelope_content=content,
                dialect=dialect,
                expected_retry_strategy=entry.retry,
                expected_category=entry.category,
                expected_retryable=entry.retry != Retryability.NEVER,
                expected_confidence_min="high",
                is_labelled=True,
                source_code=code,
                notes=f"Seeded from KB entry ({dialect.value},{code}) → {entry.raw_message}",
            ))
    return out


def _render(rng: random.Random, fmt: str, method: str, entry: ResponseCode) -> str:
    if fmt == "soap":
        return _mint_soap_envelope(rng, method, entry.code, entry.raw_message)
    if fmt == "json":
        return _mint_json_envelope(rng, method, entry.code, entry.raw_message)
    return _mint_audit_trail(rng, method, entry.code, entry.raw_message)


def _unused_code(rng: random.Random, kb: KB, dialect: Dialect) -> str:
    """Pick a 4-digit code not present in the KB under this dialect."""
    used = {c for (d, c) in kb.keys() if d == dialect}
    for _ in range(200):
        candidate = str(rng.randint(1000, 9999))
        if candidate not in used:
            return candidate
    return "ZZ99"  # very-unlikely-collision fallback


def generate_out_of_kb_fixtures(kb: KB, count: int = 20, seed: int = 43) -> list[Fixture]:
    """Codes not in KB, but message hint suffices for correct verdict — LLM triager territory."""
    rng = random.Random(seed)
    out: list[Fixture] = []
    for i in range(count):
        message_pattern, retry, category, retryable = rng.choice(MESSAGE_HINT_TO_VERDICT)
        dialect = rng.choice(list(Dialect))
        code = _unused_code(rng, kb, dialect)
        fmt = rng.choice(["soap", "json"])
        method = rng.choice(METHODS)
        content = (
            _mint_soap_envelope(rng, method, code, message_pattern)
            if fmt == "soap"
            else _mint_json_envelope(rng, method, code, message_pattern)
        )
        out.append(Fixture(
            id=f"out_of_kb-{i:03d}-{dialect.value}-{code}",
            kind=FixtureKind.OUT_OF_KB,
            envelope_format=fmt,
            envelope_content=content,
            dialect=dialect,
            expected_retry_strategy=retry,
            expected_category=category,
            expected_retryable=retryable,
            expected_confidence_min="medium",
            is_labelled=True,
            source_code=code,
            notes=f"Unknown code {code} in {dialect.value}; message hint {message_pattern!r}",
        ))
    return out


def generate_adversarial_fixtures(kb: KB, count: int = 10, seed: int = 44) -> list[Fixture]:
    """Ambiguous/contradictory message-code pairs. Verifier must force status_query."""
    rng = random.Random(seed)
    out: list[Fixture] = []
    for i in range(count):
        message, extra = rng.choice(ADVERSARIAL_PATTERNS)
        dialect = rng.choice(list(Dialect))
        code = _unused_code(rng, kb, dialect)
        fmt = rng.choice(["soap", "json"])
        method = rng.choice(METHODS)
        full_message = f"{message} {extra}".strip()
        content = (
            _mint_soap_envelope(rng, method, code, full_message)
            if fmt == "soap"
            else _mint_json_envelope(rng, method, code, full_message)
        )
        out.append(Fixture(
            id=f"adversarial-{i:03d}-{dialect.value}-{code}",
            kind=FixtureKind.ADVERSARIAL,
            envelope_format=fmt,
            envelope_content=content,
            dialect=dialect,
            expected_retry_strategy=Retryability.STATUS_QUERY,
            expected_category=Category.UNKNOWN,
            expected_retryable=True,
            expected_confidence_min="low",
            is_labelled=True,
            source_code=code,
            notes=f"Ambiguous — safe fallback expected. Message: {full_message!r}",
        ))
    return out


def generate_malformed_fixtures(count: int = 5, seed: int = 45) -> list[Fixture]:
    """Missing response code or missing dialect. Expected: low-confidence deterministic result."""
    rng = random.Random(seed)
    out: list[Fixture] = []
    for i in range(count):
        method = rng.choice(METHODS)
        session_id = _mint_session_id(rng)
        content = f"""<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ns:{method}Response xmlns:ns="http://nibss.com/nip/">
      <SessionID>{session_id}</SessionID>
    </ns:{method}Response>
  </soap:Body>
</soap:Envelope>
"""
        out.append(Fixture(
            id=f"malformed-{i:03d}",
            kind=FixtureKind.MALFORMED,
            envelope_format="soap",
            envelope_content=content,
            dialect=None,
            expected_retry_strategy=Retryability.NEVER,
            expected_category=None,
            expected_retryable=False,
            expected_confidence_min="low",
            is_labelled=True,
            source_code=None,
            notes="Missing response code and dialect — deterministic must return low-confidence.",
        ))
    return out


def generate_all(
    kb: KB | None = None,
    per_code_variants: int = 3,
    out_of_kb_count: int = 20,
    adversarial_count: int = 10,
    malformed_count: int = 5,
    seed: int = 42,
) -> list[Fixture]:
    kb = kb or load_kb()
    fixtures: list[Fixture] = []
    fixtures.extend(generate_in_kb_fixtures(kb, per_code_variants, seed))
    fixtures.extend(generate_out_of_kb_fixtures(kb, out_of_kb_count, seed + 1))
    fixtures.extend(generate_adversarial_fixtures(kb, adversarial_count, seed + 2))
    fixtures.extend(generate_malformed_fixtures(malformed_count, seed + 3))
    return fixtures
