// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/// @title BondedWitnessAnchor — Arc-flavored verdict anchor with USDC dispute bond.
/// @notice Superset of WitnessAnchor.sol (deployed on 0G Chain).
///         On Arc, the filer stakes USDC when filing a dispute; the bond
///         is settled at anchor time based on the jury's ruling.
/// @dev Design: bond is the filer's skin-in-the-game against frivolous
///      disputes. On rulings that favor the filer (refund_buyer if buyer
///      filed, release_to_seller if seller filed) the bond is refunded.
///      On rulings that go against the filer the bond is slashed to a
///      treasury address (in production: Kajota's community treasury /
///      Circle grant recipient). On escalate_to_human the bond is
///      refunded (no fault-finding on ambiguity).
contract BondedWitnessAnchor {
    // ------------------------------------------------------------------
    // Types
    // ------------------------------------------------------------------

    enum Party { Unknown, Buyer, Seller }

    struct DisputeBond {
        address filer;
        Party filerParty;   // whose side the filer was on when they filed
        uint256 amount;     // USDC bonded (6-decimal representation)
        bool settled;
    }

    struct VerdictRecord {
        bytes32 verdictRoot;     // 0G Storage merkle root of the verdict blob
        string ruling;           // refund_buyer | release_to_seller | split_50_50 | escalate_to_human
        uint64 confidenceBps;    // 0–10000
        uint64 ts;               // block.timestamp at anchor
        address anchoredBy;      // msg.sender (jury operator)
    }

    // ------------------------------------------------------------------
    // State
    // ------------------------------------------------------------------

    IERC20 public immutable USDC;
    address public immutable treasury;
    address public immutable deployer;

    /// @notice Amount of USDC required to file a dispute (6-decimal USDC).
    uint256 public constant BOND_AMOUNT = 1_000_000; // 1 USDC

    mapping(bytes32 => VerdictRecord) public verdicts;
    mapping(bytes32 => DisputeBond) public bonds;

    // ------------------------------------------------------------------
    // Events
    // ------------------------------------------------------------------

    event DisputeFiled(
        bytes32 indexed disputeId,
        address indexed filer,
        Party filerParty,
        uint256 bondAmount,
        uint64 ts
    );

    event VerdictAnchored(
        bytes32 indexed disputeId,
        bytes32 indexed verdictRoot,
        string ruling,
        uint64 confidenceBps,
        uint64 ts,
        address anchoredBy
    );

    event BondSettled(
        bytes32 indexed disputeId,
        address indexed filer,
        uint256 refunded,
        uint256 slashed,
        string ruling
    );

    // ------------------------------------------------------------------
    // Constructor
    // ------------------------------------------------------------------

    constructor(address usdc, address treasury_) {
        require(usdc != address(0), "usdc=0");
        require(treasury_ != address(0), "treasury=0");
        USDC = IERC20(usdc);
        treasury = treasury_;
        deployer = msg.sender;
    }

    // ------------------------------------------------------------------
    // File a dispute (locks bond)
    // ------------------------------------------------------------------

    /// @notice Filer must approve BOND_AMOUNT USDC to this contract before calling.
    /// @param disputeId Content-addressed dispute identifier (keccak of dispute metadata).
    /// @param filerParty Whose side the filer is on (Buyer or Seller).
    function fileDispute(bytes32 disputeId, Party filerParty) external {
        require(bonds[disputeId].filer == address(0), "already filed");
        require(filerParty == Party.Buyer || filerParty == Party.Seller, "party invalid");

        require(
            USDC.transferFrom(msg.sender, address(this), BOND_AMOUNT),
            "bond transfer failed"
        );

        bonds[disputeId] = DisputeBond({
            filer: msg.sender,
            filerParty: filerParty,
            amount: BOND_AMOUNT,
            settled: false
        });

        emit DisputeFiled(disputeId, msg.sender, filerParty, BOND_AMOUNT, uint64(block.timestamp));
    }

    // ------------------------------------------------------------------
    // Anchor verdict (settles bond)
    // ------------------------------------------------------------------

    /// @notice Record the jury's verdict on-chain and settle the filer's bond.
    ///         Callable by anyone — the verdictRoot MUST be byte-identical to
    ///         the 0G Storage CID of the encrypted verdict blob, else /verify
    ///         will not cross-match. Anyone can call because the storage blob
    ///         itself is the source of truth; the anchor is a public commitment.
    function anchor(
        bytes32 disputeId,
        bytes32 verdictRoot,
        string calldata ruling,
        uint64 confidenceBps
    ) external {
        require(verdictRoot != bytes32(0), "verdictRoot=0");
        require(bytes(ruling).length > 0, "ruling=empty");
        require(confidenceBps <= 10000, "confidence>10000bps");
        require(verdicts[disputeId].verdictRoot == bytes32(0), "already anchored");

        verdicts[disputeId] = VerdictRecord({
            verdictRoot: verdictRoot,
            ruling: ruling,
            confidenceBps: confidenceBps,
            ts: uint64(block.timestamp),
            anchoredBy: msg.sender
        });

        emit VerdictAnchored(disputeId, verdictRoot, ruling, confidenceBps, uint64(block.timestamp), msg.sender);

        // Settle the bond if one was posted.
        DisputeBond storage b = bonds[disputeId];
        if (b.filer != address(0) && !b.settled) {
            _settleBond(disputeId, ruling, b);
        }
    }

    // ------------------------------------------------------------------
    // Bond settlement logic
    // ------------------------------------------------------------------

    function _settleBond(bytes32 disputeId, string calldata ruling, DisputeBond storage b) private {
        b.settled = true;

        uint256 refund = 0;
        uint256 slash = 0;

        bytes32 h = keccak256(bytes(ruling));

        if (h == keccak256(bytes("refund_buyer"))) {
            // Buyer's side won. Refund if filer was buyer; slash if filer was seller.
            if (b.filerParty == Party.Buyer) refund = b.amount;
            else slash = b.amount;
        } else if (h == keccak256(bytes("release_to_seller"))) {
            // Seller's side won. Refund if filer was seller; slash if filer was buyer.
            if (b.filerParty == Party.Seller) refund = b.amount;
            else slash = b.amount;
        } else if (h == keccak256(bytes("split_50_50"))) {
            // Half back, half slashed regardless of party.
            refund = b.amount / 2;
            slash = b.amount - refund;
        } else if (h == keccak256(bytes("escalate_to_human"))) {
            // Ambiguity — no fault-finding, full refund.
            refund = b.amount;
        } else {
            // Unknown ruling — hold the bond by NOT settling (mark unsettled).
            b.settled = false;
            return;
        }

        if (refund > 0) require(USDC.transfer(b.filer, refund), "refund failed");
        if (slash > 0) require(USDC.transfer(treasury, slash), "slash failed");

        emit BondSettled(disputeId, b.filer, refund, slash, ruling);
    }

    // ------------------------------------------------------------------
    // Views
    // ------------------------------------------------------------------

    function getVerdict(bytes32 disputeId) external view returns (VerdictRecord memory) {
        return verdicts[disputeId];
    }

    function getBond(bytes32 disputeId) external view returns (DisputeBond memory) {
        return bonds[disputeId];
    }
}
