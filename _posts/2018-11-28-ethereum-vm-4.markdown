---
layout: post
title: "Ethereum Virtual Machine in Rust - Part 4: After the Stack, the Memory"
date: 2018-11-28
---


* [Ethereum virtual machine in Rust - Part 1: Introduction]({% post_url 2018-11-09-ethereum-vm-1 %})
* [Ethereum virtual machine in Rust - Part 2: The stack]({% post_url 2018-11-14-ethereum-vm-2 %})
* [Ethereum virtual machine in Rust - Part 3: Loops and Pure functions]({% post_url 2018-11-17-ethereum-vm-3 %})
* Ethereum virtual machine in Rust - Part 4: After the stack, the memory



In my previous posts about the Ethereum VM, I focused on very simple
examples, using `Value Types`. These are variable that will always be passed
by value according to the [Solidity documentation](https://solidity.readthedocs.io/en/v0.4.24/types.html).

We saw that passing by value involved the stack. However, `Reference types`,
which are types that do not always fit in 256 bit, should be store either
in the memory or in the storage. As opposed to the storage, the memory
does not persist between contract's
execution.

`Reference Types` are:
- arrays
- struct
- mapping

According to the documentation, the default location for function parameters
is `memory` and the default for local variables is `storage`. State variables
are forced to have their location in `storage`.

Well, what a bummer. If I want to exhibit the usage of memory in our compiled
code, I'd need to use a more complex example.

## Solidity code

```solidity
pragma solidity ^0.4.0;

contract Example {
    struct Position {
        address owner;
        uint id;
    }
    
    uint x; 
    function takeOver() public {
        Position memory p = Position(msg.sender, 0);
        x = p.id;
    }
}
```

Again a useless contract. I just want to exhibit the use of the memory without involving the storage too much. I swear by the end of this post series you'd be able to understand
what happens for a real contract :').

What I want to understand here is:
- How a struct is defined in binary code
- How memory is used to store p

First, let's read a bit about the memory in the EVM specifications.

## Specifications for memory

### Memory layout

> The memory model is a simple word-addressed byte array. 

The stack had two basic operations: push and pop. The memory is word
addressed so we can retrieve data at specific addresses in the byte array.
Inserting is also done wherever in the array.

In solidity, the memory follows a specific layout ([Doc](https://solidity.readthedocs.io/en/v0.4.24/miscellaneous.html)). Four 32 bytes slots are reserved for solidity usage:
- 0x00 to 0x3f: Scratch space for hashing methods
- 0x40-0x5f: Free memory pointer
- 0x60-0x7f: Zero slot

> Solidity always places new objects at the free memory pointer and memory is never freed (this might change in the future).

When creating an object in memory, we first need to take a look at the first available
address. Then we can insert the object in memory at this address. The first available address,
i.e. the free memory pointer, can be loaded with mload(0x40). This instruction will load
a 32 bytes address.

### Opcodes

According to the yellow paper, the instructions that deal with the memory are:
- SHA3: Compute Keccak-256 hash
- CALLDATACOPY: Copy input data in current environment to memory
- CODECOPY: Copy code running in current environment to memory
- EXTCODECOPY: Copy an account's code to memory
- MLOAD: Load word from memory
- MSTORE: Save word to memory
- MSTORE8: Save byte to memory
- CREATE: Create a new account with associated code
- CALL: Message-call into an account
- RETURN: Halt execution returning output data

You can see that there is not arithmetic nor control flow involved in these
instructions. These instructions are the domain of the stack.

Something to note about memory is that the amount of gas to pay will grow with the memory
usage.


## Decompiling our compiled code

As always, `solc` is a dear an annotate the .evm code for us.
```
    tag_6:
        /* "contract.sol":191:214  Position(msg.sender, 0) */
      0x40
      dup1
      mload
      swap1
      dup2
      add
      0x40
      mstore
      dup1
        /* "contract.sol":200:210  msg.sender */
      caller
        /* "contract.sol":191:214  Position(msg.sender, 0) */
      0xffffffffffffffffffffffffffffffffffffffff
      and
      dup2
      mstore
      0x20
      add
        /* "contract.sol":212:213  0 */
      0x0
        /* "contract.sol":191:214  Position(msg.sender, 0) */
      dup2
      mstore
      pop
        /* "contract.sol":171:214  Position memory p = Position(msg.sender, 0) */
      swap1
      pop
        /* "contract.sol":228:229  p */
      dup1
        /* "contract.sol":228:232  p.id */
      0x20
      add
      mload
        /* "contract.sol":224:225  x */
      0x0
        /* "contract.sol":224:232  x = p.id */
      dup2
      swap1
      sstore
      pop
        /* "contract.sol":134:239  function takeOver() public {... */
      pop
      jump	// out
        /* "contract.sol":25:241  contract Example {... */
 
```
    

Well, this is slightly more complicated. Let's decompose it and show the current stack and memory.

Initial situation:
```
stack: [...]
memory: ... |0x40 -> addr1 | .... | ....
```
The memory just contains the first available address (addr1). The stack state is unknown.

```
        /* "contract.sol":213:237  Position(msg.sender, id) */
      0x40
      [ 0x040 ]
      ... |0x40 -> addr1 | ...
      
      dup1
      [0x40, 0x40]
      ... |0x40 -> addr1 | ...
      
      mload
      [0x40, addr1]
      ... |0x40 -> addr1 | ...
      
      swap1
      [addr1, 0x40]
      ... |0x40 -> addr1 | ...
      
      dup2
      [addr1, 0x40, addr1]
      ... |0x40 -> addr1 | ...
      
      add
      [addr1, addr1 + 0x40]
      ... |0x40 -> addr1 | ...
      
      0x40
      [addr1, addr1+0x40, 0x40]
      ... |0x40 -> addr1 | ...
      
      mstore
      [addr1]
      ... | 0x40 -> addr1+0x40 | ...
```
Well this is funky. What happened here is that we got  the free memory pointer from the memory,
and set a new value for this free memory pointer. The new value is the original value increased
by 64 bytes. So now, we have a free memory address on the stack that we can use to store some
data. In the memory, we have stored the next free memory address that we can use later.

The question here is why does the code only allocate two times 32 bytes. Let's continue.
```
      dup1
      [addr1, addr1]
      
      caller
      [addr1, addr1, CALLER]
      
      0xfffffffffffffffffffffffffffffffffffffff
      [addr1, addr1, CALLER, 0xffffffffffffffffffffffffffffffffffffffff]
      
      and
      [addr1, addr1, CALLER MASKED]
      
      dup2
      [addr1, addr1, CALLER MASKED, addr1]
      ... | 0x40 -> addr1+0x40 | .. 
      
      mstore
      [addr1, addr1]
      ... | 0x40 -> addr1+0x40 | ... | addr1 -> CALLER MASKED | ...
      
      0x20
      [addr1, addr1, 0x20]
      
      add
      [addr1, addr1+0x20]
    
      0x0
      [addr1, addr1+0x20, 0]
      
      dup2
      [addr1, addr1+0x20, 0x0, addr1+0x20]
      
      mstore
      [addr1, addr1+0x20]
      ... | 0x40 -> addr1+0x40 | ... | addr1 -> CALLER MASKED | addr1+0x20 -> 0x0 | ...
 
```
Now we have our answer as why only 2 times 32 bytes were allocated. It was to store the
`msg.sender` and `0` that are the members of our structure. The address of `p` is `addr1`. 
The content of `Position` is known at compile-time so `solc` knows about many bytes are
required for `Position`. 

(By the way, I have no idea about the 0xffffffffffffffffffffffffffffffffffffffff AND. If you
know its use please leave me a message).

Now for the rest of the code.
```
      pop
      [addr1]
      
      swap1
      [addr1, unknown] // something that was already on the stack. 
      
      pop
      [addr1]
      
      dup1
      [addr1, addr1]
      
      0x20
      [addr1, addr1, 0x20]
      
      add
      [addr1, addr1+0x20]
      
      mload
      [addr1, 0x0]
      
      0x0
      [addr1, 0x0 from mload, 0x0]
      
      dup2
      [addr1, 0x0 from mload, 0x0, 0x0 from mload]
      
      swap1
      [addr1, 0x0 from mload, 0x0 from mload, 0x0]
      
      sstore
      [addr1, 0x0 from mload]
      
      pop
      [addr1]
        
      pop
      []
      
      jump	// out
```
Okay now it looks like something we've seen before. We want to store p.id in x. Solidity will
store x at address 0x0 in the storage. It will first load p.id from memory. The address of this
field is just `address of p + offset of field ID`, which is `addr1 + 0x20`.

Nice ! I think we're ready to emulate that with Rust.

## Emulation in Rust

As always, a few opcodes are not implemented (whoops). PUSH32, MLOAD, MSTORE.

In order to avoid duplicating code too much, I refactored a bit the enumeration to accept directly U256 in PUSHX values.

```rust
// in opcode.rs
    // Push operations
    PUSH1(usize, U256), // 0x60
    PUSH2(usize, U256), // 0x61
    PUSH32(usize, U256),

// in vm.rs

// next function
            0x60 => {
                let value = self.extract_u256(1);
                self.pc += 2;
                Opcode::PUSH1(addr, value)
            },
            0x61 => {
                let value = self.extract_u256(2);
                self.pc += 3;
                Opcode::PUSH2(addr, value)
            },
            0x73 => {
                let value = self.extract_u256(32);
                self.pc += 33;
                Opcode::PUSH32(addr, value)
            }


// Vm.extract_u256

    fn extract_u256(&mut self, to_extract: usize) -> U256 {
        let mut bytes = vec![0;32];
        for i in  0..to_extract {
            let value = self.code[self.pc+i+1];
            bytes[32-to_extract+i] = value;
        }

        U256::from_big_endian(&bytes)
    }
 
```

That's much less complexity. I guess we could factored it more to get the numbers of byte
to read for each PUSH instruction and group everything under one match case. For now it should
be fine.

Now, to implement MLOAD and MSTORE, we need to have an implementation of the memory. According to specifications, we should be able to load words from the memory (32-bytes) and we should be able to store words but also individual bytes. The memory can also grow. 

Let's use a vector of bytes. The first bytes will be reserved according to solidity specs.

> By the way, saving the free memory pointer at 0x40 is from Solidity specification, not the EVM.

A vector initial size is 0. When calling instructions such as MSTORE or MLOAD, a certain address
is specified. If the address is out of range of the current memory, we need to resize the vector. In go-ethereum, this is done by resize up to the requested index + a certain amount of
bytes. See here:
- https://github.com/ethereum/go-ethereum/blob/cab1cff11cbcd4ff60f1a149deb71ec87413b487/core/vm/memory_table.go
- https://github.com/ethereum/go-ethereum/blob/b66f793443f572082d24f115e706532a620ba3ee/core/vm/memory.go

I will do something similar. Simply use a structure wrapping a `Vec<u8>`. Resize it if an instruction needs to access an address. For our tests, the following should do the trick:

```rust
// memory.rs
extern crate uint;

use self::uint::U256;


pub struct Memory {
    data: Vec<u8>,
}

impl Memory {

    pub fn new() -> Memory {
        Memory { data: Vec::new() }
    }

    pub fn resize(&mut self, new_size: usize) {
        if self.data.len() < new_size {
            self.data.resize(new_size, 0);
        }
    }

    // We only get words from the memory
    pub fn get_word(&self, addr: usize) -> U256 {
        // will panic if oob
        U256::from_big_endian(&self.data[addr..addr+32])
    }

    pub fn set_byte(&mut self, addr: usize, b: u8) {
        self.data[addr] = b;
    }

    pub fn set_word(&mut self, addr: usize, w: U256) {
        let mut bytes = vec![0; 32];
        w.to_big_endian(&mut bytes);

        for i in 0..bytes.len() {
            self.data[i+addr] = bytes[i];
        }
    }
}
```

We can see the 4 operations mentioned above:
- Resize in case the address requested is out of bound
- Get by word
- Set a word or a byte

Now for the MLOAD and MSTORE implementation, it is easy. First get the address, then resize the memory (might do nothing if address already in range). At last, either Store or Load.

```rust
// In vm.rs:interpret
            Opcode::MLOAD(_addr) => {
                let offset = self.stack.pop().unwrap();
                let loaded_value = self.mem.get_word(offset.as_u64() as usize);
                self.stack.push(loaded_value);
            },
            Opcode::MSTORE(_addr) => {
                let offset = self.stack.pop().unwrap();
                let w = self.stack.pop().unwrap();
                self.mem.set_word(offset.as_u64() as usize, w);
            },
            Opcode::MSTORE8(_addr) => {
                // stored as big endian so we get the last byte
                let offset = self.stack.pop().unwrap();
                let b = self.stack.pop().unwrap().byte(31);
                self.mem.set_byte(offset.as_u64() as usize, b);
            },
```

Before executing these instructions, we need to resize our memory. I added a function that will return an Option. It will contain the new size of the memory if we need to resize.

```rust
fn get_new_size(&self, code: &Opcode) -> Option<usize> {
        match code {
        Opcode::MLOAD(_) | Opcode::MSTORE(_) => {
            Some(self.stack.last().unwrap().as_u64() as usize + 32)
        },
        Opcode::MSTORE8(_) => {
            Some(self.stack.last().unwrap().as_u64() as usize + 1)
        },
        _ => None  
        }
    }

```

And right before the execution match:
```rust
        match self.get_new_size(&op) {
            Some(n) => self.mem.resize(n),
            _ => {}
        }
```

Let's try something. I will try to execute the following code.
```
0x60
0x01 // push 1
0x60
0x50 // push 0x50
0x80
0x91 // SWAP2
0x90 // SWAP1
0x52 // store 1 at 0x50
0x51 // load from 0x50
0x00 // halt
```

At the end, we should have 0x01 on top of the stack.

When debugging, I get the following output:
```
Please type either c, s or q
c
0x0     PUSH1   Place 1-byte item on the stack
c
0x2     PUSH1   Place 1-byte item on the stack
c
0x4     DUP1    Duplicate 1st stack item.
s
pc:5

Stack:
|2:     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 80]|
|1:     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 80]|
|0:     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]|
c
0x5     SWAP2   Swap 1st and 3rd stack items.
s
pc:6

Stack:
|2:     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]|
|1:     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 80]|
|0:     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 80]|
c
0x6     SWAP1   Swap 1st and 2nd stack items.
s
pc:7

Stack:
|2:     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 80]|
|1:     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]|
|0:     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 80]|

Please type either c, s or q
c
0x7     MSTORE  Save word to memory
s
pc:8

Stack:
|0:     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 80]|
c
0x8     MLOAD   Load word from memory
s
pc:9

Stack:
|0:     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]|
```

It does not look too bad. Obviously, if we were aiming for a production-quality VM, we would need to implement many many more tests to ensure the behaviour of our VM is entirely correct.

That was quite a lot to cover! Next time, I'll take a small break from the different models of memory in the EVM and I'll talk about how to execute a contract from an user's input data.

