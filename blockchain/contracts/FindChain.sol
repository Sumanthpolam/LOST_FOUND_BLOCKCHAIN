// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

contract FindChain is Ownable {
    struct Record { bytes32 recordHash; uint64 registeredAt; bool exists; }
    mapping(bytes32 => Record) public records;
    event ItemRegistered(bytes32 indexed itemId, bytes32 recordHash, uint64 timestamp);
    event ClaimReviewed(bytes32 indexed claimId, bool approved, uint64 timestamp);
    event ItemHandedOver(bytes32 indexed handoverId, bytes32 indexed itemId, uint64 timestamp);

    constructor() Ownable(msg.sender) {}
    function registerItem(bytes32 itemId, bytes32 recordHash) external onlyOwner {
        require(itemId != bytes32(0) && recordHash != bytes32(0), "empty reference");
        require(!records[itemId].exists, "item already registered");
        records[itemId] = Record(recordHash, uint64(block.timestamp), true);
        emit ItemRegistered(itemId, recordHash, uint64(block.timestamp));
    }
    function reviewClaim(bytes32 claimId, bool approved) external onlyOwner {
        require(claimId != bytes32(0), "empty claim id");
        emit ClaimReviewed(claimId, approved, uint64(block.timestamp));
    }
    function confirmHandover(bytes32 handoverId, bytes32 itemId) external onlyOwner {
        require(records[itemId].exists, "unknown item");
        emit ItemHandedOver(handoverId, itemId, uint64(block.timestamp));
    }
    function verifyItem(bytes32 itemId, bytes32 recordHash) external view returns (bool) {
        return records[itemId].exists && records[itemId].recordHash == recordHash;
    }
}
