# An exploration of the Ethereum Virtual Machine

Hello everybody!

Ethereum is a complex piece of software. It includes among other a RPC server, the Proof-of-Work consensus algorithm, some data structure to store the state of smart contracts and its own virtual machine to execute smart contract code.

This time, I wanted to focus on the virtual machine, and in particular how does it executes a smart contract. I'm sure you will be learn something from this 6-part blog series. Expect a bunch of EVM code and random Rust interpreter.

* [Ethereum virtual machine in Rust - Part 1: Introduction]({% post_url 2018-11-09-ethereum-vm-1 %})
* [Ethereum virtual machine in Rust - Part 2: The stack]({% post_url 2018-11-14-ethereum-vm-2 %})
* [Ethereum virtual machine in Rust - Part 3: Loops and Pure functions]({% post_url 2018-11-17-ethereum-vm-3 %})
* [Ethereum virtual machine in Rust - Part 4: After the stack, the memory]({% post_url 2018-11-28-ethereum-vm-4 %})
* [Ethereum virtual machine in Rust - Part 5: Executing a real smart contract]({% post_url 2018-12-05-ethereum-vm-5 %})
* [Ethereum virtual machine in Rust - Part 5-Bis: Executing a real smart contract with Rocket]({% post_url 2018-12-12-ethereum-vm-5bis %})

There is still a lot to talk about (permanent storage, gas used per instruction). I feel that I learned enough while writing those posts. If you'd like more information about a certain topic, be sure to leave a comment ;).

