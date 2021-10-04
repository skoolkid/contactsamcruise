Contact Sam Cruise disassembly
==============================

A disassembly of the [Spectrum](https://en.wikipedia.org/wiki/ZX_Spectrum) game
[Contact Sam Cruise](https://en.wikipedia.org/wiki/Contact_Sam_Cruise), created
using [SkoolKit](https://skoolkit.ca).

Decide which number base you prefer and then click the corresponding link below
to browse the latest release:

* [Contact Sam Cruise disassembly](https://skoolkid.github.io/contactsamcruise/) (hexadecimal; mirror [here](https://skoolkid.gitlab.io/contactsamcruise/))
* [Contact Sam Cruise disassembly](https://skoolkid.github.io/contactsamcruise/dec/) (decimal; mirror [here](https://skoolkid.gitlab.io/contactsamcruise/dec/))

To build the current development version of the disassembly, first obtain the
development version of [SkoolKit](https://github.com/skoolkid/skoolkit). Then:

    $ skool2html.py sources/csc.skool

To build an assembly language source file that can be fed to an assembler:

    $ skool2asm.py sources/csc.skool > csc.asm
