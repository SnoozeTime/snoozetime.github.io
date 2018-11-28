---
layout: post
title: "Ethereum Virtual Machine in Rust - Part 2: The stack"
date: 2018-11-14
---


* [Ethereum virtual machine in Rust - Part 1: Introduction]({% post_url 2018-11-09-ethereum-vm-1 %})
* Ethereum virtual machine in Rust - Part 2: The stack
* [Ethereum virtual machine in Rust - Part 3: Loops and Pure functions]({% post_url 2018-11-17-ethereum-vm-3 %})
* [Ethereum virtual machine in Rust - Part 4: After the stack, the memory]({% post_url 2018-11-28-ethereum-vm-4 %})

# Memory model of Ethereum - The stack

Welcome to the second post of my Ethereum VM series. Part 1 was dedicated to the instruction set
of the Ethereum VM and showed a simple way of printing instructions from a smart contract
binary file. Now, I'll talked more about the memory model of the VM and how to understand the
code compiled by solc.

I'll try to answer those questions:
- How are additions, multiplications and subtractions implemented?
- How to find the compiled instructions for a block of solidity code?
- How are IF condition implemented?
- Where is the smart contract data stored?

There is a lot to cover here. In this post, I'll show what kind of operations are possible using the stack. There is a lot to cover so maybe this post will be split in two...

## VM specifications

The VM is described in the yellow paper, part 9: [Yellow paper](https://ethereum.github.io/yellowpaper/paper.pdf)

> The word size of the machine (and thus size of stack items0 is 256-bits.
32 bytes word size is quite large. Yellow paper mentioned it is to facilitate the Keccak-256 hash scheme and elliptic-curve computations. Hum. Let's see later if we can find out what they mean.

> The EVM is a simple stack-based architecture.

Stack-based architectures carry out their operation by pushing and popping items on a stack. A
stack is just a LIFO (last in, first out) container. For example, _a + b_ can be done by:
- pushing a on the stack
- pushing b on the stack
- pop a and pop b
- push a+b on the stack

> The memory model is a simple word-addressed byte array.

Memory is a random-access byte array. We read a word at a time (32 bytes).
 
> Unlike memory which is volatile, storage is non volatile and is maintained as part of the system state.
This is where the fun happen. The data is persisted between transactions in this storage. It
is stored under the contract's account.

## Fun with the stack
According to Rust official documentation, the best way to model a stack is just to use a vector.
Vec has `push` and `pop` operations so it fits well with our use case. Unfortunately, the size
of the stack items is 256 bits, which is not standard in Rust so I needed to use an external
package (I don't really want to implement 256-bits arithmetic myself...).

The bigint package looks pretty complete: [BigInt documentation](https://docs.rs/bigint/4.2.0/bigint/uint/struct.U256.html)
We'll have to be careful with endianess here... (Ah, can't avoid this problem forever)

Starting from part 1 implementation, our VM will become:
```rust
struct Vm {
    code: Vec<u8>, // This is the smart contract code.
    pc: usize, 
    stack: Vec<U256>,
}
```

And the factory function:
```rust
    fn new_from_file(filename: &str) -> Result<Vm, Box<Error>> {
        let mut f = File::open(filename)?;
        let mut buffer = String::new();
        f.read_to_string(&mut buffer)?;

        let code = decode(&buffer)?;
        Ok(Vm { code: code, pc: 0, stack: Vec::new()})
    }
```

### Additions
As mentioned above, an addition implemented with a stack can be with the following operations:
- PUSH left operand
- PUSH right operand
- POP 2 items from stack and add them
- PUSH result

It can be easily translated to Ethereum instructions.
- PUSH1 left
- PUSH1 right
- ADD

For example, if we want to add 2 and 5, the binary code would be:
0x60 0x02 0x60 0x05 0x01
PUSH 2    PUSH 5    ADD

Let's save the string "6002600501" to a file and use it for our testing.

I'll create an `interpret` function that will read the next instruction and apply it to
the VM.

```rust

    fn interpret(&mut self) {
        let maybe_op = self.next();

        // just for debugging
        match &maybe_op {
            Some(x) => x.describe(),
            None => {}
        }

        // The real execution
        match &maybe_op {
            Some(x) => {
                match x {
                Opcode::PUSH1(addr, value) => {
                    // Value is u8, we need to push a u256 on the stack...
                    self.stack.push(U256::from(*value));
                },
                Opcode::ADD(addr) => {
                    // How to recover nicely? There is no meaning in recovering nicely here.
                    // Just burn and crash if cannot pop.
                    let v1 = self.stack.pop().unwrap();
                    let v2 = self.stack.pop().unwrap();
                    self.stack.push(v1 + v2);
                },
                _ => {
                    // not implemented, just chill
                }
                }
            },
            None => {}
        }
    }
```

For pushing a u8 integer on the stack, we can just convert it to U256 and use the built-in 
push method of vector. Popping is also built-in, but it returns an Option. If the option is None at this point, there is NO way to recover gracefully as something must have gone wrong
with the compilation. Unwrap looks like a correct choice in that case.

By the way, I am printing the instruction description before execution. It's always a good idea
to add this kind of debug print during development. It is easier to find out when something goes
wrong. In the same spirit, I'll add a function to print the stack.

```rust

    fn print_stack(&self) {
        self.stack
            .iter()
            .enumerate()
            .rev()
            .for_each(|(i, x)| {
                let mut bytes = vec![0;32];
                x.to_big_endian(&mut bytes);
                println!("|{}:\t{:?}|", i, bytes)
            });
    }
```
Here again, chaining iterator methods really makes my day :).

My main.rs is growing quite a lot so I'll separate the code in three files:
- main.rs: Entry point. Can either print the instructions or execute the code
- evm/vm.rs: VM code and execution
- evm/opcode.rs: Opcode enumeration and debug print function

Main file will look like that:
```rust
mod evm;
use evm::vm::Vm;
use evm::opcode::Opcode;
use std::error::Error;
use std::env;

fn debug(vm: &mut Vm) {
    loop {
        match vm.next() {
            Opcode::EOF => break,
            x => x.describe(),
        }
    }
}

fn interpret(vm: &mut Vm) {
    while !vm.at_end {
        vm.interpret();
    }
    vm.print_stack();
}

fn run() -> Result<(), Box<Error>> {

    let args: Vec<String> = env::args().collect();
    let function = args[1].clone();
    let filename = args[2].clone();

    println!("In file {}", filename);
 
    let mut vm = Vm::new_from_file(&filename)?;
    println!("Correctly loaded VM");

    match &*function {
        "debug" => debug(&mut vm),
        "run" => interpret(&mut vm),
        _ => panic!("Expect either 'debug' or 'run' for first parameter")
    }
    Ok(())
}

fn main() {
    run().unwrap();
}
```

Also, I did a bit of refactoring for printing the Opcode. Instead of returning `Option<Opcode>`
from the `next` method, I'll return `Opcode` directly. I also add a new Opcode for debugging
called _UNKNOWN_ which contains the opcode that is not implemented yet.

### A word on unit testing

Previously I was just struggling to get my program working. Now that I am a bit more confident
in Rust (or is it an illusion), it is time to add some unit testing. 

The convention in Rust is to put unit tests for a module into a submodule. Basically, it comes to adding the following at the end of each file.
```rust
#[cfg(test)]
mod test {
    // unit tests here
}
```

For my vm code, I expect the code to grow quite a lot considering the number of opcode to implement. I'll move the tests to another file. That was actually more annoying to do than I initially though. If you have a better way to do this, please add a comment.

The Vm fields need to be public. The test file is in evm/vm_test.rs and the module is added
in evm/mod.rs.

```rust

// evm/mod.rs
#[cfg(test)]
mod vm_test;


// evm/vm_test.rs
use super::vm::Vm;
#[test]
fn sometest() {

}
```

To test the addition, we can create a fake binary array (Vec<u8>), create a new VM and execute
the code. After execution, we can access the state of the VM and verify that the number on the
stack corresponds to our expectations.

```rust
use super::vm::Vm;
fn create_vm(binary: Vec<u8>) -> Vm {
    Vm { code: binary, pc: 0, stack: Vec::new(), at_end: false}
}

#[test]
fn addition() {
    // 1 + 5
    let binary = vec![0x60, 0x0f, 0x60, 0x01, 0x01, 0x00];
    let mut vm = create_vm(binary); //moved

    // execute three instructions.
    // push 0x0f
    vm.interpret();
    // push 0x01
    vm.interpret();
    // add
    vm.interpret();
    // halt
    vm.interpret();

    // Now make sure the stack size is 1 and contains 16.
    assert_eq!(1, vm.stack.len());
    assert_eq!(16, vm.stack[0].as_u32()); // this is panicking in case of overflow.
}
```

### Find the addition in our compile Ethereum contract

Let's compile this code:
```solidity
pragma solidity ^0.4.0;

contract Addition{

	int public x;
    
    function add() public {
        int a = 5;
        int b = 6;
    	x = a + b;
   	}
}
```

We should see these instructions:
- Initialize a and b
- Add a and b in x
- store x

Looking directly at the compiled output is hard. Solc can generate intermediate code by passing
the --asm flag. So let's run `solc --bin-runtime --overwrite --asm --optimize -o . contract.sol` and examine the .evm file that was created.

Solc is nice and annotate the .evm file. I can find these lines:
```
    tag_13:
        /* "contract.sol":170:175  a + b */
      0xb
        /* "contract.sol":119:124  int a */
      0x0
        /* "contract.sol":166:175  x = a + b */
      sstore
        /* "contract.sol":87:182  function add() public {... */
      jump      // out
```
What happens here?
* 0xb is a shorthand for "PUSH 0xb" on the stack
* 0x0 is a shorthand for "PUSH 0x0" on the stack
* sstore will pop two values from the stack. The first one will be the key, the second one will be the value. It will then store Key=>Value in persistent storage.

This code is just storing the amount 11 at address 0 of the persistent storage. This is optimized
code so it detected at compile time that `a + b` will always be 11. If you remove the unoptimized
code, you'll notice that the output is less pretty:

```
  tag_13:
        /* "contract.sol":119:124  int a */
      0x0
        /* "contract.sol":138:143  int b */
      dup1
        /* "contract.sol":127:128  5 */
      0x5
        /* "contract.sol":119:128  int a = 5 */
      swap2
      pop
        /* "contract.sol":146:147  6 */
      0x6
        /* "contract.sol":138:147  int b = 6 */
      swap1
      pop
        /* "contract.sol":174:175  b */
      dup1
        /* "contract.sol":170:171  a */
      dup3
        /* "contract.sol":170:175  a + b */
      add
        /* "contract.sol":166:167  x */
      0x0
        /* "contract.sol":166:175  x = a + b */
      dup2
      swap1
      sstore
      pop
        /* "contract.sol":87:182  function add() public {... */
      pop
      pop
      jump      // out
```
 
There are a lot of superfluous instructions here. Swap, pop and dup are just stack operations.
If we follow the instructions and print the stack, it would look like the following:
```
[0] // int a
[0, 0] // int b
[0, 0, 5] // 5
[5, 0, 0] // a = 5
[5, 0] // pop
[5, 0, 6] // 6
[5, 6, 0] // b = 6
[5, 6] // pop
[5, 6, 6] // b - dup1
[5, 6, 6, 5] // a = dup3
[5, 6, 11] // a + b
[5, 6, 11, 0]
[5, 6, 11, 0, 11] 
[5, 6, 11, 11, 0]
[5, 6, 11] // store. here it will store 11 at address 0
[5, 6] // pop
[5] // pop
[] // pop
```
We can see a bit the logic behind the compiler. For example, to initialize an integer, it will
first push 0 on the stack. When assigning the value, it will push the value then swap with the
0 that corresponds to this integer. It will then pop the extra 0.

Let's find the corresponding opcodes for this block of intermediate code. I'll first add the POP, DUP, SWAP and SSTORE opcodes to my Rust code. Then after compiling and running the debug
program, I can find the following:

```
0xd9    JUMPDES  Destination
0xda    PUSH1   Place 1-byte item on the stack 0x0
0xdc    DUP1    Duplicate 1st stack item.
0xdd    PUSH1   Place 1-byte item on the stack 0x5
0xdf    SWAP2   Swap 1st and 3rd stack items.
0xe0    POP     Remove item from stack
0xe1    PUSH1   Place 1-byte item on the stack 0x6
0xe3    SWAP1   Swap 1st and 2nd stack items.
0xe4    POP     Remove item from stack
0xe5    DUP1    Duplicate 1st stack item.
0xe6    DUP3    Duplicate 3rd stack item.
0xe7    ADD     Addition operation
0xe8    PUSH1   Place 1-byte item on the stack 0x0
0xea    DUP2    Duplicate 2nd stack item.
0xeb    SWAP1   Swap 1st and 2nd stack items.
0xec    SSTORE  Save word to storage
0xed    POP     Remove item from stack
0xee    POP     Remove item from stack
0xef    POP     Remove item from stack
0xf0    JUMP     Jump to destination
0xf1    STOP    Halts execution
```
This map quite well to the .ecm file ;)

### Flow control - If and Loops

At this point, I am not so sure about what happen when compiling an if statement. I assume the
opcodes for this feature would be a combinaison of one of the logic operation (LT, GT, ...) and
JUMP opcode to go to change pc to the correct block of instructions. To be certain, I'll change
my previous solidity program to include a simple if-else statement and I'll take a look at the
diff between the two compiled programs.

```solidity
pragma solidity ^0.4.0;

contract Addition{

	int public x;
    bool public large;
    function add() public {
        int a = 5;
        int b = 6;
    	x = a + b;

        if (x < 5) {
            x = 5;
        } else {
            x = 7;
        }
   	}
}

```

Again, this smart contract is completely useless. Anyway, the output of solc gives us this:
```
      0x0
        /* "contract.sol":154:163  x = a + b */
      dup2
      swap1
      sstore
      pop
        /* "contract.sol":182:183  5 */
      0x5
        /* "contract.sol":178:179  x */
      sload(0x0)
        /* "contract.sol":178:183  x < 5 */
      slt
        /* "contract.sol":174:251  if (x < 5) {... */
      iszero
      tag_15
      jumpi
        /* "contract.sol":203:204  5 */
      0x5
        /* "contract.sol":199:200  x */
      0x0
        /* "contract.sol":199:204  x = 5 */
      dup2
      swap1
      sstore
      pop
        /* "contract.sol":174:251  if (x < 5) {... */
      jump(tag_16)
    tag_15:
        /* "contract.sol":239:240  7 */
      0x7
        /* "contract.sol":235:236  x */
      0x0
        /* "contract.sol":235:240  x = 7 */
      dup2
      swap1
      sstore
      pop
        /* "contract.sol":174:251  if (x < 5) {... */
    tag_16:
        /* "contract.sol":87:257  function add() public {... */
      pop
      pop
      jump      // out
```

The opcode SLOAD, SLT, ISZERO and JUMPI are used for this IF statement.
- sload(0x00) will just get the value stored at address 0x00 (it is x!)
- slt will add 1 to the stack if first value of stack is strictly less than the second value of the stack
- iszero pop a value and push 1 if the value is zero, 0 otherwise (simple not operator)
- jumpi will jump to the address stored at second place in the stack in the first value of the stack is not 0.

In our case, the stack will look like (after SLT)
[1] // SLT 
[0] // ISZERO
[0, Address of tag 15] // tag_15
[] // just increment pc as usual. No jump here.

Then assign 5 to x. If SLT was false, then JUMPI would have set pc to tag_15 and we would have
assigned 7 to x instead.

In opcode, this translates to:
```
0xfb    PUSH1   Place 1-byte item on the stack 0x5
0xfd    PUSH1   Place 1-byte item on the stack 0x0
0xff    SLOAD   Load word from storage
0x100   SLT     Signed less-than comparison
0x101   ISZERO  Simple not operator.
0x102   PUSH2   Place 2-bytes item on the stack 0x1 0x12
0x105   JUMPI   Conditional jump to destination
0x106   PUSH1   Place 1-byte item on the stack 0x5
0x108   PUSH1   Place 1-byte item on the stack 0x0
0x10a   DUP2    Duplicate 2nd stack item.
0x10b   SWAP1   Swap 1st and 2nd stack items.
0x10c   SSTORE  Save word to storage
0x10d   POP     Remove item from stack
0x10e   PUSH2   Place 2-bytes item on the stack 0x1 0x1b
0x111   JUMP     Jump to destination
0x112   JUMPDES  Destination
0x113   PUSH1   Place 1-byte item on the stack 0x7
0x115   PUSH1   Place 1-byte item on the stack 0x0
0x117   DUP2    Duplicate 2nd stack item.
0x118   SWAP1   Swap 1st and 2nd stack items.
0x119   SSTORE  Save word to storage
0x11a   POP     Remove item from stack
0x11b   JUMPDES  Destination
0x11c   POP     Remove item from stack
0x11d   POP     Remove item from stack
0x11e   JUMP     Jump to destination
0x11f   STOP    Halts execution
```
Note that the "tag_15" was actually replaced by pushing 2 bytes to the stack (0x11b). When we
take a look at line 0x11b, it actually corresponds to a JUMPDEST.

Great! We made a great progression in our understanding of the IF statement. First, we need to
set 0 or 1 on the stack depending on what condition we choose. Then, we need to push to address of the "then" block and use JUMPI. JUMPI will set the program counter to the address of the "then" block if the condition is 1. Otherwise, the program execution will continue as normal.

It should be noted that in the compile code, the "then" block in the binary file is located directly after the JUMPI instruction. In order to do so, an instruction ISZERO is added directly
after the comparison. Why do it like that? One of the possible reason is code locality. The
compiler assumes that the "then" block is executed more often than the "else" block so it makes
sense to keep it closer in memory.

### Intepreting a IF statement

Now that I have a clear image of how the If-else statement is implemented in the EVM, I'll continue the Rust interpreter and implement the missing opcodes. The program to interpret will
be:

```
0x60
0x07 // push 7
0x60
0x05 // push 5
0x12 // execute SLE (5 < 7)
0x60
0x0C // push 0x0C
0x57 // JumpI
0x60
0x01 // push 0x01
0xbb // My special instruction
0x00 // Halt.
0x5b // Jumpdest
0x60
0x02 // push 0x02
0xbb
```

0xbb is Benoit instruction which is my special instruction. It will pop and print an item from the stack. This code should print "1" as 5 < 7.

The opcodes' implementation is the following:
```rust
// in vm.rs:interpret
            Opcode::SLT(_addr) => {
                let lhs = self.stack.pop().unwrap();
                let rhs = self.stack.pop().unwrap();
                if lhs < rhs {
                    self.stack.push(U256::from(0x01));
                } else {
                    self.stack.push(U256::from(0x00));
                }
            },
            Opcode::JUMPI(_addr) => {
                let then_addr = self.stack.pop().unwrap();
                let cond = self.stack.pop().unwrap();
                if !cond.is_zero() {
                    self.pc = then_addr.as_u64() as usize;
                } // else continue to next :)
            }
            Opcode::PRINT(_addr) => {
                // TODO this should be removed in release mode..
                let v = self.stack.pop().unwrap();
                let mut bytes = vec![0;32];
                v.to_big_endian(&mut bytes);
                println!("PRINT\t{:?}|", bytes)

            },
```

If you run the program, it should display "PRINT" followed by 1. You can also change the operand
to see that the else block can be reached.

At this point, it would be worth it to implement some tooling. For example, a step by step debugger would be greatly useful.

## Wrapping up

That's a bunch of words already. We saw how the stack of the EVM was used to perform basic arithmetic and flow operations. We saw how to compile the code and map the solidity code to the
evm code. We saw how to add unit tests to validate the behaviour of the VM. Phew!

There are still some missing flow operations that I'd like to explore. In particular, I want to
review the loop and the functions. This is going to be the topic of the next part of this series.
