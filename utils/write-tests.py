#!/usr/bin/env python
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

SKOOL = '../sources/csc.skool'

SNAPSHOT = '../build/contact_sam_cruise.z80'

OUTPUT = """Using skool file: ../sources/csc.skool
Using ref files: ../sources/csc.ref, ../sources/csc-bugs.ref, ../sources/csc-changelog.ref, ../sources/csc-data.ref, ../sources/csc-facts.ref, ../sources/csc-glossary.ref, ../sources/csc-graphics.ref, ../sources/csc-pages.ref, ../sources/csc-pokes.ref
Parsing ../sources/csc.skool
Creating directory {odir}/contact_sam_cruise
Copying {SKOOLKIT_HOME}/skoolkit/resources/skoolkit.css to {odir}/contact_sam_cruise/skoolkit.css
Copying ../sources/csc.css to {odir}/contact_sam_cruise/csc.css
  Writing disassembly files in contact_sam_cruise/asm
  Writing contact_sam_cruise/maps/all.html
  Writing contact_sam_cruise/maps/routines.html
  Writing contact_sam_cruise/maps/data.html
  Writing contact_sam_cruise/maps/messages.html
  Writing contact_sam_cruise/buffers/gbuffer.html
  Writing contact_sam_cruise/graphics/graphics.html
  Writing contact_sam_cruise/graphics/asstart0.html
  Writing contact_sam_cruise/graphics/asstart1.html
  Writing contact_sam_cruise/graphics/asstart2.html
  Writing contact_sam_cruise/graphics/asstart3.html
  Writing contact_sam_cruise/graphics/asstart4.html
  Writing contact_sam_cruise/graphics/as.html
  Copying ../sources/tiles.js to {odir}/contact_sam_cruise/tiles.js
  Writing contact_sam_cruise/graphics/astiles/astiles.html
  Writing contact_sam_cruise/buffers/cbuffer.html
  Writing contact_sam_cruise/tables/keys.html
  Writing contact_sam_cruise/maps/command_lists.html
  Writing contact_sam_cruise/reference/walkthrough.html
  Writing contact_sam_cruise/graphics/playarea.html
  Writing contact_sam_cruise/graphics/playarea_objects.html
  Writing contact_sam_cruise/graphics/glitches.html
  Writing contact_sam_cruise/reference/changelog.html
  Writing contact_sam_cruise/reference/bugs.html
  Writing contact_sam_cruise/reference/facts.html
  Writing contact_sam_cruise/reference/glossary.html
  Writing contact_sam_cruise/reference/pokes.html
  Parsing ../sources/csc-load.skool
    Writing contact_sam_cruise/load/load.html
    Writing disassembly files in contact_sam_cruise/load
  Parsing ../sources/csc-save.skool
    Writing contact_sam_cruise/save/save.html
    Writing disassembly files in contact_sam_cruise/save
  Parsing ../sources/csc-start.skool
    Writing contact_sam_cruise/start/start.html
    Writing disassembly files in contact_sam_cruise/start
  Writing contact_sam_cruise/index.html"""

HTML_WRITER = '../sources:samcruise.ContactSamCruiseHtmlWriter'

ASM_WRITER = '../sources:samcruise.ContactSamCruiseAsmWriter'

write_tests(SKOOL, SNAPSHOT, OUTPUT, HTML_WRITER, ASM_WRITER)
