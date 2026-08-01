// Client-side port of kajota-coach's coach_auditor.py.
//
// Kept intentionally in lockstep with the Python module so a judge who
// clones kajota-coach and runs pytest sees the SAME 19 tests pass
// against the same rule set that fires here in the browser. Reason to
// ship this in the browser at all: judges paste any KH workflow, see
// the audit render instantly, no roundtrip. If a downstream builder
// wants the same rules over an HTTP surface, POST /coach/audit-workflow
// on kajota-coach returns the same shape.

const SEV_ERROR = "error";
const SEV_WARN = "warn";
const SEV_INFO = "info";

const REJECTED_FUNCTION_ALIASES = new Set(["function", "method", "contract"]);
const LEGACY_FUNCTION_ALIASES = new Set(["functionName"]);
const SILENTLY_IGNORED_ROUTING_KEYS = new Set(["integrationId"]);
const CANONICAL_ROUTING_KEY = "web3Connection";
const CANONICAL_ROUTING_VALUES = new Set(["default", "eoa"]);
const WRITE_CONTRACT_ACTION = "web3/write-contract";

const STORED_TEMPLATE_RE = /\{\{\s*@([a-zA-Z0-9_-]+):([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\s*\}\}/g;
const BROKEN_TEMPLATE_RE = /\{\{\s*@trigger\.body\.([A-Za-z0-9_]+)\s*\}\}/g;

const isJsonEncodedString = (v) => {
  if (typeof v !== "string") return false;
  try { JSON.parse(v); return true; } catch { return false; }
};

const iterActionNodes = (workflow) => {
  const out = [];
  const nodes = workflow?.nodes || [];
  nodes.forEach((node, i) => {
    if (!node || typeof node !== "object") return;
    const outer = node.type || "";
    const data = node.data || {};
    const config = data.config || {};
    const actionType = config.actionType || "";
    const isAction = outer === "action" || outer.includes("/");
    const looksWriteContract = actionType === WRITE_CONTRACT_ACTION || outer === WRITE_CONTRACT_ACTION;
    if (isAction && looksWriteContract) out.push([`nodes[${i}]`, node]);
  });
  return out;
};

const issue = (trap, severity, path, detail, fix) => ({ trap, severity, path, detail, fix });

const checkFunctionKey = (path, config) => {
  const out = [];
  const hasCanonical = "abiFunction" in config;
  for (const alias of LEGACY_FUNCTION_ALIASES) {
    if (alias in config && !hasCanonical) {
      out.push(issue(
        "legacy-function-alias", SEV_WARN,
        `${path}.data.config.${alias}`,
        `\`${alias}\` is an accepted legacy alias for \`abiFunction\`, but the canonical field is \`abiFunction\`. New code should use the canonical form.`,
        `rename "${alias}" to "abiFunction"`,
      ));
    }
  }
  for (const bad of REJECTED_FUNCTION_ALIASES) {
    if (bad in config) {
      out.push(issue(
        "rejected-function-alias", SEV_ERROR,
        `${path}.data.config.${bad}`,
        `\`${bad}\` is rejected by the strict-mode validator as UNKNOWN_FIELD. Use \`abiFunction\`.`,
        `rename "${bad}" to "abiFunction"`,
      ));
    }
  }
  if (!hasCanonical && ![...LEGACY_FUNCTION_ALIASES].some(a => a in config)) {
    out.push(issue(
      "missing-abi-function", SEV_ERROR,
      `${path}.data.config`,
      "write-contract step is missing `abiFunction` (the function name to call).",
      'add `"abiFunction": "<yourFunctionName>"`',
    ));
  }
  return out;
};

const checkFunctionArgs = (path, config) => {
  if (!("functionArgs" in config)) return [];
  const args = config.functionArgs;
  if (Array.isArray(args)) {
    return [issue(
      "function-args-raw-array", SEV_ERROR,
      `${path}.data.config.functionArgs`,
      "`functionArgs` is a raw array. The API accepts it, but the runtime throws `Invalid function arguments JSON` at execute time — this fails silently until you fire the workflow.",
      `wrap in a JSON-encoded string, e.g. ${JSON.stringify(JSON.stringify(args))}`,
    )];
  }
  if (!isJsonEncodedString(args)) {
    return [issue(
      "function-args-not-json-string", SEV_ERROR,
      `${path}.data.config.functionArgs`,
      '`functionArgs` must be a JSON-encoded array string like `"[\\"0xabc…\\"]"`.',
      'wrap the arguments as JSON: JSON.stringify(["…", "…"])',
    )];
  }
  return [];
};

const checkAbi = (path, config) => {
  if (!("abi" in config)) return [];
  const abi = config.abi;
  if (Array.isArray(abi)) {
    return [issue(
      "abi-raw-array", SEV_ERROR,
      `${path}.data.config.abi`,
      "`abi` is a raw array. Like `functionArgs`, it must be JSON-encoded to a string.",
      "wrap as JSON: JSON.stringify(abiFragment)",
    )];
  }
  if (!isJsonEncodedString(abi)) {
    return [issue(
      "abi-not-json-string", SEV_ERROR,
      `${path}.data.config.abi`,
      "`abi` must be a JSON-encoded array string.",
      "wrap as JSON: JSON.stringify(abiFragment)",
    )];
  }
  return [];
};

const checkWeb3Connection = (path, config) => {
  const out = [];
  for (const silent of SILENTLY_IGNORED_ROUTING_KEYS) {
    if (silent in config) {
      out.push(issue(
        "silently-ignored-integration-id", SEV_ERROR,
        `${path}.data.config.${silent}`,
        `\`${silent}\` is a reserved config key that the validator accepts but the write-contract action ignores. The signing wallet is routed by \`web3Connection\` instead.`,
        `replace \`"${silent}": "…"\` with \`"web3Connection": "default"\` (or "eoa" / "safe:<id>")`,
      ));
    }
  }
  if (CANONICAL_ROUTING_KEY in config) {
    const val = config[CANONICAL_ROUTING_KEY];
    const ok = typeof val === "string"
      && (CANONICAL_ROUTING_VALUES.has(val) || val.startsWith("safe:"));
    if (!ok) {
      out.push(issue(
        "invalid-web3-connection-value", SEV_ERROR,
        `${path}.data.config.${CANONICAL_ROUTING_KEY}`,
        '`web3Connection` must be one of `"default"`, `"eoa"`, or `"safe:<safeWalletId>"`.',
        'set to "default" (org policy) unless you need EOA or a specific Safe',
      ));
    }
  }
  return out;
};

const checkNetwork = (path, config) => {
  if (!("network" in config)) return [];
  const net = config.network;
  if (typeof net === "number") {
    return [issue(
      "network-numeric-not-string", SEV_WARN,
      `${path}.data.config.network`,
      "`network` is a JSON number; KH expects a numeric chain id as a STRING (e.g. `\"11155111\"`).",
      `wrap as a string: "${net}"`,
    )];
  }
  return [];
};

const checkTemplates = (path, config) => {
  const out = [];
  for (const [key, value] of Object.entries(config)) {
    if (typeof value !== "string") continue;
    // reset regex state — global flag
    BROKEN_TEMPLATE_RE.lastIndex = 0;
    let m;
    while ((m = BROKEN_TEMPLATE_RE.exec(value)) !== null) {
      const fieldName = m[1];
      out.push(issue(
        "broken-trigger-template", SEV_ERROR,
        `${path}.data.config.${key}`,
        `\`{{@trigger.body.${fieldName}}}\` is the intuitive template pattern but resolves to an empty string in stored workflows. HTTP triggers use the slot-scoped syntax \`{{@<nodeId>:HTTP.${fieldName}}}\`.`,
        `replace \`{{@trigger.body.${fieldName}}}\` with \`{{@trigger-1:HTTP.${fieldName}}}\` (match the HTTP trigger node id)`,
      ));
    }
  }
  return out;
};

const checkHttpTriggerBodyWrap = (workflow) => {
  for (const node of workflow?.nodes || []) {
    if (!node || typeof node !== "object") continue;
    const data = node.data || {};
    const cfg = data.config || {};
    const triggerType = cfg.triggerType || "";
    const outer = node.type || "";
    if (triggerType === "HTTP" || (outer === "trigger" && data.label === "HTTP")) {
      return [issue(
        "http-body-wrap-reminder", SEV_INFO,
        "request body",
        'HTTP triggers spread top-level fields of the request body into the trigger output — but ONLY when the body is wrapped under `input`. POST `{"input": {"depositId": "0x…"}}`, not `{"depositId": "0x…"}`.',
        "wrap the POST body under `input`",
      )];
    }
  }
  return [];
};

const summarise = (passed, actionCount, errs, warns) => {
  if (actionCount === 0) {
    return "No `web3/write-contract` action nodes in this workflow — nothing to audit. The auditor only checks the write-contract action's field-name traps; other action types are out of scope.";
  }
  if (passed) {
    const soft = warns ? ` ${warns} warning${warns !== 1 ? "s" : ""} logged.` : "";
    return `Clean audit across ${actionCount} write-contract action${actionCount !== 1 ? "s" : ""}.${soft} Safe to execute — no traps from PR #1857 detected.`;
  }
  return `Audit failed: ${errs} error${errs !== 1 ? "s" : ""} (+ ${warns} warning${warns !== 1 ? "s" : ""}) across ${actionCount} write-contract action${actionCount !== 1 ? "s" : ""}. Fix errors before executing — the traps below either mis-route the signing wallet or fail silently at execute time.`;
};

export function auditWorkflow(workflow, { workflowRef = "inline" } = {}) {
  const issues = [];
  const actionNodes = iterActionNodes(workflow);
  for (const [path, node] of actionNodes) {
    const cfg = (node.data && node.data.config) || {};
    issues.push(...checkFunctionKey(path, cfg));
    issues.push(...checkFunctionArgs(path, cfg));
    issues.push(...checkAbi(path, cfg));
    issues.push(...checkWeb3Connection(path, cfg));
    issues.push(...checkNetwork(path, cfg));
    issues.push(...checkTemplates(path, cfg));
  }
  issues.push(...checkHttpTriggerBodyWrap(workflow));

  const errorCount = issues.filter(i => i.severity === SEV_ERROR).length;
  const warnCount = issues.filter(i => i.severity === SEV_WARN).length;
  const infoCount = issues.filter(i => i.severity === SEV_INFO).length;
  const passed = errorCount === 0;

  return {
    passed,
    counts: { error: errorCount, warn: warnCount, info: infoCount },
    issues,
    summary: summarise(passed, actionNodes.length, errorCount, warnCount),
    actionNodesScanned: actionNodes.length,
    workflowRef,
  };
}
