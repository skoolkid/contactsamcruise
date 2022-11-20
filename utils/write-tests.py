#!/usr/bin/env python3
import sys
import os

SKOOLKIT_HOME = os.environ.get('SKOOLKIT_HOME')
if not SKOOLKIT_HOME:
    sys.stderr.write('SKOOLKIT_HOME is not set; aborting\n')
    sys.exit(1)
if not os.path.isdir(SKOOLKIT_HOME):
    sys.stderr.write('SKOOLKIT_HOME={}: directory not found\n'.format(SKOOLKIT_HOME))
    sys.exit(1)
sys.path.insert(0, '{}/tools'.format(SKOOLKIT_HOME))
from testwriter import write_tests

SKOOL = 'csc.skool'

SNAPSHOT = 'build/contact_sam_cruise.z80'

OUTPUT = """Using ref files: csc.ref, bugs.ref, changelog.ref, data.ref, facts.ref, glossary.ref, graphics.ref, pages.ref, pokes.ref, sound.ref
Parsing csc.skool
Output directory: {odir}/contact_sam_cruise
Copying {SKOOLKIT_HOME}/skoolkit/resources/skoolkit.css to skoolkit.css
Copying csc.css to csc.css
Writing disassembly files in asm
Writing maps/all.html
Writing maps/routines.html
Writing maps/data.html
Writing maps/messages.html
Writing buffers/gbuffer.html
Writing reference/bugs.html
Writing reference/changelog.html
Writing reference/facts.html
Writing reference/glossary.html
Writing graphics/glitches.html
Writing reference/pokes.html
Writing graphics/graphics.html
Writing graphics/playarea.html
Writing graphics/asstart0.html
Writing graphics/asstart1.html
Writing graphics/asstart2.html
Writing graphics/asstart3.html
Writing graphics/asstart4.html
Writing graphics/playarea_objects.html
Writing graphics/as.html
Copying tiles.js to tiles.js
Writing graphics/astiles.html
Writing buffers/cbuffer.html
Writing tables/keys.html
Writing maps/command_lists.html
Writing reference/walkthrough.html
Writing sound/sound.html
Parsing load.skool
Writing load/load.html
Writing disassembly files in load
Parsing save.skool
Writing save/save.html
Writing disassembly files in save
Parsing start.skool
Writing start/start.html
Writing disassembly files in start
Writing index.html"""

write_tests(SKOOL, SNAPSHOT, OUTPUT)
