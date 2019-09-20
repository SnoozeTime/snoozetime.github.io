---
layout: post
title: "Favorite crates: 2019 edition"
date: 2019-09-23
---

It is time for the favorite Rust crates, 2019 edition!
This post will focus mostly on Web technologies as I've been using Rust more and more in my daily work (ssh that's a secret :D).

Logging with `tracing`
========================

Formerly part of the `tokio` crates, `tracing` provides a way to instrument your code to collect structure information about what
is happening. This can be used for logging or measuring timing for example.

Here is an example, courtesy of the `tracing` github repository.

```rust
#![deny(rust_2018_idioms)]
use tracing::{debug, error, info, span, trace, warn, Level};

use std::{error::Error, fmt};

#[tracing::instrument]
pub fn shave(yak: usize) -> Result<(), Box<dyn Error + 'static>> {
    debug!(
        message = "hello! I'm gonna shave a yak.",
        excitement = "yay!"
    );
    if yak == 3 {
        warn!(target: "yak_events", "could not locate yak!");
        Err(ShaveError::new(yak, YakError::new("could not locate yak")))?;
    } else {
        trace!(target: "yak_events", "yak shaved successfully");
    }
    Ok(())
}

pub fn shave_all(yaks: usize) -> usize {
    let span = span!(Level::TRACE, "shaving_yaks", yaks_to_shave = yaks);
    let _enter = span.enter();

    info!("shaving yaks");

    let mut num_shaved = 0;
    for yak in 1..=yaks {
        let res = shave(yak);
        trace!(target: "yak_events", yak, shaved = res.is_ok());

        if let Err(ref error) = res {
            error!(
                message = "failed to shave yak!",
                yak,
                error = error.as_ref()
            );
        } else {
            num_shaved += 1;
        }

        trace!(target: "yak_events", yaks_shaved = num_shaved);
    }

    num_shaved
}

#[derive(Debug)]
struct ShaveError {
    source: Box<dyn Error + 'static>,
    yak: usize,
}

impl fmt::Display for ShaveError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "shaving yak #{} failed!", self.yak)
    }
}

impl Error for ShaveError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        Some(self.source.as_ref())
    }
}

impl ShaveError {
    fn new(yak: usize, source: impl Into<Box<dyn Error + 'static>>) -> Self {
        Self {
            source: source.into(),
            yak,
        }
    }
}

#[derive(Debug)]
struct YakError {
    description: &'static str,
}

impl fmt::Display for YakError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.description)
    }
}

impl Error for YakError {}

impl YakError {
    fn new(description: &'static str) -> Self {
        Self { description }
    }
}
```

Instrumentation (`span`, `info`, ...) will send events that are handled by a subscriber. In this code, the subscriber just log the event to the
console, but some subscribers such as [tracing-timing](https://docs.rs/tracing-timing/0.2.12/tracing_timing/) will provide information
about event timing.

Currently, I mostly use the provided `FmtSubscriber` but I might in the future implement my own to push events to third-party services such
as ElasticSearch.

Error handling with `Snafu`
============================

I really like Rust explicit error handling but sometimes I need to write a lot of boilerplates to convert errors from
other crate to my application error. Of course, one solution is to convert everything to `Box<Error>` but `Snafu` provides
an easy way to get started with clean error handling from the start of a new project.

Let's take a look at an example, heavily inspired by [this great article by `BurntSushi`](https://blog.burntsushi.net/rust-error-handling/#standard-library-traits-used-for-error-handling).

```rust

use snafu::{ResultExt, Snafu};

/// Our custom error. Here, no need to implement Display, Error and so on.
/// Everything is handled by the proc macro
#[derive(Debug, Snafu)]
enum CliError {
    #[snafu(display("Cannot read file: {}", filename))]
    CannotReadFile { source: std::io::Error, filename: String },

    #[snafu(display("Cannot read to string: {}", filename))]
    CannotReadToString { source: std::io::Error, filename: String },

    // the ParseIntError will already contain the string value
    #[snafu(display("Cannot convert string to integer"))]
    CannotConvertToInt { source: std::num::ParseIntError },

    // Can also create variant without a source
    #[snafu(display("Input integer is too small: got {}, expected large than 10", value))]
    IntTooSmall { value: u8 },
}

```

This is all I need to create a custom error. The `source` field is a bit of a magic field for Snafu. It 
is basically the underlying error. A function that returns a result with this underlying error can 
be convert to my custom error by adding some context information.

For example,
```rust
fn file_double(file_path: &str) -> Result<i32, CliError> {
    let mut file = File::open(file_path).context(CannotReadFile { filename: String::from(file_path) })?;
    let mut contents = String::new();
    file.read_to_string(&mut contents).context(CannotReadToString { filename: String::from(file_path)})?;
    let n: u8 = contents.trim().parse().context(CannotConvertToInt {})?;

    // ensure is a macro that will return the error is a condition is not satisfied
    ensure!(n >= 10, IntTooSmall { value: n });

    Ok(2 * n)
}

```

It is a bit more verbose than the version with `std::convert::From`. However, you have the possibility to add more
context information to the error which would help you create more precise error messages.

I tried the traditional way to create Errors with the standard library. I also tried the `Failure` crate which confused
me with different types :'). So far, `Snafu` is really easy to get started, reduce a lot of boilerplate and helps providing
precise and specific error messages.

Wasm outside the web browser with `wasmer-runtime`
================================================

For some reason I am super fascinated by embedding interpreters within my Rust code. I have tried Lua (see here). I have
also experience rust-cpython with success but what irks me is the lack of static typing. I know, some people use interpreters
so that they can quickly create scripts with having to bother with a compiler and its annoying error messages. 
For me, static typing equates to safety and sleep without worry, so I was delighted when I heard about `wasmer-runtime` which
allows me to run pre-compiled Wasm modules within my Rust code.

Somebody already wrote a really complete guide on how to do it so you really should take a loot at [https://wiredforge.com/blog/wasmer-plugin-pt-1](https://wiredforge.com/blog/wasmer-plugin-pt-1).
