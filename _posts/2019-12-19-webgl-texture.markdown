---
layout: post
title: "How to load textures in Rust/WebGl"
date: 2019-12-19
---

All the work done in Wasm/Rust + WebGl makes it possible to write your game in Rust
and still have it working in the web browser. Not all the crates are available. Notably,
multithreading is not supported so ECS crates such as `specs` and `legion` are a bit restricted.

For rendering, WebGl2 provides an API close to modern opengl. The way to load assets however is specific to the web platform so I will provide some code here to help you load a texture from a web server. The code was adapted from the Mozilla documentation [here](https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API/Tutorial/Using_textures_in_WebGL).

```rust

use std::rc::Rc;
use wasm_bindgen::prelude::*;
use wasm_bindgen::JsCast;
use web_sys::console;
use web_sys::{
    HtmlImageElement, WebGl2RenderingContext, WebGlBuffer, WebGlProgram, WebGlShader, WebGlTexture,
};

/// Load a new texture :)
///
/// To do so, the texture image needs to be loaded from the server first. This is done
/// asynchronously in Javascript so we can upload the image to the GPU only after the image
/// is received on the client.
///
/// One trick is to create first the texture with one single blue pixel, then add a callback to
/// load the texture when the image is loaded. See here: https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API/Tutorial/Using_textures_in_WebGL
pub fn load_texture(
    gl: &WebGl2RenderingContext,
    img_src: &str,
) -> Result<Rc<WebGlTexture>, JsValue> {
    let texture = gl.create_texture().expect("Cannot create gl texture");
    gl.bind_texture(WebGl2RenderingContext::TEXTURE_2D, Some(&texture));
    let level = 0;
    let internal_format = WebGl2RenderingContext::RGBA;
    let width = 1;
    let height = 1;
    let border = 0;
    let src_format = WebGl2RenderingContext::RGBA;
    let src_type = WebGl2RenderingContext::UNSIGNED_BYTE;

    // Now upload single pixel.
    let pixel: [u8; 4] = [0, 0, 255, 255];
    gl.tex_image_2d_with_i32_and_i32_and_i32_and_format_and_type_and_opt_u8_array(
        WebGl2RenderingContext::TEXTURE_2D,
        level,
        internal_format as i32,
        width,
        height,
        border,
        src_format,
        src_type,
        Some(&pixel),
    )?;

    let img = HtmlImageElement::new().unwrap();
    img.set_cross_origin(Some(""));

    let imgrc = Rc::new(img);

    let texture = Rc::new(texture);

    {
        let img = imgrc.clone();
        let texture = texture.clone();
        let gl = Rc::new(gl.clone());
        let a = Closure::wrap(Box::new(move || {
            gl.bind_texture(WebGl2RenderingContext::TEXTURE_2D, Some(&texture));

            if let Err(e) = gl.tex_image_2d_with_u32_and_u32_and_html_image_element(
                WebGl2RenderingContext::TEXTURE_2D,
                level,
                internal_format as i32,
                src_format,
                src_type,
                &img,
            ) {
                // TODO better error handling...
                console::log_1(&e);
                return;
            }

            // different from webgl1 where we need the pic to be power of 2
            gl.generate_mipmap(WebGl2RenderingContext::TEXTURE_2D);
        }) as Box<dyn FnMut()>);
        imgrc.set_onload(Some(a.as_ref().unchecked_ref()));

        // Normally we'd store the handle to later get dropped at an appropriate
        // time but for now we want it to be a global handler so we use the
        // forget method to drop it without invalidating the closure. Note that
        // this is leaking memory in Rust, so this should be done judiciously!
        a.forget();
    }

    imgrc.set_src(img_src);

    Ok(texture)
}
```

The trick
=========

Use the HTML Image element to load from an URL and do the decoding. Then, the WebGl2Rendering context can use the content of the image element as a texture. Image download is done asynchronously. First, a texture is created with a single blue pixel. Then, a callback `onload` will upload the correct texture instead of the pixel.

During development, I often use some javascript server to create my web UI (Vuejs) and another rust server to serve the static files. It is problematic because the web browser (WebGl) will block the image loading because of [CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS). To bypass this problem, your asset server can allow any origin.

Mandatory warp sample:
```rust
use warp::Filter;

fn main() {
    pretty_env_logger::init();

    let cors = warp::cors().allow_any_origin();
    let assets = warp::fs::dir("./assets/").with(cors);

    warp::serve(assets).run(([127, 0, 0, 1], 3031));
}
```

Another detail that is important. The `img` element will not send pre-flight requests by default, so the line `img.set_cross_origin(Some(""));` is mandatory.


Using with Rust
===============

The asynchronous aspect of the texture loading means that we need to use javascript callback to do an action once the image is loaded. The way to do it with Rust is to use the Closure struct. The syntax is a bit funky so I'll redirect you to the wasm_bindgen examples in the [github repository](https://github.com/rustwasm/wasm-bindgen). 

Another important point
=======================

I am using WebGl2 because it is closer to modern opengl. If you want to use webgl1 for compatibility reasons, you will need to generate the mipmap a bit differently. See the Mozilla documentation.

Make sure you use `WebGl2RenderingContext` and not `WebGlRenderingContext`.

That's all folks!
