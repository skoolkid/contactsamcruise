# -*- coding: utf-8 -*-
import sys
PY3 = sys.version_info >= (3,)
if PY3:
    from io import StringIO
else:
    from StringIO import StringIO
import os
import shutil
import tempfile
from lxml import etree
from xml.dom.minidom import parse
from xml.dom import Node
from unittest import TestCase
from nose.plugins.skip import SkipTest

SKOOLKIT_HOME = os.environ.get('SKOOLKIT_HOME')
if not SKOOLKIT_HOME:
    sys.stderr.write('SKOOLKIT_HOME is not set; aborting\n')
    sys.exit(1)
if not os.path.isdir(SKOOLKIT_HOME):
    sys.stderr.write('SKOOLKIT_HOME={}: directory not found\n'.format(SKOOLKIT_HOME))
    sys.exit(1)
sys.path.insert(0, SKOOLKIT_HOME)
from skoolkit import skool2asm, skool2ctl, skool2html, skool2sft, sna2skool

CSC_SKOOL = '../sources/csc.skool'
CSC_LOAD_SKOOL = '../sources/csc-load.skool'
CSC_SAVE_SKOOL = '../sources/csc-save.skool'
CSC_START_SKOOL = '../sources/csc-start.skool'

XHTML_XSD = os.path.join(SKOOLKIT_HOME, 'XSD', 'xhtml1-strict.xsd')

OUTPUT_CSC = """Creating directory {odir}
Using skool file: {srcdir}/csc.skool
Using ref files: {srcdir}/csc.ref, {srcdir}/csc-bugs.ref, {srcdir}/csc-changelog.ref, {srcdir}/csc-data.ref, {srcdir}/csc-facts.ref, {srcdir}/csc-glossary.ref, {srcdir}/csc-graphics.ref, {srcdir}/csc-pages.ref, {srcdir}/csc-pokes.ref
Parsing {srcdir}/csc.skool
Creating directory {odir}/contact_sam_cruise
Copying {SKOOLKIT_HOME}/skoolkit/resources/skoolkit.css to {odir}/contact_sam_cruise/skoolkit.css
Copying ../resources/csc.css to {odir}/contact_sam_cruise/csc.css
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
  Copying ../resources/tiles.js to {odir}/contact_sam_cruise/tiles.js
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
  Parsing {srcdir}/csc-load.skool
    Writing contact_sam_cruise/load/load.html
    Writing disassembly files in contact_sam_cruise/load
  Parsing {srcdir}/csc-save.skool
    Writing contact_sam_cruise/save/save.html
    Writing disassembly files in contact_sam_cruise/save
  Parsing {srcdir}/csc-start.skool
    Writing contact_sam_cruise/start/start.html
    Writing disassembly files in contact_sam_cruise/start
  Writing contact_sam_cruise/index.html"""

def _find_ids_and_hrefs(elements, doc_anchors, doc_hrefs):
    for node in elements:
        if node.nodeType == Node.ELEMENT_NODE:
            element_id = node.getAttribute('id')
            if element_id:
                doc_anchors.add(element_id)
            if node.tagName in ('a', 'link', 'img', 'script'):
                if node.tagName == 'a':
                    element_name = node.getAttribute('name')
                    if element_name:
                        doc_anchors.add(element_name)
                if node.tagName in ('a', 'link'):
                    element_href = node.getAttribute('href')
                    if element_href:
                        doc_hrefs.add(element_href)
                elif node.tagName in ('img', 'script'):
                    element_src = node.getAttribute('src')
                    if element_src:
                        doc_hrefs.add(element_src)
            _find_ids_and_hrefs(node.childNodes, doc_anchors, doc_hrefs)

def _read_files(root_dir):
    all_files = {} # filename -> (element ids and <a> names, hrefs and srcs)
    for root, dirs, files in os.walk(root_dir):
        for f in files:
            fname = os.path.join(root, f)
            all_files[fname] = (set(), set())
            if f.endswith('.html'):
                doc = parse(fname)
                _find_ids_and_hrefs(doc.documentElement.childNodes, *all_files[fname])
    return all_files

def check_links(root_dir):
    missing_files = []
    missing_anchors = []
    all_files = _read_files(root_dir)
    linked = set()
    for fname in all_files:
        for href in all_files[fname][1]:
            if not href.startswith('http://'):
                if href.startswith('#'):
                    link_dest = fname + href
                else:
                    link_dest = os.path.normpath(os.path.join(os.path.dirname(fname), href))
                dest_fname, sep, anchor = link_dest.partition('#')
                linked.add(dest_fname)
                if dest_fname not in all_files:
                    missing_files.append((fname, link_dest))
                elif anchor and anchor not in all_files[dest_fname][0]:
                    missing_anchors.append((fname, link_dest))
    orphans = set()
    for fname in all_files:
        if fname not in linked:
            orphans.add(fname)
    return all_files, orphans, missing_files, missing_anchors

class Stream:
    def __init__(self):
        self.buffer = StringIO()

    def write(self, text):
        self.buffer.write(text)

    def getvalue(self):
        return self.buffer.getvalue()

    def clear(self):
        self.buffer.seek(0)
        self.buffer.truncate()

class DisassembliesTestCase(TestCase):
    def setUp(self):
        self.maxDiff = None
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        sys.stdout = self.out = Stream()
        sys.stderr = self.err = Stream()
        self.tempfiles = []
        self.tempdirs = []

    def tearDown(self):
        for f in self.tempfiles:
            if os.path.isfile(f):
                os.remove(f)
        for d in self.tempdirs:
            if os.path.isdir(d):
                shutil.rmtree(d, True)
        sys.stdout = self.stdout
        sys.stderr = self.stderr

    def _to_lines(self, text):
        # Use rstrip() to remove '\r' characters (useful on Windows)
        lines = [line.rstrip() for line in text.split('\n')]
        if lines[-1] == '':
            lines.pop()
        return lines

    def run_skoolkit_command(self, cmd, args, out_lines=True, err_lines=False):
        self.out.clear()
        self.err.clear()
        try:
            cmd(args.split())
        except SystemExit:
            pass
        out = self._to_lines(self.out.getvalue()) if out_lines else self.out.getvalue()
        err = self._to_lines(self.err.getvalue()) if err_lines else self.err.getvalue()
        return out, err

class AsmTestCase(DisassembliesTestCase):
    def _write_asm(self, options, skoolfile, writer=None):
        args = [options, skoolfile]
        if writer:
            writer_spec = '../skoolkit:{}'.format(writer)
            args.insert(0, '-W {}'.format(writer_spec))
        output, stderr = self.run_skoolkit_command(skool2asm.main, ' '.join(args), err_lines=True)
        self.assertTrue(stderr[0].startswith('Parsed {}'.format(skoolfile)))
        if writer:
            self.assertEqual(len(stderr), 3)
            self.assertEqual(stderr[1], 'Using ASM writer {}'.format(writer_spec))
        else:
            self.assertEqual(len(stderr), 2)
        self.assertTrue(stderr[-1].startswith('Wrote ASM to stdout'))

    def write_csc(self, options):
        self._write_asm(options, CSC_SKOOL, 'samcruise.ContactSamCruiseAsmWriter')

    def write_csc_load(self, options):
        self._write_asm(options, CSC_LOAD_SKOOL)

    def write_csc_save(self, options):
        self._write_asm(options, CSC_SAVE_SKOOL)

    def write_csc_start(self, options):
        self._write_asm(options, CSC_START_SKOOL)

class CtlTestCase(DisassembliesTestCase):
    def _write_ctl(self, options, skoolfile):
        args = '{} {}'.format(options, skoolfile)
        output, stderr = self.run_skoolkit_command(skool2ctl.main, args)
        self.assertEqual(stderr, '')

    def write_csc(self, options):
        self._write_ctl(options, CSC_SKOOL)

class HtmlTestCase(DisassembliesTestCase):
    def setUp(self):
        DisassembliesTestCase.setUp(self)
        self.odir = 'html-{}'.format(os.getpid())
        self.tempdirs.append(self.odir)

    def _validate_xhtml(self):
        if os.path.isfile(XHTML_XSD):
            with open(XHTML_XSD) as f:
                xmlschema_doc = etree.parse(f)
            xmlschema = etree.XMLSchema(xmlschema_doc)
            for root, dirs, files in os.walk(self.odir):
                for fname in files:
                    if fname[-5:] == '.html':
                        htmlfile = os.path.join(root, fname)
                        try:
                            xhtml = etree.parse(htmlfile)
                        except etree.LxmlError as e:
                            self.fail('Error while parsing {}: {}'.format(htmlfile, e.message))
                        try:
                            xmlschema.assertValid(xhtml)
                        except etree.DocumentInvalid as e:
                            self.fail('Error while validating {}: {}'.format(htmlfile, e.message))

    def _check_links(self):
        all_files, orphans, missing_files, missing_anchors = check_links(self.odir)
        if orphans or missing_files or missing_anchors:
            error_msg = []
            if orphans:
                error_msg.append('Orphaned files: {}'.format(len(orphans)))
                for fname in orphans:
                    error_msg.append('  {}'.format(fname))
            if missing_files:
                error_msg.append('Links to non-existent files: {}'.format(len(missing_files)))
                for fname, link_dest in missing_files:
                    error_msg.append('  {} -> {}'.format(fname, link_dest))
            if missing_anchors:
                error_msg.append('Links to non-existent anchors: {}'.format(len(missing_anchors)))
                for fname, link_dest in missing_anchors:
                    error_msg.append('  {} -> {}'.format(fname, link_dest))
            self.fail('\n'.join(error_msg))

    def _write_html(self, options, writer, ref_file, exp_output):
        shutil.rmtree(self.odir, True)

        main_options = '-W ../skoolkit:{}'.format(writer)
        main_options += ' -S ../resources'
        main_options += ' -d {}'.format(self.odir)
        args = '{} {} ../{}'.format(main_options, options, ref_file)
        output, error = self.run_skoolkit_command(skool2html.main, args)
        self.assertEqual(len(error), 0)
        srcdir = '../{}'.format(os.path.dirname(ref_file))
        reps = {'odir': self.odir, 'srcdir': srcdir, 'SKOOLKIT_HOME': SKOOLKIT_HOME}
        self.assertEqual(exp_output.format(**reps).split('\n'), output)

        self._validate_xhtml()
        self._check_links()

    def write_csc(self, options):
        self._write_html(options, 'samcruise.ContactSamCruiseHtmlWriter', 'sources/csc.ref', OUTPUT_CSC)

class SftTestCase(DisassembliesTestCase):
    def _assert_output_equal(self, output, expected):
        for i, line in enumerate(expected):
            if i < len(output):
                self.assertEqual(output[i], line)
        if len(output) > len(expected):
            self.fail("Unexpected extra line in output: '%s'" % output[len(expected)])
        elif len(expected) > len(output):
            self.fail("Expected lines missing from output, starting with: '%s'" % expected[len(output)])

    def _write_text_file(self, contents):
        fd, path = tempfile.mkstemp(dir='', text=True)
        path = os.path.basename(path.replace(os.path.sep, '/'))
        f = os.fdopen(fd, 'wt')
        self.tempfiles.append(path)
        f.write(contents)
        f.close()
        return path

    def _write_sft(self, options, skoolfile, game):
        snapshot = '../build/{}.z80'.format(game)
        if not os.path.isfile(snapshot):
            raise SkipTest("{} not found".format(snapshot))
        with open(skoolfile, 'rt') as f:
            orig_skool = f.read().split('\n')
        skool2sft_args = '{} {}'.format(options, skoolfile)
        sft, stderr = self.run_skoolkit_command(skool2sft.main, skool2sft_args, out_lines=False)
        self.assertEqual(stderr, '')
        sftfile = self._write_text_file(sft)
        sna2skool_args = '-T {} {}'.format(sftfile, snapshot)
        output, stderr = self.run_skoolkit_command(sna2skool.main, sna2skool_args)
        self._assert_output_equal(output, orig_skool[:-1])

    def write_csc(self, options):
        self._write_sft(options, CSC_SKOOL, 'contact_sam_cruise')
