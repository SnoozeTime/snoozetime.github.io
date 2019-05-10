---
layout: post
title: "Object picking with Vulkan: Select your game objects by mouse click!"
date: 2019-05-02
---

Object picking is a technique used to select an object in a scene from a click of the mouse.
For example, it can be used in a RTS to select a unit. It can also be used in a game engine editor
to select an object to modify.

There are several ways to do object picking. If you have an existing physics engine, you can cast
a ray from the mouse position. Unfortunately, I do not have a physics engine yet so I'll talk about
another method, which is using the GPU.

![Object picking in action]({{ site.url }}/assets/obj_picking.gif)

## The concept: Pixel-perfect object selection using the GPU

When rendering a scene to the screen, the GPU is already doing all the calculations necessary to
determine what color each pixel should have. Depth testing in particular will discard the fragments
that can not be visible. If you click on a pixel located a (x, y), the color of this pixel is actually
specific to a game object.

The idea of this technique is to use a unique color for each object in the scene. Then, when clicking on
a pixel, we can find what object is it by getting the pixel's color. Of course, you don't want to
actually render this to the screen. The pixel information will be available in a buffer but will
not be presented to the screen.

The problem with that technique is that you need to render the scene to an image a second time. However, object picking is only done when the user click on a mouse button so this performance penalty will only occur at that time.

In drawing, this is your original scene with a few objects. Each object will have a unique color assigned. The rendered image will look like:

## Vulkan implementation

There are already a lot of examples on the Web about opengl. This time, I will use vulkano
(Rust Vulkan library) for the implementation. The scene will contain a few 2D shapes and depth
testing is enabled so some shapes will appear in front of other shapes. This code will be based
on the triangle example. I'll make it available on github instead of copy-pasting the code here
as I used to do because there is a lot of boilerplate :).

### The shaders

The first vertex and fragment shaders are from the vulkano examples, except that I accept a
vec3 to include the depth and I want to set a different color for each shape.

```glsl
#version 450
layout(location = 0) in vec3 position;
layout(location = 1) in vec3 color;

layout(location = 0) out vec3 out_color;

void main() {
    gl_Position = vec4(position, 1.0);
    out_color = color;
}
```

Then, each fragment will get its color from the vertex shader. A push constant will be used to indicate whether an object is selected. This is a visual way of confirming the code work instead of printing to console.
```glsl
#version 450

layout(location = 0) in vec3 color;
layout(location = 0) out vec4 f_color;

layout (push_constant) uniform PushConstants {
    int isSelected;    
} pushConstants;

void main() {
    if (pushConstants.isSelected == 0) {
        f_color = vec4(frag_color, 1.0);
    } else {
        f_color = vec4(1.0, 1.0, 1.0, 1.0);
    }
}
```

For object picking, we want to encode the object ID as a color. For example, I could have two
blue triangles. They would use the same vertex data (position and color) but they won't have
the same object ID. Clearly, we cannot use the same shaders to implement that idea. Instead,
I will use shaders that are a bit different. They should use the same vertex data as I do not
want to duplicate the amount of data uploaded to GPU memory.

```glsl
#version 450
layout(location = 0) in vec3 position;
layout(location = 1) in vec3 color;

layout(location = 0) out vec4 out_color;

// Magic happens here.
layout(push_constant) uniform PushConstants {
        vec4 color;
} pushConstants;

void main() {
    gl_Position = vec4(position, 1.0);
    out_color = uniforms.color;
}
```

Instead of getting the color from the vertices, I get it from a push constant. For each object, we can push different data using the push constants. 

The fragment shader changes a bit as I use a vec4 now. The reason is that I want to use the value `vec4(0.0, 0.0, 0.0, 0.0)` as absence of object.

```glsl
#version 450

layout(location = 0) in vec3 color;
layout(location = 0) out vec4 f_color;

void main() {
    f_color = color;
}
```


### Adding depth testing to our triangle example
A few things are necessary to do to enable depth testing. In summary:
- Enable depth testing in the pipeline
- Add a depth attachment to the render pass
- Add a depth buffer to the framebuffer
- Provide clear values for drawing. In vulkan, depth ranges from 0.0 to 1.0, 1.0 being the far plane.

This link provides more information: [vulkan-tutorial](https://vulkan-tutorial.com/Depth_buffering).


### Render scene to an image


Hum, this is going to be more complicated. This process will be done independently from
the real rendering. The object picking is done only when the user click on the mouse and
does not alter what is rendered to the screen.

As we saw before, the shaders for object picking are not the same than for normal scene rendering so I will need to create a new pipeline for this.
Then, when beginning the render pass, I cannot touch the swapchain images as they are going to be presented to the screen so I need to create new 
images only for object picking, where color information will be written to.

Like the triangle example, there is a lot of preparation to do before issuing the actual commands
to the GPU:
- Create the image that will contain color information;
- Create the render pass: I just need a single pass that writes to a color attachment;
- Create the pipeline with the corresponding shaders;
- Create the framebuffer that will be used in the command buffer.

That's my image:

```rust
        // Create the image to which we are going to render to. This
        // is not a swapchain image as we do not render to screen.
        let image_usage = ImageUsage {
            transfer_source: true, // This is necessary to copy to external buffer
            .. ImageUsage::none()
        };

        let image = AttachmentImage::with_usage(
            queue.device().clone(),
            dimensions,
            Format::R8G8B8A8Unorm, // simple format for encoding the ID as a color
            image_usage).unwrap();

```

That's my render pass:

```rust
        let render_pass = Arc::new(vulkano::single_pass_renderpass!(
                queue.device().clone(),
                attachments: {
                    color: {
                        load: Clear,
                        store: Store,
                        format: Format::R8G8B8A8Unorm,
                        samples: 1,
                    },
                    depth: {
                        load: Clear,
                        store: DontCare,
                        format: Format::D16Unorm,
                        samples: 1,
                    }
                },
                pass: {
                    color: [color],
                    depth_stencil: {depth}
                }
        ).unwrap());


```


That's my pipeline:

```rust
        let vs = pick_vs::Shader::load(queue.device().clone()).unwrap();
        let fs = pick_fs::Shader::load(queue.device().clone()).unwrap();
        let pipeline = Arc::new(GraphicsPipeline::start()
                                .vertex_input_single_buffer::<Vertex>()
                                .vertex_shader(vs.main_entry_point(), ())
                                .triangle_list()
                                .viewports_dynamic_scissors_irrelevant(1)
                                .depth_stencil_simple_depth()
                                .viewports(iter::once(Viewport {
                                    origin: [0.0, 0.0],
                                    dimensions: [dimensions[0] as f32, dimensions[1] as f32],
                                    depth_range: 0.0 .. 1.0,
                                }))
                                .fragment_shader(fs.main_entry_point(), ())
                                .render_pass(Subpass::from(render_pass.clone(), 0).unwrap())
                                .build(queue.device().clone())
                                .unwrap());
```

And this is my framebuffer:

```rust
        let depth_buffer = AttachmentImage::transient(
            queue.device().clone(),
            dimensions,
            Format::D16Unorm).unwrap();

       // Use our custom image in the framebuffer.
        let framebuffer = Arc::new(Framebuffer::start(render_pass.clone())
                                   .add(image.clone()).unwrap()
                                   .add(depth_buffer.clone()).unwrap()
                                   .build().unwrap());


```

Nothing too fancy here!

Then, when triggering the object picking functionality:
- Create a new command buffer builder;
- Start a new render pass with the previous framebuffer;
- for each game object, encode the ID as push constants;
- Create a draw call for the game object using the previous push constants;
- Finish render pass and execute the command buffer.

I also need to wait for the GPU to finish the operation before reading from the image.

### ID encoding

For this code, I used a simple color encoding. Opaque colors are objects. Transparent colors
mean no object. Then the ID is converted to RGB with the following pseudo-code.

```
r = (id & 0xFF) / 255
g = ((id >> 8) & 0xFF) / 255
b = ((id >> 16) & 0xFF) / 255
```

The division by 255 is to get a value between 0 and 1. The ID can be retrieved from a color by
inverting these equations. By the way, choosing the good format for the image is important here.
We chose R8G8B8A8... so that the bytes we get in the buffer will actually correspond to 8-bit RGB.

### How to transfer back to a CPU accessible buffer

The image I created now holds the color information. Unfortunately I cannot access
it directly. I need to transfer it to a `CPU accessible` buffer first. This is done
in two steps: first, create the buffer which has the same size than the image, then
issue a command to copy from the image to the buffer.

```rust
        // That is the CPU accessible buffer to which we'll transfer the image content
        // so that we can read the data. It should be as large as 4 the number of pixels (because we
        // store rgba value, so 4 time u8)
        let buf = CpuAccessibleBuffer::from_iter(
            queue.device().clone(), BufferUsage::all(),
            (0 .. dimensions[0] * dimensions[1] * 4).map(|_| 0u8)).expect("Failed to create buffer");

        // .... A bit after having issued draw commands
        command_buffer_builder = command_buffer_builder
            .copy_image_to_buffer(self.image.clone(), self.buf.clone())
            .unwrap();

        let command_buffer = command_buffer_builder.build().unwrap();

        // Execute command buffer and wait for it to finish.
        command_buffer
            .execute(self.queue.clone())
            .unwrap()
            .then_signal_fence_and_flush()
            .unwrap()
            .wait(None)
            .unwrap();


```

The vulkano guide shows how to do it: [vulkano guide](https://vulkano.rs/guide/image-export).
Also there!

### Extract ID from the CPU accessible buffer

The image with the objects'ID has been transferred to a buffer, so the last step is to get back the entity from the position of the mouse. Winit provides events to detect mouse click and mouse position change so I won't talk in details about that.

Let's say we have x and y from Winit. These are in logical coordinates, so first, they need to be converted to physical coordinates by multiplying by the hidpi factor. 

```rust
let x = mouse_x * surface.window().get_hidpi_factor();
```

Then, be mindful that the pixel information is stored as R8G8B8A8 in the buffer. For each pixels, there are four u8 values (Red, Green, Blue and A for transparency). That gives us the index: 4 * (line * width) + column. Mouse's y position is the line, and mouse's x position is the column. 

Then, by inverting the encoding of before, we get the selected entity.

```rust
    fn get_entity_id(r: u8, g: u8, b: u8, a: u8) -> Option<usize> {
        if a == 0 {
            None
        } else {
            Some((r as usize) | (g as usize) << 8 | (b as usize) << 16)
        }
    }
```

## Finally!

This was an easy way of doing object picking using the GPU. It's not particularly performant as the scene is drawn again. It is also not part of the main rendering pipeline as this is an on-demand feature. For a small number of object, the current implementation does the trick.

The code is available on my github so feel free to use it as it is.
