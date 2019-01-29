---
layout: post
title: "Scripting behaviour in a game engine - A small example"
date: 2019-01-29
---
Hello there, today I'll write a bit about scripting in game engine. Usually, game engines are
written in low-level languages to run as fast as possible. It is a bit inconvenient for fast
prototyping so on top of that, scripts are use to defined the gameplay. Think c# in Unity for
example.

I've always been interested by this topic. In theory, you can separate the real performance-critical part of your engine (physics engine for example) from the gameplay parts. Different
people can work independently. An engineer will optimize the renderer while another will implement a quest system for the game.

More often than not, people will answer negatively when you ask how to implement scripting in a game engine:
- Should you implement your own game engine? Of course not, use Unity
- Should you create your own GUI library? Why are you wasting you time? Use unity.
But what the heck, we are here to learn and have fun so let's get started!

## The scripting language

Lua is used a lot for scripting language. It is easy to integrate with C and has relatively good performance compared to other dynamically typed languages. I am coding in Rust, and fortunately,
Kyren from ChuckleFish has done most of the hard work to provide Lua integration in Rust. The module is [rlua](https://github.com/kyren/rlua).

## A simple example

Just playing with rlua examples, you can expose some data defined in Rust, modify
it with Lua, and get it back to Rust.

```rust
use rlua::{Function, Lua, MetaMethod, Result, UserData, UserDataMethods, Variadic};

const CODE: &'static str = r#"
    position = position*2
"#;

#[derive(Copy, Clone, Debug)]
struct Vec2(f32, f32);

impl UserData for Vec2 {

    fn add_methods<'lua, M: UserDataMethods<'lua, Self>>(methods: &mut M) {
        methods.add_method("magnitude", |_, vec, ()| {
            let mag_squared = vec.0 * vec.0 + vec.1 * vec.1;
            Ok(mag_squared.sqrt())
        });

        methods.add_meta_function(MetaMethod::Add, |_, (vec1, vec2): (Vec2, Vec2)| {
            Ok(Vec2(vec1.0 + vec2.0, vec1.1 + vec2.1))
        });

        methods.add_meta_function(MetaMethod::Mul, |_, (vec1, scalar): (Vec2, f32)| {
            Ok(Vec2(vec1.0 * scalar, vec1.1 * scalar))
        });
    }

}

fn main() -> Result<()> {

    let lua = Lua::new();
    let mut v = Vec2(1.0, 0.5);
    lua.context(|lua_ctx| {
        let globals = lua_ctx.globals();
        globals.set("position", v)?;
        dbg!(lua_ctx.load(CODE).eval::<()>()?);
        v = globals.get::<_, Vec2>("position")?;

        Ok(())
    })?;

    dbg!(v);
    Ok(())
}
```

The data is just a simple Rust `struct`. Methods for this structure are exposed to Lua via the 
UserData trait. Now, let's improve this a bit:
- I want to be able to load from a script, not from some hard-coded string.
- I want to loop and call my script's method at each iteration.
- I want to load code in the lua context only once.

This is the function to load the script. Nothing too surprising here, but notice the use of
`<P: AsRef<Path>>` that allows to convert the function's parameter to a `Path`.

```rust
fn load_script<P: AsRef<Path>>(path: P) -> Result<String, Box<Error>> {
    let mut f = File::open(path).unwrap();
    let mut content: String = String::new();
    f.read_to_string(&mut content)?;
    Ok(content)
}
```

Then, the main function will be changed to:

```rust
fn main() -> rlua::Result<()> {

    let code = load_script("script.lua".to_string()).unwrap();
    let lua = Lua::new();
    let mut v = Vec2(1.0, 0.5);
    
    // Set up context
    lua.context(|lua_ctx| {
        let globals = lua_ctx.globals();
        globals.set("position", v)?;
        let vec2_constructor = lua_ctx.create_function(|_, (x, y): (f32, f32)| Ok(Vec2(x, y)))?;
        globals.set("vec2", vec2_constructor)?;

        dbg!(lua_ctx.load(&code).eval::<()>()?);
        Ok(())
    })?;

    loop {
        lua.context(|lua_ctx| {
            let globals = lua_ctx.globals();
            v = globals.get::<_, Vec2>("position")?;
            lua_ctx.load("update()").eval::<()>()?;
            Ok(())
        })?;

        dbg!(v);
        std::thread::sleep(std::time::Duration::from_millis(2000));
    }
    Ok(())
}
```

The Lua context is persistent, so the data I load in a `lua.context` block will be available in another block. The other subtleties (not so subtle though) here is that a function named `update` will be called at every loop iteration. This function is actually defined in my  `script.lua` file. I guess defining conventions for Lua scripts cannot hurt.

```lua
function update()
        position = position * 2
end
```

If you run this code, `v` will double at each iteration and will be printed to the console. You
can also change the code and run the program again to alter the behaviour without having to
recompile! Bye-bye long compilation time :D

## Hot-reload anyone?

It looks good, but why not adding hot-reload? I should be able to modify the script and my
engine should reload the code.

### Monitor for changes

To begin with, I'll do it the hacky way, on Linux. The command `stat -c '%y' script.lua` will tell me the last time the file was modified. If I can monitor this in a separate thread, I
will be able to know when I should reload my code.

The code that does the magic is:

```rust
    let (sender, receiver) = channel();

    thread::spawn(move|| {
        let mut cmd =  Command::new("stat");
        cmd.args(&["-c", "'%y'", "script.lua"]);
        let d = cmd.output().unwrap();
        
        let mut last_stat = String::from_utf8(d.stdout).unwrap();

        loop {
            let new_stat = String::from_utf8(cmd.output().unwrap().stdout).unwrap();
            if new_stat != last_stat {
                last_stat = new_stat;
                sender.send(true).unwrap();
            }

            std::thread::sleep(std::time::Duration::from_millis(1000));
        }
    });

```
It will just check the output of `stat` in another thread and send an event if the output differs from last time. Then, in the main loop, we can just check the `receiver`.

```rust
if let Ok(_) = receiver.try_recv() {
    println!("Reloading");
    eval_script(&lua, "script.lua".to_owned());
}
```
`eval_script` is just some code I extracted from `main` to read a file and evaluate its code.

It works, but I don't feel so good about this solution. For example, just saving without modifying on vim will reload the script. Fortunately, watching for file modification is a common problem so there is a cross-platform [crate for that](https://github.com/passcod/notify).


## A lot of work

Writing this small prototype has been a lot of fun. In reality, I expect a lot of repetitive codes as you need to specify the API that should be available in Lua file. There will be probably
an impact on performance that need to be measured.

Again, Kyren sums it up nicely:

> In the meantime, think really really hard before you add a scripting layer to your game engine. The problem is, I LOVE scripting layers in game engines (for modability and many other reasons), so I do this anyway, but it is not a decision to be taken lightly and it can eat up a lot of time and effort. 
