---
title: "Deserialization with Rust"
layout: "post"
date: 2019-01-08
---
For my NES emulator, I want to be able to save the current state of the NES so that I can reload it 
later. This process is called serialization, and if you want to do it in Rust, the cool kid in the block
is serde.

If you just want to serialize simple types, Serde pretty much provides everything out of the box. Things
begin to get tricky when more dynamic types enter the scene. This post will explore how I implement
serialization for mappers in the NES emulator. Mappers are not known at compile time and are determined
by the ROM file header. Typically, you'd need 2 or 3 mapper's implementation to get a lot of games running.

## First iteration: Model the mapper as `Box<dyn Mapper>`

Coming from OOP, I modeled the mapper as a trait. The objects that contains a mapper would
hold a pointer to the trait and the pointer is created from the ROM file header.

```rust
pub type MapperPtr = Box<dyn Mapper>;

pub trait Mapper {

    // Read ROM from cartridge
    // writing is needed for some mappers that have registers.
    fn read_prg(&self, addr: usize) -> u8;
    fn write_prg(&mut self, addr: usize, value: u8);

    // Read/Write pattern tables. Sometimes, it is RAM instead of ROM
    fn read_chr(&self, addr: usize) -> u8;
    fn write_chr(&mut self, addr: usize, value: u8);
    fn get_chr(&self, idx: usize) -> &[u8];

    fn get_mirroring(&self) -> Mirroring;
}

pub fn create_mapper(rom: &rom::INesFile) -> Result<MapperPtr, String> {
    let mapper_id = rom.get_mapper_id();

    match mapper_id {
        0 => {
            let nrom = nrom::Nrom::from(&rom)?;
            Ok(Box::new(nrom))
        },
        1 => {
            let mmc1 = mmc1::Mmc1::from(&rom)?;
            Ok(Box::new(mmc1))
        },
        2 => {
            let uxrom = uxrom::Uxrom::from(&rom)?;
            Ok(Box::new(uxrom))
        },
        _ => Err(String::from("Not implemented yet"))
    }
}
```

Using this model, the emulator works great! Except when trying to serialize this `Box<dyn Mapper>`.
Serde does not know how to serialize this smart pointer. There are some crates to help ([https://github.com/dtolnay/erased-serde](https://github.com/dtolnay/erased-serde))
but deserialization becomes also complicated. The type of the mapper needs to be included in the serialized data
in order to deserialize it to the correct structure, but `Box<dyn Mapper>` erases the type.

## Second iteration: Use enumeration instead

The mapper is determined at runtime, but it is not that dynamic. In reality, I implemented the code for N mappers
so there are only N variant of mappers. Using Rust enumerations to hold these variant, I can use serde to serialize
the mapper: [https://serde.rs/enum-representations.html](https://serde.rs/enum-representations.html).

As a bonus, the type is not erased and the mapper struct can be retrieved using pattern matching. It is also not
necessary to use a trait anymore. The implementation becomes:

```rust

#[derive(Serialize, Deserialize)]
pub enum MapperType {
    Nrom(nrom::Nrom),
    Uxrom(uxrom::Uxrom),
    Mmc1(mmc1::Mmc1),
}

impl MapperType {
    pub fn read_prg(&self, addr: usize) -> u8 {
        match *self {
            MapperType::Nrom(ref x) => x.read_prg(addr),
            MapperType::Uxrom(ref x) => x.read_prg(addr),
            MapperType::Mmc1(ref x) => x.read_prg(addr),
        }
    }

    pub fn write_prg(&mut self, addr: usize, value: u8) {
        match *self {
            MapperType::Nrom(ref mut x) => x.write_prg(addr, value),
            MapperType::Uxrom(ref mut x) => x.write_prg(addr, value),
            MapperType::Mmc1(ref mut x) => x.write_prg(addr, value),
        }

    }

    // Read/Write pattern tables. Sometimes, it is RAM instead of ROM
    pub fn read_chr(&self, addr: usize) -> u8 {
        match *self {
            MapperType::Nrom(ref x) => x.read_chr(addr),
            MapperType::Uxrom(ref x) => x.read_chr(addr),
            MapperType::Mmc1(ref x) => x.read_chr(addr),
        }
    }
    
    pub fn write_chr(&mut self, addr: usize, value: u8) {
        match *self {
            MapperType::Nrom(ref mut x) => x.write_chr(addr, value),
            MapperType::Uxrom(ref mut x) => x.write_chr(addr, value),
            MapperType::Mmc1(ref mut x) => x.write_chr(addr, value),
        }
    }

    pub fn get_chr(&self, idx: usize) -> &[u8] {
        match *self {
            MapperType::Nrom(ref x) => x.get_chr(idx),
            MapperType::Uxrom(ref x) => x.get_chr(idx),
            MapperType::Mmc1(ref x) => x.get_chr(idx),
        }
    }


    
    pub fn get_mirroring(&self) -> Mirroring {
        match *self {
            MapperType::Nrom(ref x) => x.get_mirroring(),
            MapperType::Uxrom(ref x) => x.get_mirroring(),
            MapperType::Mmc1(ref x) => x.get_mirroring(),
        }
    }
}

pub fn create_mapper(rom: &rom::INesFile) -> Result<MapperType, String> {

    let mapper_id = rom.get_mapper_id();

    println!("MAPPER ID: {}", mapper_id);
    match mapper_id {
        0 => {
            let nrom = nrom::Nrom::from(&rom)?;
            Ok(MapperType::Nrom(nrom))
        },
        1 => {
            let mmc1 = mmc1::Mmc1::from(&rom)?;
            Ok(MapperType::Mmc1(mmc1))
        },
        2 => {
            let uxrom = uxrom::Uxrom::from(&rom)?;
            Ok(MapperType::Uxrom(uxrom))
        },
        _ => Err(String::from("Not implemented yet"))
    }
}
```

Using this code, serialization and deserialization work! On the other hand, it created a bunch of extra-code.
Whenever you want to add a new variant, you will have to add it to all the pattern matching code...

## Iteration 3: Use macros to reduce boilerplate code

Macros are the perfect fit to fix this inconvenience. A macro will generate the code for you. All you need
to do is to write it (easier said than done :D).

The code becomes:
```rust

macro_rules! mapper_types {
    ($($name:ident: ($id: expr, $mapper:ty)),+) => {
        #[derive(Serialize, Deserialize)]
        pub enum MapperType {
            $(
                $name($mapper)
            ),+
        }

        impl MapperType {

            pub fn read_prg(&self, addr: usize) -> u8 {
                match *self {
                    $(
                        MapperType::$name(ref x) => x.read_prg(addr),
                        )+
                }
            }

            pub fn write_prg(&mut self, addr: usize, value: u8) {
                match *self {
                    $(
                        MapperType::$name(ref mut x) => x.write_prg(addr, value),
                        )+
                }
            }

            // Read/Write pattern tables. Sometimes, it is RAM instead of ROM
            pub fn read_chr(&self, addr: usize) -> u8 {
                match *self {
                    $(
                        MapperType::$name(ref x) => x.read_chr(addr),
                        )+
                }
            }

            pub fn write_chr(&mut self, addr: usize, value: u8) {
                match *self {
                    $(
                        MapperType::$name(ref mut x) => x.write_chr(addr, value),
                        )+
                }
            }

            pub fn get_chr(&self, idx: usize) -> &[u8] {
                match *self {
                    $(
                        MapperType::$name(ref x) => x.get_chr(idx),
                        )+
                }
            }

            pub fn get_mirroring(&self) -> Mirroring {
                match *self {
                    $(
                        MapperType::$name(ref x) => x.get_mirroring(),
                        )+
                }
            }

        }


        pub fn create_mapper(rom: &rom::INesFile) -> Result<MapperType, String> {
            let mapper_id = rom.get_mapper_id();
            match mapper_id {
                $(
                    $id => {
                        let x = <$mapper>::from(&rom).unwrap();
                        Ok(MapperType::$name(x))
                    },
                    )+
                    _ => Err(String::from("Not implemented yet"))
            }
        }
    }
}

mapper_types!(
    Nrom: (0, nrom::Nrom),
    Mmc1: (1, mmc1::Mmc1),
    Uxrom: (2, uxrom::Uxrom)
);
```

I admit, it is still a lot to swallow. However, the only thing to do if you want to add a new variant is to
add a line to `mapper_types!`. If you compare to the previous iteration, where at least 6 methods had to be
changed manually, that is a huge improvement.

## A final word

In my code, changing `Box<Trait>` for `enum` delegation solved the serialization issue in a satisfactory
way. However, as everything in programming, this solution has its trade-offs. [This thread](https://users.rust-lang.org/t/performance-implications-of-box-trait-vs-enum-delegation/11957) on the rust
forum is really informative:
- An enum is as big as its biggest variant
- Enums keep data on the stack
- "Enums represent a closed set of type, trait objects represent an open set."

For my use case, using an enumeration instead of trait objects for polymorphism really
solved various issues I had. However, enumerations are hard-coded, so if you are
writing a library it makes sense to use traits for polymorphism instead.
