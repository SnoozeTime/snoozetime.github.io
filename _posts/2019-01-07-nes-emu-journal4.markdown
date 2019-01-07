---
layout: post
title: "NES emulation journal: Implementing mappers"
date: 2019-01-03
---

The first NES games were pretty simple. Arkanoid, Donkey Kong and Super Mario
Bros for example are all running using the first generation of cartridge, which
includes 16kb or 32kb of ROM (instructions) and 8kb of sprite/tiles data.
The size and scope of a game were effectively limited.

Game developers began using different [kind of chips](https://en.wikipedia.org/wiki/Memory_management_controller) for their game to extend
those original limitations. Instead of having just 32kb of PRG-ROM (program ROM) data, a game 
could have much more and the chip would select what instruction area is currently
in use. In NES emulation, the term `mapper` is used to refer to the different type of
chips.

## Mapper 0: NROM

This is the mapper used with the first NES games. It has not bank-switching capabilities
so the game using it are pretty simple. It can have either one or two PRG-ROM of 16kb, that
are mapped at ranges 0x8000-0xBFFF and 0xC000-0xFFFF of the CPU memory. It also has CHR-ROM
which contains the tile and sprite data. This CHR-ROM is mapped to the PPU memory at addresses
0x0-0x2000.

You can still have fun with games using this mapper:
- Donkey Kong
- Mario Bros
- Super Mario Bros
- Arkanoid

The CPU cannot write to the PRG-ROM for this mapper. We'll see later that other cartridge have registers
that can be written to using the PRG-ROM addresses.

## Mapper 2: UxRom

The easiest mapper to implement after NROM is Uxrom. It provide bank-switching capabilities. It means
that the program can change the data that is mapped to the CPU memory. In the Mapper 2's case, the 
CPU memory from 0x8000 to 0xBFFF can be changed by writing to the mapper's register.

The PPU memory is mapped to the cartridge RAM. There are not ROM for sprites but instead the program will
write the tiles to memory before starting the game.

By implementing UxROM, you can unlock a lot of pretty cool games. Notably:
- Contra
- MegaMan
- Castlevania


![Contra: A game using mapper 2]({{ site.url }}/assets/contra.gif)
*Contra: A game using mapper 2*

## Mapper 1: MMC1

Once you understand UxROM, a more complicated mapper is MMC1. The principle is similar. CHR and PRG data can be
switched to allow a game to have more data. The bank switching mechanism is more complex that UxROM in that it allows
to switch banks from multiple memory locations. You'll need to implement this mapper if you wish to play:
- MegaMan 2
- The Legend of Zelda
- Metroid


![Megaman 2: a glorious death]({{ site.url }}/assets/megaman.gif)
*Megaman 2: Glorious death*

I still have a few bugs to fix though :D
![The buggy Legend of Zelda]({{ site.url }}/assets/zelda.gif)
*The Buggy Legend Of Zelda*

## Next steps

MMC3 is also a must to implement as it is required to play Super Mario Bros 3. I still have a lot of graphic
glitches in some games so I'll start with that first...But hopefully I should be ready soon to put the code
on a RaspberryPi!

## Other recent improvements
- Support 2 players
- Performance improvement: Turned out that reading from input at each cycle slows down the emulator a lot...

## References:
[http://wiki.nesdev.com/w/index.php/UxROM](http://wiki.nesdev.com/w/index.php/UxROM)
[https://wiki.nesdev.com/w/index.php/MMC1](https://wiki.nesdev.com/w/index.php/MMC1)



