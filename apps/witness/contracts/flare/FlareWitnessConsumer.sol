// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import {ContractRegistry} from "@flarenetwork/flare-periphery-contracts/coston2/ContractRegistry.sol";
import {IEVMTransaction} from "@flarenetwork/flare-periphery-contracts/coston2/IEVMTransaction.sol";
import {IFdcVerification} from "@flarenetwork/flare-periphery-contracts/coston2/IFdcVerification.sol";

/// @title FlareWitnessConsumer — import Kajota AI-jury verdicts onto Flare via FDC.
/// @notice A verdict is written to 0G Storage and its root hash anchored on
///         Ethereum Sepolia (via the existing WitnessAnchor contract). This
///         contract uses Flare's FDC EVMTransaction attestation type to verify
///         the anchor tx happened on Sepolia and to decode the VerdictAnchored
///         event, without trusting Kajota's server or requiring a bridge.
/// @dev The Sepolia WitnessAnchor emits:
///        event VerdictAnchored(bytes32 indexed disputeId, bytes32 indexed verdictRoot,
///                              string ruling, uint64 confidenceBps, uint64 ts, address anchoredBy);
contract FlareWitnessConsumer {
    struct VerifiedVerdict {
        bytes32 verdictRoot;      // 0G Storage merkle root of the encrypted verdict blob
        string ruling;             // refund_buyer | release_to_seller | split_50_50 | escalate_to_human
        uint64 confidenceBps;      // 0..10000
        uint64 anchorTs;           // block.timestamp at anchor tx on Sepolia
        address anchoredBy;        // address that called anchor() on Sepolia
        bytes32 anchorTxHash;      // Sepolia tx hash the FDC proof was built from
        uint64 anchorBlockNumber;  // Sepolia block number
        uint64 fdcVotingRound;     // Flare State Connector round that finalized the proof
    }

    /// @notice The Kajota WitnessAnchor deployment on Ethereum Sepolia.
    /// @dev Set at construction; every accepted event log must originate from this address.
    address public immutable witnessAnchorSepolia;

    /// @notice keccak256 topic0 of the VerdictAnchored event (computed at compile time).
    bytes32 public constant VERDICT_ANCHORED_TOPIC =
        keccak256("VerdictAnchored(bytes32,bytes32,string,uint64,uint64,address)");

    mapping(bytes32 => VerifiedVerdict) public verdicts;

    event VerdictImported(
        bytes32 indexed disputeId,
        bytes32 indexed verdictRoot,
        string ruling,
        uint64 confidenceBps,
        bytes32 sepoliaTxHash,
        uint64 fdcVotingRound
    );

    constructor(address _witnessAnchorSepolia) {
        require(_witnessAnchorSepolia != address(0), "anchor=0");
        witnessAnchorSepolia = _witnessAnchorSepolia;
    }

    /// @notice Submit a Sepolia-anchor tx proof issued by FDC and import the verdict on Flare.
    /// @dev Reverts if the Merkle proof is invalid, the tx did not succeed on Sepolia,
    ///      no expected event exists in the tx, or the event data is malformed.
    function submitVerdict(IEVMTransaction.Proof calldata _proof) external {
        IFdcVerification fdc = ContractRegistry.getFdcVerification();
        require(fdc.verifyEVMTransaction(_proof), "FDC: invalid proof");

        require(_proof.data.responseBody.status == 1, "Sepolia tx reverted");

        uint256 n = _proof.data.responseBody.events.length;
        for (uint256 i = 0; i < n; i++) {
            IEVMTransaction.Event memory ev = _proof.data.responseBody.events[i];
            if (ev.emitterAddress != witnessAnchorSepolia) continue;
            if (ev.topics.length < 3) continue;
            if (ev.topics[0] != VERDICT_ANCHORED_TOPIC) continue;

            bytes32 disputeId = ev.topics[1];
            bytes32 verdictRoot = ev.topics[2];

            (string memory ruling, uint64 confidenceBps, uint64 ts, address anchoredBy) =
                abi.decode(ev.data, (string, uint64, uint64, address));

            require(bytes(ruling).length > 0, "ruling=empty");
            require(confidenceBps <= 10000, "confidence>10000bps");

            verdicts[disputeId] = VerifiedVerdict({
                verdictRoot: verdictRoot,
                ruling: ruling,
                confidenceBps: confidenceBps,
                anchorTs: ts,
                anchoredBy: anchoredBy,
                anchorTxHash: _proof.data.requestBody.transactionHash,
                anchorBlockNumber: uint64(_proof.data.responseBody.blockNumber),
                fdcVotingRound: _proof.data.votingRound
            });

            emit VerdictImported(
                disputeId,
                verdictRoot,
                ruling,
                confidenceBps,
                _proof.data.requestBody.transactionHash,
                _proof.data.votingRound
            );
            return;
        }

        revert("No VerdictAnchored event from WitnessAnchor in this tx");
    }

    function hasVerdict(bytes32 disputeId) external view returns (bool) {
        return verdicts[disputeId].verdictRoot != bytes32(0);
    }

    function getRuling(bytes32 disputeId) external view returns (string memory) {
        return verdicts[disputeId].ruling;
    }

    function getVerdict(bytes32 disputeId) external view returns (VerifiedVerdict memory) {
        return verdicts[disputeId];
    }
}
