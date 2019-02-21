---
title: "Protocol framing with Tokio and MsgPack"
layout: "post"
date: 2019-02-20
---

I often use TCP for communication within a network of systems. Let's just use the example
of a online game. The client, that is the game that is running on your own machine, needs
to get the latest game update from the server, which is located on my environment. The
client also needs to send updates to the server. For example, if your character moves and shoot,
this information need to be forwarded to the server.

Here, I won't talk about problematics such as who hold the true state between the server and client.
I will just show an easy way to send messages across the network.

I'll show how to solve common problems that are encountered when sending data across the network:
- How to abstract away the exchange of bytes:
  TCP allows two hosts to exchange stream of bytes. When reading from a TCP socket, you might not
  receive at once enough data to recreate the original logical message, so you need to accumulate
  the received bytes in a buffer until there are enough to unpack your message.
- How to send different messages with different fields across the network.

## From a stream of bytes to a stream of frames

Accumulating and decoding messages from a buffer is not fun. I'd rather receive a complete message
or nothing whenever I read from a socket. To do so, you need to add some structure to the stream
of bytes. For example, you can decide that each message is finished with CRLF. Then, you read bytes until
you find '\r\n' and here you are, one complete message. This is called message framing.

![Converting a stream of bytes to a stream of frames]({{ site.url }}/assets/from_bytes_to_frames.PNG)

### Basics with Tokio

I'll use the `Tokio` crate for creating the server and client of my application. 'Tokio' introduces
very quickly the concept of framing in its example. See the following striped down example, from [`chat.rs`](https://github.com/tokio-rs/tokio/blob/master/examples/chat.rs).

```rust

impl Stream for Lines {
    type Item = BytesMut;
    type Error = io::Error;


    fn poll(&mut self) -> Poll<Option<Self::Item>, Self::Error> {

        // First, read any new data that might have been received off the socket
        let sock_closed = self.fill_read_buf()?.is_ready();

        // Now, try finding lines
        let pos = self.rd.windows(2).enumerate()
            .find(|&(_, bytes)| bytes == b"\r\n")
            .map(|(i, _)| i);

        if let Some(pos) = pos {
            // Remove the line from the read buffer and set it to `line`.
            let mut line = self.rd.split_to(pos + 2);

            // Drop the trailing \r\n
            line.split_off(pos);

            // Return the line
            return Ok(Async::Ready(Some(line)));
        }

        if sock_closed {
            Ok(Async::Ready(None))
        } else {
            Ok(Async::NotReady)
        }
    }
}
```

This is what happens:
1. Data available on the socket is added to an internal buffer `rd` in `self.fill_read_buff`.
2. If there is `\r\n` in the buffer, split it and return the data before.
3. If not, tell the rest of the code that no data is available yet.

`Lines` is wrapping a `TcpStream`. Instead of polling the TCP socket directly, the chat application
is polling the `Lines` stream that will internally get the data from the socket.

```rust
while let Async::Ready(line) = self.lines.poll()? {
    println!("Received line ({:?}) : {:?}", self.name, line);
}
```

Splitting messages per line is super basic but has several pitfalls. The size of the message is unknown
until you reach CRLF so you cannot allocate memory upfront for the message. If the separator is present
in the message data, then you split the message in two parts or more. Bernstein proposed an encoding
of a string that is very easy to parse and generate: [netstring](http://cr.yp.to/proto/netstrings.txt). I will use it
in the rest of this post.

### Writing a netstring code with Tokio

Implementing `Stream` worked great to decode incoming data, but it does not handle sending the same
kind of data to the other party. To do so, `Tokio` provides the `Framed` structure, that wraps
a socket and provides a stream to read from, and a sink to send data to. All the `Framed` structure
needs is a stream of bytes and a way (a codec) to encode/decode bytes to your choice of encoding. In the online
[documentation](https://tokio.rs/docs/going-deeper/frames/), the example is using new lines as encoding.

The codec needs to implement the Encoder and Decoder traits. Encoding a netstring from a string is easy:

```rust
/// Netstring is an easy way to frame data on TCP.
/// http://cr.yp.to/proto/netstrings.txt
pub struct NetstringCodec {
    state: ParserState,

    current_length: usize,

    /// Max length for the string. This is to avoid attacks by sending
    /// packets that are too large.
    max_length: usize,

    /// Will disconnect the peer on error if this is true.
    disconnect_on_error: bool,
}

impl Encoder for NetstringCodec {

    type Item = Vec<u8>;
    type Error = io::Error;

    fn encode(&mut self, item: Vec<u8>, dst: &mut BytesMut) -> io::Result<()> {

        let item_len = item.len().to_string();
        if item.len() >= self.max_length {
            return Err(io::Error(io::ErrorKind::InvalidData,
                                 format!("data is too large ({}) to send. max length: {}",
                                         item_len, self.max_length)));
        }
        
        let len_string = item_len.as_bytes();
        dst.extend_from_slice(len_string);
        dst.extend_from_slice(":".to_string().as_bytes());
        dst.extend_from_slice(&item[..]);
        dst.extend_from_slice(",".to_string().as_bytes());

        Ok(())
    }
}
```

By the way, I am using a vector of `u8` here. That represents the message I want to send. It
will make more sense later ;). The encoder will get the message (`item` in the signature) and will add it to the buffer `dst`.

Decoding needs a bit more work. Basically the parser which will yield an item from a buffer
of bytes can be in two states. Either it is reading the length of the netstring, or it is reading the body, including the final comma. I represent those states with an enumeration:

```rust
#[derive(Debug, PartialEq)]
enum ParserState {
    Length,
    Data,
}
```

Then, if the parser is in the `Length` state, it should be looking for a colon, which indicates
that we have received the length of the string. In the `Data` state, the parser will read
length+1 bytes from the incoming buffer. It will make sure that the last byte received is a comma and then it will return the whole message.

```rust

impl Decoder for NetstringCodec {
    type Item = Vec<u8>;
    type Error = io::Error;

    fn decode(&mut self, buf: &mut BytesMut) -> Result<Option<Vec<u8>>, io::Error> {
        self.parse_length(buf) 
    }
}

impl NetstringCodec {
    fn parse_length(&mut self, buf: &mut BytesMut) -> Result<Option<Vec<u8>>, io::Error> {

        // Try to find the current length.
        if self.state == ParserState::Length {


            if let Some(colon_offset) = buf.iter().position(|b| *b == b':') {
                // try to extract the length here.
                let length = buf.split_to(colon_offset+1);
                let length = &length[..length.len()-1]; // remove colon from length
                //TODO better - leading 0 should not be ok
                self.current_length = str::from_utf8(&length).unwrap().parse().unwrap();

                if self.current_length > self.max_length {
                    return Err(io::Error::new(
                            io::ErrorKind::InvalidData,
                            format!("Packet length ({}) is larger than max_length {}.",
                            self.current_length,
                            self.max_length)));
                }

                self.state = ParserState::Data;
            } else {

                // If len is 9 and we are still trying to parse the length, give up now.
                // I absolutely don't want 99999999 sized packets.
                if buf.len() >= 9 {
                    return Err(io::Error::new(io::ErrorKind::InvalidData, "Data length part is bigger than 8."));
                }
                return Ok(None);
            }
        }

        // In case we have already read the size of the data.
        if self.state == ParserState::Data {
            return self.parse_data(buf);
        }

        Ok(None)
    }

    fn parse_data(&mut self, buf: &mut BytesMut) -> Result<Option<Vec<u8>>, io::Error> {

        if buf.len() >= self.current_length+1 {

            let data = buf.split_to(self.current_length+1);

            if data[data.len()-1] != b',' {
                // There's a bug in the matrix.
                return Err(io::Error::new(io::ErrorKind::InvalidData, "End delimiter of data should be a comma"));
            }

            // last char should be a comma.
            let data = &data[..data.len() - 1];

            self.state = ParserState::Length;
            self.current_length = 0;

            return Ok(Some(data.to_vec()));
        }

        Ok(None)
    }
}
```

Whenever I return `Ok(None)`, it means that no data is available yet. This codec, along with
`Framed`, is used to receive and send `Vec<u8>` in one message. The code for the server is:

```rust


fn main() -> Result<(), Box<std::error::Error>> {
    let addr = "127.0.0.1:6142".parse()?;
    let listener = TcpListener::bind(&addr)?;
    let server = listener.incoming().for_each(move |socket| {
        process(socket);
        Ok(())
    })
    .map_err(|err| {
        println!("accept error = {:?}", err);
    });

    println!("Running on localhost:6142");
    tokio::run(server);

    Ok(())
}


// Spawn a task to manage the socket.
fn process(socket: TcpStream) {
    // transform our stream of bytes to stream of frames.
    // This is where the magic happens
    let framed_sock = Framed::new(socket, NetstringCodec::new(123, true));

    let connection = Peer::new(framed_sock).map_err(|e| {
            println!("connection error = {:?}", e);
        });
    // spawn the task. Internally, this submits the task to a thread pool
    tokio::spawn(connection);
}

// Struct for each connected clients.
struct Peer {
    socket: Framed<TcpStream, codec::NetstringCodec>,
}

impl Peer {
    fn new(socket: Framed<TcpStream, codec::NetstringCodec>) -> Peer {
        Peer {
            socket,
        }
    }
}

impl Future for Peer {
    type Item = ();
    type Error = io::Error;

    fn poll(&mut self) -> Poll<(), io::Error> {
        while let Async::Ready(line) = self.socket.poll()? {
            match line {
                Some(d) => {
                    dbg!(d);
                },
                // eol/something bad happend in decoding -> disconnect.
                None => return Ok(Async::Ready(())),
            }
        }

        Ok(Async::NotReady)
    }
}
```

The interesting bits are:
- `Framed::new(...)` will transform the `TcpStream` to a stream of netstrings.
- The type for the Framed structure is `Framed<TcpStream, NetstringCodec>`
- The framed socket is used the same way as a raw TCP socket.

The following code can be used as a client:

```rust
use codec;
use std::env;
use std::io::{self, Read, Write};
use std::net::SocketAddr;
use std::thread;

use tokio::prelude::*;
use futures::sync::mpsc;

fn main() -> Result<(), Box<std::error::Error>> {
    let mut args = env::args();
    // Parse what address we're going to connect to
    let addr = match args.nth(1) {
        Some(addr) => addr,
        None => Err("this program requires at least one argument")?,
    };

    let addr = addr.parse::<SocketAddr>()?;
    let (stdin_tx, stdin_rx) = mpsc::channel(0);

    thread::spawn(|| read_stdin(stdin_tx));
    let stdin_rx = stdin_rx.map_err(|_| panic!("errors not possible on rx"));

    let stdout = tcp::connect(&addr, Box::new(stdin_rx))?;
    let mut out = io::stdout();

    tokio::run({
        stdout
            .for_each(move |chunk| {
                out.write_all(&chunk)
            })
        .map_err(|e| println!("error reading stdout; error = {:?}", e))
    });

    Ok(())
}



mod tcp {

    use tokio;
    use tokio::net::TcpStream;
    use tokio::prelude::*;
    use tokio::codec::{Framed, Decoder};

    use bytes::BytesMut;
    use std::error::Error;
    use std::io;
    use std::net::SocketAddr;

    pub fn connect(addr: &SocketAddr,
                   stdin: Box<Stream<Item = Vec<u8>, Error = io::Error> + Send>)
        -> Result<Box<Stream<Item = Vec<u8>, Error = io::Error> + Send>, Box<Error>>
        {

            let tcp = TcpStream::connect(addr);

            let stream = Box::new(tcp.map(move |stream| {
                // magiiic
                let (sink, stream) = Framed::new(stream, tw::codec::NetstringCodec::new(255, true)).split();

                tokio::spawn(stdin.forward(sink).then(|result| {
                    if let Err(e) = result {
                        println!("failed to write to socket: {}", e)
                    }
                    Ok(())
                }));

                stream
            }).flatten_stream());

            Ok(stream)
        }

}

fn read_stdin(mut tx: mpsc::Sender<Vec<u8>>) {
    let mut stdin = io::stdin();


    loop {
        let buf: Vec<u8> = vec![2, 14, 42];
        tx = match tx.send(buf).wait() {
            Ok(tx) => tx,
            Err(_) => break,
        };

        thread::sleep(std::time::Duration::from_secs(1));
    }
}
```

This code is based on the example from tokio `connect.rs`. The Framed socket is split into the stream and the sink.

Well that's great. I have a client and a server that can exchange vectors of `u8` and I don't have to manage buffering data from the TCP socket anymore. Next step is to send data that actually mean anything instead of a sequence of bytes. To do so, I will use serde and MessagePack to serialize a Rust Struct into a vector of `u8`. 

## Serializing/Deserializing the messages

Serde is a crate to serialize and deserialize Rust objects to a defined format. [MessagePack](https://msgpack.org/index.html) is one of those formats and is binary, i.e. we can convert a Rust object to a vector of bytes.

Now you can see the bigger picture:
- The socket receives a netstring.
- It will extract a sequence of bytes from this netstring
- Serde will then deserialize the sequence of bytes to a proper Rust structure

![Receiving a message]({{ site.url }}/assets/receiving.PNG)

On the other side:
- Serde serialize a Rust structure to a vector of bytes.
- This vector of bytes is then encoded to a netstring.
- Which in turn is sent to the other party via the socket.

![Sending a message]({{ site.url }}/assets/sending.PNG)

### The simplest message

A very basic example is: 

```rust
use serde_derive::{Serialize, Deserialize};
use rmp_serde::Serializer;
use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize, Debug)]
pub struct Message {
        x: f32,
        msg: String,
}

impl Message {
        pub fn pack(&self) -> Vec<u8> {
                let mut buf = Vec::new();
                self.serialize(&mut Serializer::new(&mut buf)).unwrap()
                buf
        }
        
        pub fn unpack(buf: Vec<u8>) -> Result<Self, rmp_serde::decode::error> {
                rmp_serde::from_slice::Message>(&buf).unwrap()
        }
}
```

In the server example, you can use this code to get a message structure from a socket.

```rust

impl Future for Peer {
    type Item = ();
    type Error = io::Error;

    fn poll(&mut self) -> Poll<(), io::Error> {
        while let Async::Ready(line) = self.socket.poll()? {
            match line {
                Some(d) => {
                    let msg = Message::unpack(d); // This is a Result
                    dbg!(d);
                },
                // eol/something bad happend in decoding -> disconnect.
                None => return Ok(Async::Ready(())),
            }
        }

        Ok(Async::NotReady)
    }
}

```
Just one line is necessary. The code for the client is straightforward as well so I won't
paste it here. Just call `message.pack()` to get the `Vec<u8>` that can be sent with the
framed socket.

### I want different message types!

In reality, using only a struct like that for a message will not be very useful. What if you
want to send position of player in one message, and some action in another message (like "Shoot").
Clearly, the previous implementation will not be enough. You might add a lot of fields for different
purposes but the structure will become very big after some time.

Fortunately, serde allows use to serialize and deserialize enumeration. We can use that fact to
have a lot of different small messages. First, you need to create a small structure for each
message type. For example:

```rust
#[derive(Debug, Serialize, Deserialize)]
struct MoveMessage {
        x: f32,
        y: f32,
        z: f32,
}

#[derive(Debug, Serialize, Deserialize)]
struct ShootMessage;
```

Then, create an enumeration.

```rust
#[derive(Debug, Serialize, Deserialize)]
enum Message {
        Move(MoveMessage),
        Shoot(ShootMessage),
}

impl Message {
        // Same as before
        }
```
And... that is all is needed to send multiple kind of messages on the wire!
