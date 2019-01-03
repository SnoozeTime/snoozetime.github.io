---
layout: post
title: "NES emulation journal: Do not abuse substances"
date: 2019-01-03
---

Happy new year every body! My NES emulator is taking shape! I am 
currently implementing side-scrolling and the main target is Super Mario
Bros.

The fine-x for smooth scrolling is set with the PPU register 0x2005. Fine-x
is a 3-bit value (so, between 0 and 7) and will decide what bit to select from
the tile byte when rendering a background pixel.

My implementation is not complete yet (I correctly fetch the low plane bit 
but not the high plane bit), which gives me something totally funky. Mario
on mushrooms!

![Mario on mushrooms]({{ site.url }}/assets/mushroom_mario.gif)

Enjoy!
