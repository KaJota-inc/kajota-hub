// Escrow Console client — talks to server.mjs on the same origin.
// Wallet-connect + deposit + auto-release flow uses viem via ESM CDN.
import {
  createPublicClient,
  createWalletClient,
  custom,
  http,
  parseAbi,
  formatUnits,
  formatEther,
  decodeEventLog,
} from "https://esm.sh/viem@2.21.0";
import { sepolia } from "https://esm.sh/viem@2.21.0/chains";

const $ = (s) => document.querySelector(s);
const logEl = $("#log");

// ---------- helpers ----------
function short(hex, l = 8) {
  if (!hex) return "";
  return hex.length > l * 2 + 2 ? `${hex.slice(0, l + 2)}…${hex.slice(-l)}` : hex;
}
function line(cls, ...bits) {
  const span = document.createElement("span");
  span.className = cls;
  span.textContent = bits.join(" ");
  logEl.appendChild(span);
  logEl.appendChild(document.createElement("br"));
  logEl.scrollTop = logEl.scrollHeight;
}
function clearLog() {
  logEl.textContent = "";
  const dim = document.createElement("span");
  dim.className = "dim";
  dim.textContent = "// events land here";
  logEl.appendChild(dim);
  logEl.appendChild(document.createElement("br"));
}
function txLink(hash) {
  return `${CFG.chain.explorer}/tx/${hash}`;
}

let CFG = null;
let walletClient = null;
let publicClient = null;
let account = null;

// ---------- initial config load ----------
async function loadConfig() {
  const r = await fetch("config", { cache: "no-store" });
  CFG = await r.json();
  $("#cfg-workflow").textContent = CFG.workflowId;
  $("#cfg-contract-link").href = CFG.contract.explorer;
  $("#cfg-contract-link").textContent = CFG.contract.address;
  $("#cfg-fn").textContent = CFG.contract.function;
  $("#cfg-selector").textContent = CFG.contract.selector;
  $("#cfg-keeper-link").href = CFG.keeper.explorer;
  $("#cfg-keeper-link").textContent = CFG.keeper.address;
  $("#cfg-chain").textContent = `${CFG.chain.name} · ${CFG.chain.chainId}`;
  $("#cfg-dashboard").href = CFG.kh.dashboard;
  $("#demo-deposit").textContent = CFG.demoDepositId;
  $("#arch-wf").textContent = `workflow ${short(CFG.workflowId, 8)}`;
  $("#arch-keeper").textContent = `${short(CFG.keeper.address)} · Turnkey · EIP-7702`;
  $("#fl-listing").textContent = short(CFG.fullLoop.listingId, 10);
  publicClient = createPublicClient({
    chain: sepolia,
    transport: http("https://ethereum-sepolia-rpc.publicnode.com"),
  });
  if (!CFG.khKeyConfigured) {
    line("warn", "! server has no KH_API_KEY configured — /status and release actions will 503.");
  }
}

// ---------- executions list ----------
function renderRuns(execs) {
  const runs = $("#runs");
  runs.textContent = "";
  if (!execs.length) {
    const empty = document.createElement("div");
    empty.style.color = "var(--dim)";
    empty.style.padding = "8px 4px";
    empty.textContent = "No runs yet.";
    runs.appendChild(empty);
    return;
  }
  for (const e of execs) {
    const row = document.createElement("div");
    row.className = "exec-row";
    const cls = e.status === "success" ? "success" : e.status === "error" ? "error" : "running";
    const tx = (e.transactionHashes || [])[0]?.hash;

    const c0 = document.createElement("div");
    const pill = document.createElement("span");
    pill.className = `pill ${cls}`;
    pill.textContent = e.status;
    c0.appendChild(pill);

    const c1 = document.createElement("div");
    c1.className = "mono";
    c1.textContent = e.duration ? `${e.duration} ms` : "—";

    const c2 = document.createElement("div");
    if (tx) {
      const a = document.createElement("a");
      a.className = "h";
      a.href = txLink(tx);
      a.target = "_blank";
      a.textContent = short(tx, 10);
      c2.appendChild(a);
    } else if (e.error) {
      const err = document.createElement("span");
      err.style.color = "var(--red)";
      err.textContent = e.error.length > 80 ? e.error.slice(0, 80) + "…" : e.error;
      c2.appendChild(err);
    } else {
      c2.textContent = "—";
    }

    const c3 = document.createElement("div");
    c3.className = "mono";
    c3.style.color = "var(--dim)";
    c3.textContent = e.startedAt ? new Date(e.startedAt).toLocaleTimeString() : "—";

    row.append(c0, c1, c2, c3);
    runs.appendChild(row);
  }
}

async function loadStatus() {
  try {
    const r = await fetch("status", { cache: "no-store" });
    const body = await r.json();
    if (!r.ok) throw new Error(body.error || `HTTP ${r.status}`);
    renderRuns(body.executions);
  } catch (e) {
    line("err", `status failed: ${e.message}`);
  }
}

// ---------- wallet ----------
const SEPOLIA_CHAIN_ID_HEX = "0xaa36a7";

async function connectWallet() {
  if (!window.ethereum) {
    line("err", "No injected wallet found. Install MetaMask (or another EIP-1193 wallet) and reload.");
    return;
  }
  try {
    // Ensure Sepolia
    try {
      await window.ethereum.request({
        method: "wallet_switchEthereumChain",
        params: [{ chainId: SEPOLIA_CHAIN_ID_HEX }],
      });
    } catch (switchErr) {
      if (switchErr?.code === 4902) {
        await window.ethereum.request({
          method: "wallet_addEthereumChain",
          params: [{
            chainId: SEPOLIA_CHAIN_ID_HEX,
            chainName: "Sepolia",
            nativeCurrency: { name: "Ether", symbol: "ETH", decimals: 18 },
            rpcUrls: ["https://ethereum-sepolia-rpc.publicnode.com"],
            blockExplorerUrls: ["https://sepolia.etherscan.io"],
          }],
        });
      } else if (switchErr?.code === 4001) {
        line("warn", "Chain switch rejected.");
        return;
      } else {
        throw switchErr;
      }
    }
    const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
    account = accounts[0];
    walletClient = createWalletClient({
      account,
      chain: sepolia,
      transport: custom(window.ethereum),
    });
    line("acc", `connected: ${account}`);
    await refreshBalances();
    $("#connect-btn").textContent = "Reconnect";
    $("#wallet-info").style.display = "block";
  } catch (e) {
    line("err", `connect failed: ${e.shortMessage || e.message}`);
  }
}

const USDC_ABI = parseAbi([
  "function balanceOf(address) view returns (uint256)",
  "function allowance(address owner, address spender) view returns (uint256)",
  "function approve(address spender, uint256 value) returns (bool)",
]);
const ESCROW_ABI = parseAbi([
  "function deposit(bytes32 listingId, uint256 grossAmount) returns (bytes32 depositId)",
  "event Deposited(bytes32 indexed depositId, bytes32 indexed listingId, address indexed buyer, uint256 grossAmount)",
]);

async function refreshBalances() {
  const [ethBal, usdcBal] = await Promise.all([
    publicClient.getBalance({ address: account }),
    publicClient.readContract({
      address: CFG.fullLoop.usdc,
      abi: USDC_ABI,
      functionName: "balanceOf",
      args: [account],
    }),
  ]);
  const link = $("#wallet-addr-link");
  link.href = `${CFG.chain.explorer}/address/${account}`;
  link.textContent = account;
  $("#wallet-eth").textContent = `${Number(formatEther(ethBal)).toFixed(4)} ETH`;
  $("#wallet-usdc").textContent = `${Number(formatUnits(usdcBal, 6)).toFixed(2)} USDC`;

  const need = BigInt(CFG.fullLoop.depositAmountRaw);
  const lowUsdc = usdcBal < need;
  const lowEth = ethBal < 500_000_000_000_000n; // 0.0005 ETH ≈ enough for approve+deposit
  $("#fund-usdc-btn").style.display = lowUsdc ? "" : "none";
  $("#fund-usdc-btn").onclick = () => window.open(CFG.fullLoop.faucets.usdc, "_blank");
  $("#fund-eth-btn").style.display = lowEth ? "" : "none";
  $("#fund-eth-btn").onclick = () => window.open(CFG.fullLoop.faucets.eth, "_blank");
  $("#deposit-btn").disabled = lowUsdc || lowEth;
  if (lowUsdc) line("warn", `need ${CFG.fullLoop.depositAmountHuman} USDC — click "Get Sepolia USDC" for the faucet.`);
  if (lowEth) line("warn", `need Sepolia ETH for gas — click "Get Sepolia ETH".`);
}

// ---------- deposit + auto-release ----------
async function depositAndAutoRelease() {
  const btn = $("#deposit-btn");
  btn.disabled = true;
  clearLog();
  try {
    const need = BigInt(CFG.fullLoop.depositAmountRaw);

    // 1. Approve if allowance too low
    const allow = await publicClient.readContract({
      address: CFG.fullLoop.usdc,
      abi: USDC_ABI,
      functionName: "allowance",
      args: [account, CFG.contract.address],
    });
    if (allow < need) {
      line("acc", `→ approve(USDC → escrow, ${CFG.fullLoop.depositAmountHuman})  awaiting signature…`);
      const hash = await walletClient.writeContract({
        address: CFG.fullLoop.usdc,
        abi: USDC_ABI,
        functionName: "approve",
        args: [CFG.contract.address, need],
      });
      line("dim", `  approve tx: ${short(hash, 10)}  (waiting for receipt…)`);
      await publicClient.waitForTransactionReceipt({ hash });
      line("ok", `  approve confirmed`);
    } else {
      line("dim", `allowance already sufficient — skipping approve`);
    }

    // 2. Deposit
    line("acc", `→ deposit(listingId, ${CFG.fullLoop.depositAmountHuman})  awaiting signature…`);
    const depHash = await walletClient.writeContract({
      address: CFG.contract.address,
      abi: ESCROW_ABI,
      functionName: "deposit",
      args: [CFG.fullLoop.listingId, need],
    });
    line("dim", `  deposit tx: ${short(depHash, 10)}  ${txLink(depHash)}`);
    const rcpt = await publicClient.waitForTransactionReceipt({ hash: depHash });

    // 3. Extract depositId from Deposited event
    let depositId = null;
    for (const log of rcpt.logs) {
      if (log.address.toLowerCase() !== CFG.contract.address.toLowerCase()) continue;
      try {
        const decoded = decodeEventLog({ abi: ESCROW_ABI, data: log.data, topics: log.topics });
        if (decoded.eventName === "Deposited") {
          depositId = decoded.args.depositId;
          break;
        }
      } catch {}
    }
    if (!depositId) throw new Error("Deposited event not found in receipt");
    line("ok", `  deposit landed. depositId = ${short(depositId, 10)}`);

    // 4. Auto-fire KH release
    line("acc", `→ POST /demo-release  { depositId }  (KH signs via EIP-7702 Turnkey)`);
    const r = await fetch("demo-release", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ depositId }),
    });
    const body = await r.json();
    if (!r.ok) throw new Error(body.error || `HTTP ${r.status}`);
    const eid = body.executionId;
    line("ok", `← KH accepted · executionId=${eid} status=${body.status}`);

    // 5. Poll KH execution
    for (let elapsed = 0; elapsed < 60000; elapsed += 3000) {
      await new Promise((r) => setTimeout(r, 3000));
      const s = await fetch("status", { cache: "no-store" }).then((r) => r.json());
      const run = (s.executions || []).find((x) => x.id === eid);
      if (!run) { line("dim", `  waiting… (${elapsed / 1000 + 3}s)`); continue; }
      renderRuns(s.executions);
      if (run.status === "success") {
        const tx = (run.transactionHashes || [])[0]?.hash;
        line("ok", `✓ release success in ${run.duration} ms`);
        if (tx) line("acc", `  release tx: ${txLink(tx)}`);
        line("ok", `\n🎉 end-to-end complete. buyer deposited, KeeperHub released, USDC split 85/15.`);
        break;
      }
      if (run.status === "error") {
        line("err", `⚠ release error: ${(run.error || "").slice(0, 200)}`);
        break;
      }
      line("dim", `  polling KH… status=${run.status} (${elapsed / 1000 + 3}s)`);
    }

    await refreshBalances();
  } catch (e) {
    line("err", `flow failed: ${e.shortMessage || e.message}`);
  } finally {
    btn.disabled = false;
  }
}

// ---------- fire (idempotency demo) ----------
async function fireRelease() {
  const btn = $("#fire-btn");
  btn.disabled = true;
  clearLog();
  line("acc", `→ POST /demo-release  { depositId: ${short(CFG.demoDepositId)} }`);
  try {
    const r = await fetch("demo-release", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({}),
    });
    const body = await r.json();
    if (!r.ok) throw new Error(body.error || `HTTP ${r.status}`);
    const eid = body.executionId;
    line("ok", `← KH accepted · executionId=${eid} status=${body.status}`);

    for (let elapsed = 0; elapsed < 60000; elapsed += 3000) {
      await new Promise((r) => setTimeout(r, 3000));
      const s = await fetch("status", { cache: "no-store" }).then((r) => r.json());
      const run = (s.executions || []).find((x) => x.id === eid);
      if (!run) { line("dim", `  waiting… (${elapsed / 1000 + 3}s)`); continue; }
      renderRuns(s.executions);
      if (run.status === "success") {
        const tx = (run.transactionHashes || [])[0]?.hash;
        line("ok", `✓ success in ${run.duration} ms`);
        if (tx) line("acc", `  tx: ${txLink(tx)}`);
        break;
      }
      if (run.status === "error") {
        line("warn", `⚠ error (${elapsed / 1000 + 3}s): ${(run.error || "").slice(0, 200)}`);
        line("dim", `  ↑ the release path ran end-to-end; the contract rejected the double-spend, which is the correct guard.`);
        break;
      }
      line("dim", `  polling… status=${run.status} (${elapsed / 1000 + 3}s)`);
    }
  } catch (e) {
    line("err", `fire failed: ${e.message}`);
  } finally {
    btn.disabled = false;
  }
}

// ---------- wire buttons ----------
$("#connect-btn").addEventListener("click", connectWallet);
$("#deposit-btn").addEventListener("click", depositAndAutoRelease);
$("#refresh-btn").addEventListener("click", loadStatus);
$("#fire-btn").addEventListener("click", fireRelease);

loadConfig().then(loadStatus);
