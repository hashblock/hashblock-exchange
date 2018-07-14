

## Hashblock Exchange

Hashblock Exchange enables encrypted data in flight and at rest while also providing exchange transaction anonymity.

_*Note*_: hashblock-exchange is alpha only and not considered production ready.

## No Batteries Required
Refer to the [Quick Start](http://github.com/hashblock/hashblock-exchange/wiki/No-Batteries-Required) document to get up and running with hashblock-exchange.

## Hashblock Exchange Back Story
First generation blockchain applications use UTXO transactions to record the value of a single resource that is minted and transferred between blockchain addresses. Bitcoin is an example of a first generation blockchain.

Second generation blockchain applications use single-resource smart-contracts to record the value of a resource that is minted and transferred between blockchain addresses. The ICO (initial coin offering) smart contract is an example of a second generation blockchain application.

Third generation blockchains use multi-resource smart-contracts to record the multi-dimensional and multi-scale values of multiple resources that are minted and exchanged between blockchain addresses. The hashblock-exchange setting, asset, and match family of smart contracts are an example of a third generation blockchain application.

The limitations of transfer-of-value smart contracts are exemplified by the fact that cryptocurrency brokerages do not use a blockchain to record the exchange of value when fiat currency is exchanged for cryptocurrency or visa-versa. A blockchain is used to record the transfer of value when units of a single resource are transferred between accounts. The cash receipt you get from a cash register is an example of a multi-resource value exchange because the receipt registers the quantity or product and the quantity of cash that is exchanged between two parties.

## Hashblock Exchange Current State

hashblock-exchange overcomes these limitation with multiple smart contract transaction families.

* The setting transaction family is used to set/update the authorization contraints for asset and unit proposals and voting.
* The asset transaction family is used to propose and vote on general asset entities on the chain. These assets are referenced in the match transactions.
* The unit transaction family is used to propose and vote on units-of-measure entities on the chain. These assets are referenced in the match transactions and will be of further use in exchange conversions.
* The exchange transaction family uses Unmatched Transaction Quantity (UTXQ) and Matched Transaction Quantity (MTXQ) transactions to record the dual initiating and reciprocating events that comprise a value exchange. An exchange could be potential as in an ask/tell duality, or contractual as in an offer/accept duality, or operational as in a commitment/obligation duality, or actual as in a give/take duality.  The match transaction family also validates that initiating events are not double matched and that the value of exchange assets balances. In contrast to a value-transfer balancing equation, **input-value=output-value**, a value-exchange balancing equation requires a ratio, **unmatched-quantity * ratio = matched-quantity**. Hashblock uses a Godel Hash encoding of units-of-measure and resources so that balancing equations like **5.bags{peanuts} * $2{USD}/1.bag{peanuts} = $10{USD}** can be validated algebraically.

Designing hashblock-exchange smart contract validation rules as algebraic expressions simplifies the application of zkSNARK cryptology to the problem of having to expose transaction data to blockchain node validators so that they can validate the accuracy of a transaction. zkSNARK makes it possible to hide transaction data in a non-interactive argument of proof so that blockchain node validators can verify, with a high degree of probability, that balancing equations are satisfied without having to know the magnitudes, units, and resources, of the quantities in the equation. The [zkSNARK wiki page]( https://github.com/hashblock/hashblock-exchange/wiki/zkSNARK) shows how a balancing equation is converted into a rank-1 constraint system that can be used with the [libsnark library]( https://github.com/scipr-lab/libsnark) to generate non-interactive proofs of knowledge off-chain, and to verify proofs of knowledge on-chain. Hashblock-exchange alpha uses a Elliptic Curve Diffie-Hellman algorithm to encrypt and decrypt balancing equation quantities to keep data on the blockchain private to node verifiers, and public to off-chain applications.

