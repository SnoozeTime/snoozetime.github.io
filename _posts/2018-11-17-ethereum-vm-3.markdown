---
layout: post
title: "Ethereum Virtual Machine in Rust - Part 3: Looping and Functioning"
date: 2018-11-17
---

* [Ethereum virtual machine in Rust - Part 1: Introduction]({% post_url 2018-11-09-ethereum-vm-1 %})
* [Ethereum virtual machine in Rust - Part 2: The stack]({% post_url 2018-11-14-ethereum-vm-2 %})
* Ethereum virtual machine in Rust - Part 3: Loops and Pure functions


# Looping and calling Functions in the EVM!

Last time, we saw how to add two numbers and how to execute a If-Else statement using the stack
in the EVM. This time, I want to continue learning about how the stack works by taking a look 
at loops. I'll follow the same methodology as before:
- First, compile and read the binary from solc
- Implement an interpreter in Rust

Once you've built a mental model about how the stack works, reading binary data is not that complicated.
It takes some effort to follow the evolution of the stack but everything is well documented.

## Compiling a loop

The smart contract is super simple:
```solidity
pragma solidity ^0.4.0;

contract TestingStuff {

	uint public x;

    function add() public {
        uint sum = 0;
        for (uint i = 0; i < 10; i++) {
            sum += i;
        }
        x = sum;
    }
}
```
Maybe at the end of the serie I'll try something useful.

By the way, a for loop can be written as a while loop easily. 
```solidity
{
    uint i = 0;
    while (i < 10) {
        sum += i
        i++;
    }
}
```

Just by looking at the code and thinking the basic elements of a IF statement, we can guess
how this will be compiled.
- First, we need to initialize i. Push 0 on the stack.
- Then, we need to compare with 0xA.
- Using the JUMPI instruction, we can either execute the loop body or skip it.
- We execute the loop body
- We increase i at the end of the loop body
- we jump back to the condition

The missing block here is the JUMP back.

Indeed, when compiling, there is not so many surprises:
```
0x91    PUSH1   Place 1-byte item on the stack 0x0
0x93    DUP1    Duplicate 1st stack item.
0x94    PUSH1   Place 1-byte item on the stack 0x0
0x96    SWAP2   Swap 1st and 3rd stack items.
0x97    POP     Remove item from stack
0x98    PUSH1   Place 1-byte item on the stack 0x0
0x9a    SWAP1   Swap 1st and 2nd stack items.
0x9b    POP     Remove item from stack
0x9c    JUMPDES  Destination
0x9d    PUSH1   Place 1-byte item on the stack 0xa
0x9f    DUP2    Duplicate 2nd stack item.
0xa0    LT      Less-than comparison
0xa1    ISZERO  Simple not operator.
0xa2    PUSH1   Place 1-byte item on the stack 0xb5
0xa4    JUMPI   Conditional jump to destination
0xa5    DUP1    Duplicate 1st stack item.
0xa6    DUP3    Duplicate 3rd stack item.
0xa7    ADD     Addition operation
0xa8    SWAP2   Swap 1st and 3rd stack items.
0xa9    POP     Remove item from stack
0xaa    DUP1    Duplicate 1st stack item.
0xab    DUP1    Duplicate 1st stack item.
0xac    PUSH1   Place 1-byte item on the stack 0x1
0xae    ADD     Addition operation
0xaf    SWAP2   Swap 1st and 3rd stack items.
0xb0    POP     Remove item from stack
0xb1    POP     Remove item from stack
0xb2    PUSH1   Place 1-byte item on the stack 0x9c
0xb4    JUMP     Jump to destination
0xb5    JUMPDES  Destination
0xb6    DUP2    Duplicate 2nd stack item.
0xb7    PUSH1   Place 1-byte item on the stack 0x0
0xb9    DUP2    Duplicate 2nd stack item.
0xba    SWAP1   Swap 1st and 2nd stack items.
0xbb    SSTORE  Save word to storage
```

- 0x91 to 0x9b: `i` is initialized.
- 0x9c: Set an anchor for a jump.
- 0x9d to 0xA2: This is a condition statement, similar to if.
- 0xa2: Address for after the loop
- 0xa4: JUMPI which will check if we need to loop again
- 0xa5 to 0xb1: Body of the loop
- 0xb2: Push the loop condition address to the stack
- 0xb4: Jump to the address located in the first item of the stack
- 0xb5 to 0xbb: After the loop.

## Testing in the VM

The only missing part in our Rust VM is the implementation of JUMP. This is even more simple
than JUMPI as we just need to pop the next value of pc from the stack.

```rust
Opcode::JUMP(_addr) => {
    let jump_location = self.stack.pop().unwrap();
    self.pc = jump_location.as_u64() as usize;
},
```

Creating binary code by hand is beginning to be a bit of work so I'll just implement some missing opcodes such as DUP, SWAP and ISZERO and I'll use the code compiled by solc after
cleaning it up a bit (need to replace the JUMP address by the real ones).

```
5b60008060009150600090505b600a81101560255780820191508080600101915050600c565b81600081905550505000
```

### Interlude

Code begins to be more and more complex so I took some time to create a step by step debugger.

First, add this to the Vm implementation. It can be completed later with more debugging statements.
```rust
    // see part 2 for print_stack
    pub fn print_stack(&self) {
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

    pub fn print_debug(&self) {
        println!("pc:{}\n", self.pc);
        println!("Stack:");
        self.print_stack();
    }
```

Then, main.rs will be modified to execute this:
```rust
use std::io;

fn debug(vm: &mut Vm) {

    loop {
        if vm.at_end {
            break;
        }

        // Debugger.
        // c to continue
        // s to print stack
        // q to quit
        let mut input = String::new();
        io::stdin().read_line(&mut input).ok().expect("Couldn't read line");

        match &*input {
            "c\n" => vm.interpret(),
            "s\n" => vm.print_debug(),
            "q\n" => break,
            _ => println!("Please type either c, s or q"), 
        }
    }

}

```

Using this function, I can execute the bytecode step by step and take a look at the current VM
state.

### Running it!

Mmh, there are a few surprises here (I forgot to implement POP and had a bug in my JUMPI). 
When decomposed, a for loop is quite simple to implement using the EVM opcodes.

## Pure functions

Just taking a look at for loops makes a light blog post so I'll also talk about pure functions.
According to solidity documentation,
> Functions can be declared pure, in which case they promise not to read from or modify the state.

Looks like a simple first step into understand functions in the compiled code.

```solidity
pragma solidity ^0.4.0;

contract TestingStuff {

	uint public x;

    function f(uint a, uint b) public pure returns (uint) {
        return a * (b + 42);
    }
    
    function add() public {
        x = f(1, 4);
    }
}
```
What could go wrong.

### A quick peak at the compile code

What I want to find in the compile code is:
- How to store the parameters of a function
- How to call the function
- How to return a value
So let's try to find that out.

```
0xef	JUMPDES	 Destination
0xf0	PUSH1	Place 1-byte item on the stack 0x0
0xf2	PUSH1	Place 1-byte item on the stack 0x2a
0xf4	DUP3	Duplicate 3rd stack item.
0xf5	ADD	Addition operation
0xf6	DUP4	Duplicate 4th stack item.
0xf7	MUL	Multiplication operation
0xf8	SWAP1	Swap 1st and 2nd stack items.
0xf9	POP	Remove item from stack
0xfa	SWAP3	Swap 1st and 4th stack items.
0xfb	SWAP2	Swap 1st and 3rd stack items.
0xfc	POP	Remove item from stack
0xfd	POP	Remove item from stack
0xfe	JUMP	 Jump to destination
0xff	JUMPDES	 Destination
0x100	PUSH2	Place 2-bytes item on the stack 0x1 0xb
0x103	PUSH1	Place 1-byte item on the stack 0x1
0x105	PUSH1	Place 1-byte item on the stack 0x4
0x107	PUSH2	Place 2-bytes item on the stack 0x0 0xef
0x10a	JUMP	 Jump to destination
0x10b	JUMPDES	 Destination
0x10c	PUSH1	Place 1-byte item on the stack 0x0
0x10e	DUP2	Duplicate 2nd stack item.
0x10f	SWAP1	Swap 1st and 2nd stack items.
0x110	SSTORE	Save word to storage
0x111	POP	Remove item from stack
0x112	JUMP	 Jump to destination
0x113	STOP	Halts execution
```

No biggies here. The function starts at address 0x100. Let's take a look at the stack during the execution.
```
[0x10b]
[0x10b, 0x01]
[0x10b, 0x01, 0x04]
[0x10b, 0x01, 0x04, 0xef]
```
This is the stack before 0x10a (JUMP). The address of where to continue after calling the function is
first put on the stack. Then the two function parameters are added, then the address of the code
for the function is pushed on the stack so that we can call jump.

```
[0x10b, 0x01, 0x04] // Call jump

At this point, we are at address 0xef
[0x10b, 0x01, 0x04, 0x0]
[0x10b, 0x01, 0x04, 0x0, 0x2a]
[0x10b, 0x01, 0x04, 0x0, 0x2a, 0x4]
[0x10b, 0x01, 0x04, 0x0, 0x2e]
[0x10b, 0x01, 0x04, 0x0, 0x2e, 0x01]
[0x10b, 0x01, 0x04, 0x0, 0x2e]
[0x10b, 0x01, 0x04, 0x2e, 0x0]
[0x10b, 0x01, 0x04, 0x2e]
[0x2e, 0x01, 0x04, 0x10b] // swap 1st and 4th
[0x2e, 0x10b, 0x04, 0x01] // swap 1st and 3rd 
[0x2e, 0x10b, 0x04] 
[0x2e, 0x10b] 
```
A lot of swap, dup is going on but essentially the calculation is made. Then, by swapping element and popping
the intermediate variables, the stack end up with the return value in second position and the address of where
to return in the first position.

After jumping, it will look like:
```
[0x2e]
[0x2e, 0x0]
[0x2e, 0x0, 0x2e]
[0x2e, 0x2e, 0x0]
```
Then, the store instruction is executed as expected.

The funny thing here is that I do not have to add anything to my Rust code in order to make it
work for these kind of functions. A pure function is just a clever combinaison of JUMPs, PUSH and
SWAP:
- Return location is pushed
- Arguments are pushed in order
- Function location is pushed then we jump to it
- Body of the function is executed
- Return location is put at the top of the stack, return value is right next behind
- We jump to the return location. Value at the top of the stack is the function return value.
Easy peasy.

