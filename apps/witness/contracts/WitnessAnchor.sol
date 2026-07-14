// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title WitnessAnchor — anchor AI-jury verdicts on 0G Chain.
/// @notice Mirrors the verdict blob's 0G Storage root hash on-chain
///         so the verdict is provably timestamped + tamper-evident.
/// @dev Pair: 0G Storage holds the encrypted verdict body; this
///      contract holds the public commitment.
contract WitnessAnchor {
    struct VerdictRecord {
        bytes32 verdictRoot;     // 0G Storage merkle root of the verdict blob
        string ruling;           // refund_buyer | release_to_seller | split_50_50 | escalate_to_human
        uint64 confidenceBps;    // 0–10000
        uint64 ts;               // block.timestamp at anchor
        address anchoredBy;      // msg.sender (jury operator)
    }

    address public immutable deployer;
    mapping(bytes32 => VerdictRecord) public verdicts;

    event VerdictAnchored(
        bytes32 indexed disputeId,
        bytes32 indexed verdictRoot,
        string ruling,
        uint64 confidenceBps,
        uint64 ts,
        address anchoredBy
    );

    constructor() {
        deployer = msg.sender;
    }

    function anchor(
        bytes32 disputeId,
        bytes32 verdictRoot,
        string calldata ruling,
        uint64 confidenceBps
    ) external {
        require(verdictRoot != bytes32(0), "verdictRoot=0");
        require(bytes(ruling).length > 0, "ruling=empty");
        require(confidenceBps <= 10000, "confidence>10000bps");

        verdicts[disputeId] = VerdictRecord({
            verdictRoot: verdictRoot,
            ruling: ruling,
            confidenceBps: confidenceBps,
            ts: uint64(block.timestamp),
            anchoredBy: msg.sender
        });

        emit VerdictAnchored(disputeId, verdictRoot, ruling, confidenceBps, uint64(block.timestamp), msg.sender);
    }

    function getVerdict(bytes32 disputeId) external view returns (VerdictRecord memory) {
        return verdicts[disputeId];
    }
}
