import time
from enum import Enum
from typing import Optional

from payflow.eval.fixture import Fixture, Prediction
from payflow.kb import KB, load_kb
from payflow.models import Envelope, Retryability
from payflow.parser import parse_audit_trail_json, parse_json, parse_soap
from payflow.triage import triage
from payflow.triage.llm import TriagerProtocol
from payflow.triage.verifier import VerifierProtocol


class EvalMode(str, Enum):
    KB_ONLY = "kb_only"
    WITH_LLM = "with_llm"
    WITH_VERIFIER = "with_verifier"


_PARSERS = {
    "soap": parse_soap,
    "json": parse_json,
    "audit_trail": parse_audit_trail_json,
}


def _parse_fixture(fx: Fixture) -> Envelope:
    parser = _PARSERS.get(fx.envelope_format)
    if parser is None:
        raise ValueError(f"Unknown envelope_format: {fx.envelope_format}")
    env = parser(fx.envelope_content)
    env.dialect = fx.dialect
    return env


def run_eval(
    fixtures: list[Fixture],
    mode: EvalMode,
    kb: Optional[KB] = None,
    llm_triager: Optional[TriagerProtocol] = None,
    llm_verifier: Optional[VerifierProtocol] = None,
) -> list[Prediction]:
    kb = kb or load_kb()
    use_llm = mode in (EvalMode.WITH_LLM, EvalMode.WITH_VERIFIER)
    verify = mode == EvalMode.WITH_VERIFIER

    predictions: list[Prediction] = []
    for fx in fixtures:
        started = time.perf_counter()
        try:
            env = _parse_fixture(fx)
            result = triage(
                env,
                kb,
                use_llm=use_llm,
                verify=verify,
                llm_triager=llm_triager,
                llm_verifier=llm_verifier,
            )
            predictions.append(Prediction(
                fixture_id=fx.id,
                mode=mode.value,
                predicted_retry_strategy=result.retry_strategy,
                predicted_retryable=result.retryable,
                predicted_confidence=result.confidence,
                matched_kb=result.matched_code is not None,
                duration_ms=(time.perf_counter() - started) * 1000,
            ))
        except Exception as e:  # noqa: BLE001
            predictions.append(Prediction(
                fixture_id=fx.id,
                mode=mode.value,
                predicted_retry_strategy=Retryability.NEVER,
                predicted_retryable=False,
                predicted_confidence="low",
                matched_kb=False,
                duration_ms=(time.perf_counter() - started) * 1000,
                error=repr(e),
            ))
    return predictions
