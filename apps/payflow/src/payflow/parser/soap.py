import xml.etree.ElementTree as ET
from typing import Optional

from payflow.models import Envelope

_SOAP_FRAME = {"Envelope", "Body", "Header", "Fault"}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(root: ET.Element, name: str) -> Optional[str]:
    for child in root.iter():
        if _local(child.tag) == name and child.text is not None:
            return child.text.strip() or None
    return None


def _detect_method(root: ET.Element) -> Optional[str]:
    for child in root.iter():
        name = _local(child.tag)
        if name in _SOAP_FRAME:
            continue
        for suffix in ("Request", "Response"):
            if name.endswith(suffix) and name != suffix:
                return name[: -len(suffix)]
    return None


def parse_soap(text: str) -> Envelope:
    """Parse a SOAP NIP envelope (request, response, or one that wraps both).

    Uses local-name matching so the parser is namespace-agnostic — different
    integrators use different NS URIs for the same NIBSS payload.
    """
    root = ET.fromstring(text)
    env = Envelope(source="soap", raw_request=text)
    env.method = _detect_method(root)
    env.session_id = _text(root, "SessionID") or _text(root, "sessionID")
    env.transaction_id = _text(root, "PaymentReference") or _text(root, "TransactionReference")
    env.source_account = _text(root, "OriginatorAccountNumber")
    env.dest_account = _text(root, "BeneficiaryAccountNumber")
    env.dest_bank_code = _text(root, "DestinationInstitutionCode")

    amount_str = _text(root, "Amount")
    if amount_str:
        try:
            env.amount = float(amount_str)
        except ValueError:
            pass

    env.narration = _text(root, "NarrationTruncated") or _text(root, "Narration")
    env.response_code = _text(root, "ResponseCode")
    env.response_message = _text(root, "ResponseMessage")
    return env
