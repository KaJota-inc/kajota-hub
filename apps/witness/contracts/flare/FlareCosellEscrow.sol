// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import {FlareWitnessConsumer} from "./FlareWitnessConsumer.sol";

/// @title FlareCosellEscrow — Flare-native native-token escrow gated by a
///        cross-chain Kajota AI-jury verdict imported via FDC.
/// @notice Demonstrates that the FDC-imported verdict is *load-bearing*:
///         no verdict → no release. Remove FDC and the escrow cannot resolve.
/// @dev Native token (C2FLR on Coston2) is used to keep the demo self-contained;
///      the production Kajota Mesh escrow on Sepolia uses USDC.
contract FlareCosellEscrow {
    FlareWitnessConsumer public immutable consumer;

    struct EscrowPos {
        address buyer;
        address seller;
        uint256 amountWei;
        bytes32 disputeId;
        bool resolved;
    }

    mapping(bytes32 => EscrowPos) public escrows;

    event Deposited(
        bytes32 indexed escrowId,
        address indexed buyer,
        address indexed seller,
        uint256 amount,
        bytes32 disputeId
    );

    event Released(
        bytes32 indexed escrowId,
        bytes32 indexed disputeId,
        string ruling,
        address paidTo,
        uint256 amount
    );

    constructor(FlareWitnessConsumer _consumer) {
        require(address(_consumer) != address(0), "consumer=0");
        consumer = _consumer;
    }

    /// @notice Deposit native funds into escrow, pre-committing to a Kajota disputeId.
    /// @param escrowId Application-chosen unique id (e.g. keccak256(buyer|seller|nonce)).
    /// @param seller The counterparty who receives funds if verdict = release_to_seller.
    /// @param disputeId The Kajota disputeId whose verdict will govern this escrow.
    function deposit(bytes32 escrowId, address seller, bytes32 disputeId) external payable {
        require(escrows[escrowId].amountWei == 0, "escrow exists");
        require(msg.value > 0, "no funds");
        require(seller != address(0) && seller != msg.sender, "bad seller");

        escrows[escrowId] = EscrowPos({
            buyer: msg.sender,
            seller: seller,
            amountWei: msg.value,
            disputeId: disputeId,
            resolved: false
        });

        emit Deposited(escrowId, msg.sender, seller, msg.value, disputeId);
    }

    /// @notice Release escrow funds according to the FDC-imported Kajota verdict.
    /// @dev Anyone can trigger release once the verdict is imported (it is deterministic).
    function release(bytes32 escrowId) external {
        EscrowPos storage e = escrows[escrowId];
        require(e.amountWei > 0, "no such escrow");
        require(!e.resolved, "already resolved");
        require(consumer.hasVerdict(e.disputeId), "no FDC-verified verdict yet");

        string memory ruling = consumer.getRuling(e.disputeId);
        bytes32 rulingHash = keccak256(bytes(ruling));

        address payable payTo;
        if (rulingHash == keccak256(bytes("release_to_seller"))) {
            payTo = payable(e.seller);
        } else if (rulingHash == keccak256(bytes("refund_buyer"))) {
            payTo = payable(e.buyer);
        } else {
            revert("Unhandled ruling; use split() or escalate off-chain");
        }

        e.resolved = true;
        uint256 amount = e.amountWei;
        (bool ok, ) = payTo.call{value: amount}("");
        require(ok, "transfer failed");

        emit Released(escrowId, e.disputeId, ruling, payTo, amount);
    }
}
