---
layout: post
title: "Ethereum Virtual Machine in Rust - Part 1"
date: 2018-11-09
---
# Exploring Ethereum Virtual Machine

Welcome to the great series - if everything goes well - about the Ethereum Virtual machine.
Lately I have been growing fond of emulation and cryptocurrency so I decided to take a look
at the inside of Ethereum: the virtual machine that is executing smart contracts.

And while implementing a fake EVM (Ethereum Virtual Machine) can be a challenge, why not do
it in a language I have absolutely no experience in. After these few lines, I realize the
probabilities I finish this serie of blog post is meager at best.

Anyway let's get started. In this first part I'll talk about compiling a solidity contract
to binary file, and creating a small program to read each instruction.

## Our Amazing smart contract

Take a look at this beauty.

```solidity
pragma solidity ^0.4.0;

contract Addition{

	int public x;
    
    function add(int a, int b) public {
    	x = a + b;
   	}
}
```

It's not doing much. Anybody can call `add` which will just store the addition of its
argument in the ledger. Then anybody can read the value.

Then, run `solc --bin-runtime --optimize -o . contract.sol` to output the compiled contract  binary code to the current directory.

On my computer, I get:
> 608060405260043610603e5763ffffffff7c0100000000000000000000000000000000000000000000000000000000600035041663a5f3c23b81146043575b600080fd5b348015604e57600080fd5b50605b600435602435605d565b005b016000555600a165627a7a723058204ff1427599e28990ab2413948c03501a48ab89d18888ac7d0205c12f443424070029

By the way, this is an hexadecimal string. This is going to be important when we read it from Rust (https://solidity.readthedocs.io/en/v0.4.21/using-the-compiler.html)

## Reading the binary file

Rust makes it quite easy to read data from a file.
```rust
use std::fs::File;
use std::io::prelude::*;
use std::error::Error;

fn run() -> Result<(), Box<Error>> {
    let filename = "myfilename";
    
    let mut f = File::open(filename)?;
    let mut buffer = String::new();
    f.read_to_string(&mut buffer)?;
    
    println!("{}", buffer);
}

fn main() {
    run().unwrap();
}

```

This is going to print the content of our file. Right now, the whole code is loaded in the
string. There might be better way to do it but ultimately the code is always loaded in the RAM
of the EVM. Also, the smart contracts tend to be small so it should be no problem to do it like
that.

## Opcode and Virtual machine execution

A virtual machine, such as the Java Virtual Machine, will take a set of instructions and execute
them. in Java the set of instruction is in the Java bytecode (https://en.wikipedia.org/wiki/Java_bytecode). In Ethereum, the set of instruction is the content of the binary file we just read. The instruction set is described in the Ethereum Yellow paper, in the appendix. https://ethereum.github.io/yellowpaper/paper.pdf

For example, the value 0x30 corresponds to the ADDRESS instruction (or opcode) and tells the
ethereum VM to get the address of currently executed account. Let's not worry about all the technical terms for now. Just keep in mind that our binary file is a set of instructions, and
each instructions are 8 bits, or 1 byte, long.

Our file content is an hexadecimal string, so we can represent the first bytes as:
_0x60_ _0x80_ _0x60_ _0x40_ _0x52_
If you look at the specifications, you can convert to a more readable format:
- PUSH one byte to stack: 0x80
- PUSH one byte to stack: 0x40
- STORE one word to memory

Next step in our program is to convert our string to a list of bytes (`u8` in Rust).

```rust
use std::num::ParseIntError;

fn decode(s: &str) -> Result<Vec<u8>, ParseIntError> {
    (0..(s.len()-1))
        .step_by(2)
        .map(|i| u8::from_str_radix(&s[i..i+2], 16))
        .collect()
}
```
It will construct a vector of bytes. Function composition here makes the code very expressive:
- We get an iterator from 0 to the length of our string (excluded)
- We get another iterator that will yield the first iterator elements with a step of 2. (Yield 0, 2, 4, 6... and so on)
- Then, for each index, we apply `u8::from_str_radix` to the slice [i..i+2] of our input string. This is going to convert the string to a `u8` integer, base 16. This can panic in case the string does not represent a valid integer base 16 ('P0' would panic)
- We consume the iterators with collect.

Iterators are lazy in Rust, so we need to call collect at the end to consume them. See here for more details: https://doc.rust-lang.org/book/second-edition/ch13-02-iterators.html

The Result trait implements FromIter, so instead of returning `Vec<Result<u8, ParseIntError>>`, we can return `Result<Vec<u8>, ParseIntError>`. See also here https://doc.rust-lang.org/std/result/enum.Result.html#method.from_iter

Now we can print our bytes from the files.
```rust

fn run() -> Result<(), Box<Error>> {
    let filename = "myfilename";
    
    let mut f = File::open(filename)?;
    let mut buffer = String::new();
    f.read_to_string(&mut buffer)?;
    
    let bytes = decode(&buffer)?;
    
    for b in &bytes {
        println!("0x{:x}", b) 
    }
    println!("{}", buffer);
}
```

## Our simple EVM

Now that we can read the bytes of our compiled smart contract, let's start the implementation
of the VM. I am just going to show how to print debug information about the instructions in this
part. We are going to iterate over the list of instructions and print what they mean. No stack
or memory involved here :)

The most basic VM will hold the code in memory, and will iterate through it. We could use range-based loop to do the iteration, but you will see later that it won't work nicely with our use case.
For example, not all instructions are only one byte long. Some, such as PUSH3, are 4 bytes long (one byte for the instruction value, and 3 bytes for the value to push to the stack).

For that reason, I am going to keep an index of the current instruction in the code vector. This index is often called pc, for program counter.

```rust

struct Vm {
    code: Vec<u8>, // smart contract code
    pc: usize, // current instruction
}

impl Vm {
    fn new_from_file(filename: &str) -> Result<Vm, Box<Error>> {
        let mut f = File::open(filename)?;
        let mut buffer = String::new();
        f.read_to_string(&mut buffer)?;

        let code = decode(&buffer)?;
        Ok(Vm { code: code, pc: 0})
    }
}
```
`new_from_file` will initialize us a new VM. Then, we need a way to model the instruction. I found enumeration in Rust well suited for this as they are very flexible. I also really like
the pattern matching with enumerations.

Let's get started. There are more than an hundred instructions in the EVM instruction set so
I'll just show a few of them.
```rust

enum Opcode {

    STOP, // 0x00
    ADD, // 0x01
    MUL, // 0x02
    
    PUSH1(u8), // 0x60
    PUSH2(u8, u8), // 0x61
    
    PUSH32(u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8), // 0x7f 
}

```
`PUSH1(u8)` means that the instruction is made of 2 bytes. First byte is the instruction value, 
second byte is the value to push to the stack. We are going to store this value in the enumeration.

Now that we have our Opcode enumeration, we need to yield opcodes from the list of bytes. This is called decoding. The `next` function will return the Opcode at the current pc, and then advance pc to the next instruction.

```rust
impl Vm {
    fn next(&mut self) -> Option<Opcode> {
        match self.code[self.pc] {
            0x00 => {
                self.pc += 1;
                Some(Opcode::STOP)
            },
            0x01 => {
                self.pc += 1;
                Some(Opcode::ADD)
            },
            0x02 => {
                self.pc += 1;
                Some(Opcode::MUL)
            },
            0x60 => {
                let value = self.code[self.pc+1];
                self.pc += 2;
                Some(Opcode::PUSH1(value))
            },
            Ox61 => {
                let value0 = self.code[self.pc+1];
                let value1 = self.code[self.pc+2];
                self.pc += 3;
                Some(Opcode::PUSH2(value0, value1))
            }
            _ => { self.pc += 1; None}
        }
    }
}
```
Right now, I ignore the error cases (for example, buffer overflow). Rust will panic if I try to
access values with indexes that are larger that the size of the vector. Also, the code is a bit
repetitive so there might be a better way to do it.

What `next` is doing is basic, but at the heart of the instruction decoding:
- Get the current byte
- Match it with an opcode
- If the opcode needs additional data from the instruction vector, extract them
- Move pc to the next instruction
- Return Opcode if found

For the `PUSH` instructions, pc is incremented multiple times.

## Peeking inside the code

`next` will give us the next instruction to execute. For now, I am just going to print it to
the console without extra logic. This will be useful in the future to debug our code. 

The easiest way is to make our enum derive from `Debug`. Then we'll be able to print the enum
name with `println!`.

```rust

#[derive(Debug)]
enum Opcode {
...
}

fn run() -> {

    ...
    
    loop {
        match vm.next() {
            Some(x) => println!("{:?}", x),
            None => {}
        }
    }
}
```

Just by doing so, I have the following output.
> ADD
> PUSH1(0)
> STOP
> MUL
> STOP
> thread 'main' panicked at 'index out of bounds: the len is 143 but the index is 143', libcore/slice/mod.rs:2046:10

This is good, but we can do much better. First, just display the enumeration name and content does not give enough information. I'd like a description of the opcode and the address of the opcode in the binary. Second, this panic should not be there, as our program executed as expected.

To avoid the panic, I'll add a secret Opcode (sshh) that signifies our program ends. We could break on None in the loop but I still want to intepret the whole code even if there are codes I
haven't implemented yet. So let's add `EOF` to our Opcode enumeration. In reality, 0x00 will
take care of that.

Before the match in `next`:
```rust
 if self.pc >= self.code.len() {
            return Some(Opcode::EOF);
        }
```

And in the match of the main loop:
```rust
    loop {
        match vm.next() {
            Some(Opcode::EOF) => break,
            Some(x) => println!("{:?}", x),
            None => {}
        }
    }
```
Happy days!

At last, I want to print more information. so let's add the instruction number and the description for each enum.
```rust

#[derive(Debug)]
enum Opcode {
    STOP(usize), // 0x00
    ADD(usize), // 0x01
    MUL(usize), // 0x02

    PUSH1(usize, u8), // 0x60
    PUSH2(usize, u8, u8), // 0x61
    PUSH32(usize, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8), // 0x7f 

    EOF,
}

```

And next will become:
```rust
    fn next(&mut self) -> Option<Opcode> {
        if self.pc >= self.code.len() {
            return Some(Opcode::EOF);
        }

        let addr = self.pc;
        match self.code[addr] {
             0x00 => {
                self.pc += 1;
                Some(Opcode::STOP(addr))
            },
            0x01 => {
                self.pc += 1;
                Some(Opcode::ADD(addr))
            },
            0x02 => {
                self.pc += 1;
                Some(Opcode::MUL(addr))
            },
            0x60 => {
                let value = self.code[self.pc+1];
                self.pc += 2;
                Some(Opcode::PUSH1(addr, value))
            },
            0x61 => {
                let value0 = self.code[self.pc+1];
                let value1 = self.code[self.pc+2];
                self.pc += 3;
                Some(Opcode::PUSH2(addr, value0, value1))
            },
            _ => { self.pc += 1;  None}
        }
    }
```

Now we can create a function that will describe the opcode.
```rust

impl Opcode {
    fn describe(&self) {
        match self {
        Opcode::STOP(line) => println!("0x{:x}\tSTOP\tHalts execution", line),
        Opcode::ADD(line) => println!("0x{:x}\tADD\tAddition operation", line),
        Opcode::MUL(line) => println!("0x{:x}\tMUL\tMultiplication operation", line),
        Opcode::PUSH1(line, x) => println!("0x{:x}\tPUSH1\tPlace 1-byte item on the stack 0x{:x}", line, x),
        Opcode::PUSH2(line, x0, x1) => println!("0x{:x}\tPUSH2\tPlace 2-bytes item on the stack 0x{:x} 0x{:x}", line, x0, x1),
        _ => println!("Unknown opcode")
 
        }
    }
}


// update run function
fn run() -> Result<(), Box<Error>> {

    let filename = "Addition.bin-runtime";
    
    println!("In file {}", filename);

    let mut vm = Vm::new_from_file(&filename)?;

    loop {
        match vm.next() {
            Some(Opcode::EOF) => break,
            Some(x) => x.describe(),
            None => {}
        }
    }

    Ok(())
}
```

## A final word

I showed in this article how to create a tool to display the instructions from an ethereum smart contract binary. It is not complete: the `describe` and `next` method have to be populated with all the opcodes in order to be complete.

In the next article I will introduce the memory layout of the EVM. We'll talk about concepts such as stack, memory and persistent storage.
