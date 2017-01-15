#!/usr/bin/env python3

import sys
import os
import argparse

# Use the current development version of SkoolKit
SKOOLKIT_HOME = os.environ.get('SKOOLKIT_HOME')
if not SKOOLKIT_HOME:
    sys.stderr.write('SKOOLKIT_HOME is not set; aborting\n')
    sys.exit(1)
if not os.path.isdir(SKOOLKIT_HOME):
    sys.stderr.write('SKOOLKIT_HOME={}; directory not found\n'.format(SKOOLKIT_HOME))
    sys.exit(1)
sys.path.insert(0, SKOOLKIT_HOME)

from skoolkit.image import ImageWriter
from skoolkit.snapshot import get_snapshot
from skoolkit.skoolhtml import Udg as BaseUdg, Frame

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSC_Z80 = '{}/build/contact_sam_cruise.z80'.format(parent_dir)

# Sniper's animatory state
SNIPER_AS = 54

# Doors
DOORS = {
    's1': ((48384, 84), (48640, 83)), # door of shop at far left of town
    's2': ((48386, 84), (48642, 83)), # door of next shop along
    '74': ((48389, 86),),             # door to no. 74
    '31': ((48398, 86),),             # door to no. 31
    '27': ((48403, 85),),             # door to no. 27
    '19': ((48410, 86),),             # door to no. 19
    's3': ((48412, 84), (48668, 83)), # door of shop under no. 17
    '17': ((48413, 85),),             # door to no. 17
    's4': ((48414, 84), (48670, 83)), # door of shop under no. 15
    '15': ((48415, 85),)              # door to no. 15
}

class Udg(BaseUdg):
    def __init__(self, attr, data, mask=None, x=None, y=None, fg_udg=None):
        BaseUdg.__init__(self, attr, data, mask)
        self.x = x
        self.y = y
        self.fg_udg = fg_udg

class ContactSamCruise:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self._snapshots = []

        # The tile references for the sniper sprite (animatory state 54) are
        # updated depending on the phases of animation; we use animatory states
        # greater than 256 (with bits 8-10 indicating the phase number) to
        # represent these sprites
        self.sniper_phases = (
            (SNIPER_AS + 256, 'ducking out of sight or emerging', (109, 0, 0, 110, 0, 0)),
            (SNIPER_AS + 512, 'half-height', (109, 5, 0, 110, 111, 0)),
            (SNIPER_AS + 768, 'half-height, firing', (109, 234, 0, 110, 235, 0)),
            (SNIPER_AS + 1024, 'full height', (109, 5, 112, 110, 111, 113)),
            (SNIPER_AS + 1280, 'full height, firing', (109, 234, 0, 110, 235, 113))
        )
        self.sniper_states = [state for state, desc, refs in self.sniper_phases]

        # Sprite tile references 239-247 are used by the sprites of Sam rolling
        # and somersaulting; this dictionary maps those tile references to the
        # base addresses of the source tiles that are copied and rotated
        self.sam_tile_refs = {
            239: 50946,
            240: 50947,
            241: 50948,
            242: 51114,
            243: 55245,
            244: 50951,
            245: 55221,
            246: 55229,
            247: 55237
        }

    def push_snapshot(self):
        self._snapshots.append(self.snapshot[:])

    def pop_snapshot(self):
        self.snapshot = self._snapshots.pop()

    def _get_sprite_udg(self, state, ref_page, udg_page):
        ref_addr = state + 256 * ref_page
        ref = self.snapshot[ref_addr]
        if ref == 0:
            data = [0] * 8
            mask = [255] * 8
        else:
            udg_addr = ref + 256 * udg_page
            data = self.snapshot[udg_addr:udg_addr + 4096:512]
            mask = self.snapshot[udg_addr + 256:udg_addr + 4352:512]
        return Udg(None, data, mask)

    def get_play_area_udgs(self, x, y, w, h):
        play_area_udgs = []
        for row in range(y, y + h):
            play_area_udgs.append([])
            for col in range(x, x + w):
                play_area_udgs[-1].append(self.get_play_area_udg(row, col))
        self._superimpose_sprite_udgs(play_area_udgs, x, y, w, h)
        return play_area_udgs

    def get_play_area_udg(self, y, x):
        xh = x // 8
        xl = x % 8
        yhp = 256 * (184 + y // 6)
        ylp = 256 * (160 + 2 * (y % 6))
        z = self.snapshot[xh + yhp]                    # Z value
        z1 = self.snapshot[z + 48896]                  # Z' value
        if (z1 >> 7 - xl) & 1:
            ylp += 3072
        z2 = self.snapshot[z + 128 + 256 * (184 + xl)] # Z'' value
        t = self.snapshot[z2 + ylp]                    # T value
        attr_ref = self.snapshot[32 + xh + yhp]
        attr = self.snapshot[attr_ref + 256 * (168 + (t & 3))]
        t1 = self.snapshot[z2 + ylp + 256]             # T' value
        fg_udg = None
        if t & 128:
            # This location has a background tile and a foreground tile
            if t & 64:
                # There is no window at this location
                bg_ref = 128 + (t & 60) // 2
                if t1 & 128:
                    bg_ref += 1
                fg_metaref = t1 | 128
            else:
                # There is a window at this location
                w_flags = self.snapshot[64 + xh + yhp] # Window flags
                k = self.snapshot[xh + 65472]
                if k < 168 and self.snapshot[k + 32512]:
                    # This window is affected by a blown fuse, so make sure the
                    # lights are off (set bit 5)
                    w_flags |= 32
                if t & 4:
                    # The right-hand window of a pair is here, so shift its
                    # window decoration bits (0 and 1) into bits 6 and 7, and
                    # preserve the light switch bit (bit 5)
                    w_flags = 64 * (w_flags & 3) + (w_flags & 32)
                fg_metaref = t1 | (w_flags & 224)
                bg_ref = 159 # Use tile 159 (blank) as the background
            # Get the background tile
            udg_addr = bg_ref + 32768
            data = self.snapshot[udg_addr:udg_addr + 2048:256]
            # Collect the top half of the foreground tile
            fg_ref1 = self.snapshot[fg_metaref + 49152]
            h = 128
            fg_data = []
            fg_mask = []
            for i in range(4):
                fg_data.append(self.snapshot[fg_ref1 + 256 * h])
                fg_mask.append(self.snapshot[fg_ref1 + 256 * (h + 1)])
                h += 2
            # Collect the bottom half of the foreground tile
            fg_ref2 = self.snapshot[fg_metaref + 49408]
            h = 128
            for i in range(4, 8):
                fg_data.append(self.snapshot[fg_ref2 + 256 * h])
                fg_mask.append(self.snapshot[fg_ref2 + 256 * (h + 1)])
                h += 2
            # Create a foreground UDG that can be superimposed later
            fg_udg = Udg(0, fg_data, fg_mask)
        else:
            # This location has only one tile (either background or foreground)
            udg_addr = t1 + 256 * (128 + 2 * (t & 28))
            data = self.snapshot[udg_addr:udg_addr + 2048:256]
            if t & 64:
                # This location has an opaque foreground tile
                fg_udg = Udg(0, data)

        return Udg(attr, data, x=x, y=y, fg_udg=fg_udg)

    def _superimpose_sprite_udgs(self, udg_array, x, y, w, h):
        initial_states = [self.snapshot[a:a + 4] for a in range(65198, 65408, 6)]
        initial_states += [self.snapshot[a:a + 4] for a in range(56864, 58912, 256)]
        sam_z = self.snapshot[58884]
        sam_as, sam_x, sam_y = self.snapshot[58880:58883]
        initial_states.append((sam_as, sam_x, sam_y, sam_z))
        for z in (1, 2, 4):
            for state, char_x, char_y, char_z in initial_states:
                if char_z != z:
                    continue
                width, height = self._get_sprite_size(state)
                x0 = char_x - x
                if x0 >= w:
                    continue
                x1 = min((x0 + width, w))
                if x1 < 0:
                    continue
                x0 = max((x0, 0))
                y0 = char_y - y
                if y0 >= h:
                    continue
                y1 = min((y0 + height, h))
                if y1 < 0:
                    continue
                y0 = max((y0, 0))
                for i in range(y0, y1):
                    for j in range(x0, x1):
                        udg = udg_array[i][j]
                        if z == 1 and udg.fg_udg and not udg.fg_udg.mask:
                            # This location has an opaque foreground tile, so
                            # don't superimpose characters with z=1
                            continue
                        sprite_udg = self.get_sprite_udg(state, udg.y - char_y, udg.x - char_x)
                        for k in range(8):
                            udg.data[k] = (udg.data[k] | sprite_udg.data[k]) & sprite_udg.mask[k]
            if z == 1:
                # Apply any foreground tile masks over characters with z=1
                for row in udg_array:
                    for udg in row:
                        fg_udg = udg.fg_udg
                        if fg_udg and fg_udg.mask:
                            for k in range(8):
                                udg.data[k] = (udg.data[k] | fg_udg.data[k]) & fg_udg.mask[k]

    def get_sprite_udg(self, state, row, col, udg_page=None):
        width, height = self._get_sprite_size(state)
        udg_page = 199
        col = width - 1 - col if state & 128 else col
        tile_num = col * height + row
        ref_page = 215 + tile_num

        do_pop = True
        if state & 1919 in self.sniper_states:
            self.push_snapshot()
            phase = self.sniper_states.index(state & 1919)
            self._prep_sniper_sprite(phase, tile_num)
            state = SNIPER_AS + (state & 128)
        elif state & 127 in (7, 23, 39, 55, 63, 71, 79, 87, 95, 103, 111, 119):
            self.push_snapshot()
            self._prep_knocked_out_sprite(state, tile_num)
        elif state & 127 in (9, 10, 15, 31):
            self.push_snapshot()
            self._prep_sam_sprite(state, tile_num)
        else:
            do_pop = False

        as_norm = (state if state & 7 else state + 2) | 128
        udg = self._get_sprite_udg(as_norm, ref_page, udg_page)
        if state & 128:
            udg.flip()

        if do_pop:
            self.pop_snapshot()
        return udg

    def _get_sprite_size(self, state):
        if state & 127 >= 120:
            return 2, 2
        if state % 8 == 7:
            return 5, 3
        return 3, 5

    def _prep_sniper_sprite(self, phase, tile_num):
        affected_tiles = [1, 2, 3, 6, 7, 8]
        if tile_num not in affected_tiles:
            return
        refs = self.sniper_phases[phase][2]
        dest_ref = refs[affected_tiles.index(tile_num)]
        dest_addr = SNIPER_AS + 128 + 256 * (215 + tile_num)
        self.snapshot[dest_addr] = dest_ref

    def _prep_knocked_out_sprite(self, state, tile_num):
        affected_tiles = [10, 7, 4, 1, 11, 8, 5, 2]
        if tile_num not in affected_tiles:
            return
        tile_index = affected_tiles.index(tile_num)
        dest_ref = 248 + tile_index
        source_tiles = (1, 2, 3, 4, 6, 7, 8, 9)
        source_tile_num = source_tiles[tile_index]
        source_ref_addr = (state & 248 | 130) + 256 * (215 + source_tile_num)
        source_ref = self.snapshot[source_ref_addr]
        tile_addr = source_ref + 256 * 199
        tile_data = self.snapshot[tile_addr:tile_addr + 4096:256]
        for i in range(3):
            tile_data = self._rotate_tile_data(tile_data)
        dest_addr = dest_ref + 256 * 199
        self.snapshot[dest_addr:dest_addr + 4096:256] = tile_data

    def _prep_sam_sprite(self, state, tile_num):
        target_ref = self.snapshot[state | 128 + 256 * (215 + tile_num)]
        source = self.sam_tile_refs.get(target_ref)
        if source is None:
            return
        target = target_ref + 256 * 199
        self.snapshot[target:target + 4096:256] = self.snapshot[source:source + 4096:256]
        if target_ref == 243:
            mask = 55245
            for i in range(8):
                b = self.snapshot[target] | self.snapshot[mask] & self.snapshot[mask + 256]
                self.snapshot[target] = b
                self.snapshot[target + 256] = b
                target += 512
                mask += 512
        rotations = [10, 15, 9, 31].index(state & 127)
        for i in range(rotations):
            self._rotate_tile(target_ref)

    def _rotate_tile(self, ref):
        addr = ref + 256 * 199
        tile_data = self.snapshot[addr:addr + 4096:256]
        self.snapshot[addr:addr + 4096:256] = self._rotate_tile_data(tile_data)

    def _rotate_tile_data(self, tile_data):
        tile = tile_data[0:16:2]
        mask = tile_data[1:16:2]
        rotated = []
        b = 1
        while b < 129:
            rbyte = rmask = 0
            for byte, mbyte in zip(tile, mask):
                rbyte *= 2
                rbyte += 1 if byte & b else 0
                rmask *= 2
                rmask += 1 if mbyte & b else 0
            rotated.append(rbyte)
            rotated.append(rmask)
            b *= 2
        return rotated

    def place_char(self, char_num, x=None, y=None, z=None, state=None, index=0):
        z_offset = 3
        if char_num < 222:
            # For character groups 215-221, 'index' is the index (0-4) of the
            # character in the group
            base_addr = 65198 + 30 * (char_num - 215) + 6 * index
        elif char_num < 230:
            base_addr = 32 + 256 * char_num
        elif char_num == 230:
            base_addr = 256 * char_num
            z_offset = 4
        if state is not None:
            self.snapshot[base_addr] = state
        if x is not None:
            self.snapshot[base_addr + 1] = x
        if y is not None:
            self.snapshot[base_addr + 2] = y
        if z is not None:
            self.snapshot[base_addr + z_offset] = z

    def hide_chars(self):
        for char_num in range(215, 231):
            for index in range(5):
                self.place_char(char_num, z=0, index=index)

    def reset_fuses(self):
        self.snapshot[32674:32680] = [0] * 6

    def _has_light_switch(self, floor, xh):
        for f in range(1, 6):
            fixtures_addr = 62720 + 32 * (5 - f) + xh
            fixtures_flags = self.snapshot[fixtures_addr]
            if fixtures_flags & 32 or (fixtures_flags & 192 and f == floor):
                return True
        return False

    def switch_lights_on(self):
        for floor in range(1, 6):
            for i in range(32):
                if self._has_light_switch(floor, i):
                    flags_addr = 47424 + 256 * (5 - floor) + i
                    self.snapshot[flags_addr] &= 223

    def raise_blinds(self):
        for floor in range(1, 6):
            for i in range(32):
                flags_addr = 47424 + 256 * (5 - floor) + i
                window_flags = self.snapshot[flags_addr]
                fixtures_addr = 62720 + 32 * (5 - floor) + i
                fixture_flags = self.snapshot[fixtures_addr]
                blind_l = fixture_flags & 16
                blind_r = fixture_flags & 8
                blind_c = fixture_flags & 4
                if blind_l or blind_c:
                    window_flags &= 191
                if blind_r:
                    window_flags &= 254
                self.snapshot[flags_addr] = window_flags

    def close_doors(self):
        for pokes in DOORS.values():
            for addr, val in pokes:
                self.snapshot[addr] = val

    def adjust_rope(self, show=False):
        self.snapshot[47386:47388] = [9 if show else 11] * 2

def run(snafile, imgfname, options):
    snapshot = get_snapshot(snafile)
    game = ContactSamCruise(snapshot)
    x = y = 0
    width, height = 256, 42
    game.hide_chars()
    game.reset_fuses()
    game.switch_lights_on()
    game.raise_blinds()
    game.close_doors()
    game.adjust_rope(options.rope)

    if options.geometry:
        wh, xy = options.geometry.split('+', 1)
        width, height = [int(n) for n in wh.split('x')]
        x, y = [int(n) for n in xy.split('+')]

    for spec in options.place_char:
        values = []
        index = 0
        for n in spec.split(','):
            if not values and '.' in n:
                n, i = n.split('.', 1)
                try:
                    index = int(i)
                except:
                    pass
            try:
                values.append(int(n))
            except ValueError:
                values.append(None)
        game.place_char(*values[:5], index=index)

    for spec in options.pokes:
        addr, val = spec.split(',', 1)
        step = 1
        if '-' in addr:
            addr1, addr2 = addr.split('-', 1)
            addr1 = int(addr1)
            if '-' in addr2:
                addr2, step = [int(i) for i in addr2.split('-', 1)]
            else:
                addr2 = int(addr2)
        else:
            addr1 = int(addr)
            addr2 = addr1
        addr2 += 1
        value = int(val)
        for a in range(addr1, addr2, step):
            snapshot[a] = value

    udg_array = game.get_play_area_udgs(x, y, width, height)
    frame = Frame(udg_array, options.scale)
    image_writer = ImageWriter()
    image_format = 'gif' if imgfname.lower()[-4:] == '.gif' else 'png'
    with open(imgfname, "wb") as f:
        image_writer.write_image([frame], f, image_format)

###############################################################################
# Begin
###############################################################################
parser = argparse.ArgumentParser(
    usage='cscimage.py [options] FILE.{png,gif}',
    description="Create an image of the play area in Contact Sam Cruise.",
    formatter_class=argparse.RawTextHelpFormatter,
    add_help=False
)
parser.add_argument('imgfname', help=argparse.SUPPRESS, nargs='?')
group = parser.add_argument_group('Options')
group.add_argument('-c', dest='place_char', metavar='C[.N],X,Y,Z[,S]', action='append', default=[],
                   help="Place character C[.N] at (X,Y,Z) with animatory state S\n"
                        "(this option may be used multiple times); if X, Y or Z is\n"
                        "blank, that coordinate is left unchanged\n"
                        "  230: Sam                     225: Fat man; Lana\n"
                        "  229: Banknote; hook          224: Gangster\n"
                        "  228: Banknote                223: Policeman\n"
                        "  227: Sniper                  222: Policeman\n"
                        "  226: Daisy           215.0-221.4: Various")
group.add_argument('-g', dest='geometry', metavar='WxH+X+Y',
                   help='Create an image with this geometry')
group.add_argument('-p', dest='pokes', metavar='A[-B[-C]],V', action='append', default=[],
                   help="Do POKE N,V for N in {A, A+C, A+2C,...B} (this option may\n"
                        "be used multiple times)")
group.add_argument('-r', dest='rope', action="store_true",
                   help='Display the rope over no. 19')
group.add_argument('-s', dest='scale', type=int, default=2,
                   help='Set the scale of the image (default: 2)')
namespace, unknown_args = parser.parse_known_args()
if unknown_args or not namespace.imgfname:
    parser.exit(2, parser.format_help())
run(CSC_Z80, namespace.imgfname, namespace)
