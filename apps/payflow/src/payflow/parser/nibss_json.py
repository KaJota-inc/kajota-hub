import json

from payflow.models import Envelope

FIELD_ALIASES: dict[str, str] = {
    "sessionId": "session_id",
    "sessionID": "session_id",
    "session_id": "session_id",
    "SessionID": "session_id",
    "transactionId": "transaction_id",
    "transaction_id": "transaction_id",
    "paymentReference": "transaction_id",
    "PaymentReference": "transaction_id",
    "originatorAccountNumber": "source_account",
    "OriginatorAccountNumber": "source_account",
    "beneficiaryAccountNumber": "dest_account",
    "BeneficiaryAccountNumber": "dest_account",
    "destinationInstitutionCode": "dest_bank_code",
    "DestinationInstitutionCode": "dest_bank_code",
    "amount": "amount",
    "Amount": "amount",
    "narration": "narration",
    "narrationTruncated": "narration",
    "NarrationTruncated": "narration",
    "responseCode": "response_code",
    "ResponseCode": "response_code",
    "response_code": "response_code",
    "responseMessage": "response_message",
    "ResponseMessage": "response_message",
    "response_message": "response_message",
    "method": "method",
    "operation": "method",
}


def parse_json(text: str) -> Envelope:
    obj = json.loads(text)
    env = Envelope(source="json", raw_request=text)
    for k, v in obj.items():
        target = FIELD_ALIASES.get(k)
        if not target or v is None:
            continue
        if target == "amount":
            try:
                env.amount = float(v)
            except (TypeError, ValueError):
                pass
        else:
            setattr(env, target, str(v))
    return env
