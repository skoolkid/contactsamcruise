# -*- coding: utf-8 -*-

# Copyright 2008-2015 Richard Dymond (rjdymond@gmail.com)
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.

import cgi

try:
    from .skoolhtml import Udg as BaseUdg, HtmlWriter, join
    from .skoolasm import AsmWriter
    from .skoolmacro import parse_ints, parse_params, MacroParsingError, UnsupportedMacroError
except (ValueError, SystemError, ImportError):
    from skoolkit.skoolhtml import Udg as BaseUdg, HtmlWriter, join
    from skoolkit.skoolasm import AsmWriter
    from skoolkit.skoolmacro import parse_ints, parse_params, MacroParsingError, UnsupportedMacroError

# Sniper's animatory state
SNIPER_AS = 54

class ContactSamCruiseHtmlWriter(HtmlWriter):
    def init(self):
        self.char_buf_descs = self._get_char_buf_descs()
        self.keypress_routines = self.get_dictionary('KeypressRoutines')
        self.as_descs = self.get_dictionary('AnimatoryStates')
        self.characters = self.get_dictionary('Characters')
        self.font = {
            48: (124, 138, 146, 124),
            49: (66, 254, 2),
            50: (70, 138, 146, 98),
            51: (130, 146, 178, 204),
            52: (56, 72, 254, 8),
            53: (242, 146, 146, 140),
            54: (124, 146, 146, 140),
            55: (128, 134, 152, 224),
            56: (108, 146, 146, 108),
            57: (98, 146, 146, 124)
        }
        self.tap_descs = self._get_tap_descs()
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

    def _get_sprite_udg(self, state, attr, ref_page, udg_page):
        ref_addr = state + 256 * ref_page
        ref = self.snapshot[ref_addr]
        if ref == 0:
            # These must be lists so that the UDG can be flipped or rotated
            # in-place
            udg = [0, 0, 0, 0, 0, 0, 0, 0]
            mask = [255, 255, 255, 255, 255, 255, 255, 255]
        else:
            udg_addr = ref + 256 * udg_page
            udg = self.snapshot[udg_addr:udg_addr + 4096:512]
            mask = self.snapshot[udg_addr + 256:udg_addr + 4352:512]
        return Udg(attr, udg, mask, ref_addr=ref_addr, ref=ref, udg_page=udg_page)

    def get_chr(self, code):
        if code == 127:
            return '&#169;'
        if code == 94:
            return '&#8593;'
        if code == 96:
            return '&#163;'
        return cgi.escape(chr(code))

    def build_sprite(self, state, attr=None, udg_page=None):
        width, height = self._get_sprite_size(state)
        udg_array = []
        for row in range(height):
            udg_array.append([self.get_sprite_udg(state, attr, row, col, udg_page) for col in range(width)])
        return udg_array

    def get_text(self, words):
        columns = []
        for character in words:
            columns.append(0)
            columns.extend(self.get_font_bitmap(character))
        udg_array = []
        for col in range(len(columns)):
            col_byte = columns[col]
            udg_index = col // 8
            bit = 2**(7 - (col - 8 * udg_index))
            if udg_index == len(udg_array):
                udg_array.append([0] * 8)
            udg = udg_array[udg_index]
            for b in range(8):
                udg[7 - b] |= bit * (col_byte & 1)
                col_byte //= 2
        return udg_array

    def _draw_text(self, udgs, words, x, y):
        text_udgs = self.get_text(words)
        for col in range(len(text_udgs)):
            udg = udgs[y][col + x].data
            for index in range(8):
                udg[index] |= text_udgs[col][index]

    def get_skool_udgs(self, x, y, w, h, show_chars=False, show_x=0):
        skool_udgs = []
        for row in range(y, y + h):
            skool_udgs.append([])
            for col in range(x, x + w):
                skool_udgs[-1].append(self.get_skool_udg(row, col, show_chars))
        if show_chars:
            self._superimpose_sprite_udgs(skool_udgs, x, y, w, h)
        if show_x is not None and show_x > 0:
            line = [Udg(8 * (7 - skool_x % 2), [0] * 8) for skool_x in range(x, x + w)]
            for skool_x in range(x, x + w):
                if skool_x % show_x == 0:
                    self._draw_text([line], str(skool_x), skool_x - x, 0)
            skool_udgs.insert(0, line)
            skool_udgs.append(line)
        return skool_udgs

    def _get_char_buf_descs(self):
        char_buf_descs = []
        for byte_nums, descs in self.get_sections('CharBuf', True):
            char_buf_descs.append((byte_nums, descs))
        return char_buf_descs

    def as_img(self, cwd, num, scale=2, mask=1, attr=120, udg_page=None, fname_suffix=''):
        mask_infix = 'm' if mask else 'u'
        udg_page_infix = udg_page if udg_page is not None else ''
        snapshot_name = self.get_snapshot_name()
        snapshot_infix = '_{0}'.format(snapshot_name) if snapshot_name else ''
        fname = 'as{0:03d}_{1}x{2}{3}{4}{5}{6}'.format(num & 255, attr, scale, mask_infix, udg_page_infix, snapshot_infix, fname_suffix)
        asimg_path = self.image_path(fname, 'AnimatoryStateImagePath')
        if self.need_image(asimg_path):
            self.write_image(asimg_path, self.build_sprite(num, attr, udg_page), scale=scale, mask=mask)
        return self.img_element(cwd, asimg_path, "Animatory state {0}".format(num & 255))

    def animatory_states(self, cwd):
        return '\n'.join([self._animatory_state_row(cwd, n) for n in range(128)])

    def astiles(self, cwd):
        rows = []
        attr = 120
        for n in range(128):
            for state_specs, states_desc in self._get_animatory_state_tiles_row(n):
                frames = []
                for state, udg_page in state_specs:
                    tiles = []
                    sprite = self.build_sprite(state, attr, udg_page)
                    num_rows = len(sprite)
                    for row_num in range(num_rows):
                        row = sprite[row_num]
                        for col_num in range(len(row)):
                            tile = row[col_num]
                            bubble_id_suffix = '{0:02x}'.format(udg_page) if udg_page is not None else ''
                            bubble_id = 'B{0:02x}{1:x}{2}'.format(state, row_num + num_rows * col_num, bubble_id_suffix)
                            img_fname = self._get_sprite_tile_img_fname(tile, state)
                            img_path = join(cwd, img_fname)
                            if self.need_image(img_path):
                                self.write_image(img_path, [[tile]], scale=4, mask=1)
                            template_name = 'astile' if tile.ref else 'astile_null'
                            astile_subs = {
                                'bubble_id': bubble_id,
                                'state': state,
                                'row': row_num,
                                'column': col_num,
                                'img_fname': img_fname,
                                'lsb': tile.ref_addr % 256,
                                'ref_page': tile.ref_addr // 256,
                                'tile': tile
                            }
                            tiles.append(self.format_template(template_name, astile_subs))
                    template_name = 'astiles_frame_{}x{}'.format(num_rows, len(row))
                    frames.append(self.format_template(template_name, {'tiles': tiles}))
                astiles_row_subs = {'frames': '\n'.join(frames), 'desc': states_desc}
                rows.append(self.format_template('astiles_row', astiles_row_subs))
        return '\n'.join(rows)

    def cast(self, cwd):
        return self.format_template('cast', {'characters': self.characters})

    def cbuffer(self, cwd):
        cbuffer_bytes = []
        for byte_nums, entries in self.char_buf_descs:
            descs = [self.format_template('cbuffer_desc', {'desc': entry}) for entry in entries]
            row_descs = [self.format_template('cbuffer_desc_row', {'t_cbuffer_desc': desc}) for desc in descs[1:]]
            subs = {
                'rowspan': len(descs),
                'bytes': byte_nums,
                't_cbuffer_desc': descs[0],
                'm_cbuffer_desc_row': '\n'.join(row_descs)
            }
            cbuffer_bytes.append(self.format_template('cbuffer_bytes', subs))
        return self.format_template('cbuffer', {'m_cbuffer_bytes': '\n'.join(cbuffer_bytes)})

    def _get_tap_descs(self):
        tap_descs = {}
        prefix = 'Command list:'
        for entry in self.memory_map:
            title = entry.description
            if title.startswith(prefix):
                tap_descs[entry.address] = title[len(prefix):].strip()
        return tap_descs

    def get_skool_udg(self, y, x, show_chars=False):
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
                if self.snapshot[k + 32512]:
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
            if show_chars:
                # Create a foreground UDG that can be superimposed later
                fg_udg = Udg(0, fg_data, fg_mask)
            else:
                # Otherwise superimpose the foreground tile now
                for i in range(8):
                    data[i] = (data[i] | fg_data[i]) & fg_mask[i]
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
        initial_states += [self.snapshot[a:a + 4] for a in range(56870, 58918, 256)]
        sam_z = self.snapshot[58884]
        if sam_z == 0:
            sam_as, sam_x, sam_y, sam_z = 0, 229, 19, 1
        else:
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
                            # This location has an opaque foreground tile,
                            # so don't superimpose characters with z=1
                            continue
                        sprite_udg = self.get_sprite_udg(state, None, udg.y - char_y, udg.x - char_x)
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

    def get_sprite_udg(self, state, attr, row, col, udg_page=None):
        width, height = self._get_sprite_size(state)
        udg_page = 199
        col = width - 1 - col if state & 128 else col
        tile_num = col * height + row
        ref_page = 215 + tile_num

        do_pop = False
        if state & 1919 in self.sniper_states:
            do_pop = True
            self.push_snapshot()
            phase = self.sniper_states.index(state & 1919)
            self._prep_sniper_sprite(phase, tile_num)
            state = SNIPER_AS + (state & 128)
        elif state & 127 in (7, 23, 39, 55, 63, 71, 79, 87, 95, 103, 111, 119):
            do_pop = True
            self.push_snapshot()
            self._prep_knocked_out_sprite(state, tile_num)
        elif state & 127 in (9, 10, 15, 31):
            do_pop = True
            self.push_snapshot()
            self._prep_sam_sprite(state, tile_num)

        as_norm = (state if state & 7 else state + 2) | 128
        udg = self._get_sprite_udg(as_norm, attr, ref_page, udg_page)
        if state & 128:
            udg.flip()

        if do_pop:
            self.pop_snapshot()
        return udg

    def get_font_bitmap(self, character):
        return self.font.get(ord(character), (255, 255, 255, 255))

    def keypress_table_rows(self, cwd):
        rows = []
        for index in range(80):
            address = index + 49968
            offset = self.snapshot[address]
            lookup = routine_link = purpose = ''
            if offset:
                lookup = offset + 60671
                routine = self.snapshot[lookup] + 256 * self.snapshot[lookup + 1]
                routine_link = '#R{}'.format(routine)
                purpose = self.keypress_routines[routine]
            subs = {
                'index': index,
                'key': self.get_chr(index + 48),
                'address': address,
                'offset': offset,
                'lookup': lookup,
                'routine': routine_link,
                'purpose': purpose
            }
            rows.append(self.format_template('keypress_table_row', subs))
        return '\n'.join(rows)

    def play_area(self, cwd, fname, x, y, w=1, h=1, scale=2, show_chars=0, show_x=0, game_mode=None, lights=1, blinds=1):
        img_path = self.image_path(fname, 'PlayAreaImagePath')
        if self.need_image(img_path):
            self.push_snapshot()
            if show_chars and game_mode is not None:
                self._initialise_characters(game_mode)
            if lights or blinds:
                self._adjust_lights_and_blinds(lights, blinds)
            self.write_image(img_path, self.get_skool_udgs(x, y, w, h, show_chars, show_x), scale=scale)
            self.pop_snapshot()
        return self.img_element(cwd, img_path)

    def ld_img(self, cwd, sam_x=None, sam_y=None, sam_z=None, sam_as=None, x=None, y=None, w=None, h=None):
        self.push_snapshot()
        self.hide_chars()
        self.place_char(cwd, 230, sam_x, sam_y, sam_z, sam_as)
        sam_x, sam_y = self.snapshot[58881:58883]
        ld_img_fname = 'ld-{0}-{1}-{2}'.format(sam_x, sam_y, sam_z)
        w = 7 if w is None else w
        h = 8 if h is None else h
        x = min(max(sam_x - 2, 0), 256 - w) if x is None else x
        y = min(max(sam_y - 1, 0), 40 - h) if y is None else y
        html = self._write_ld_img(cwd, ld_img_fname, x, y, w, h)
        self.pop_snapshot()
        return html

    def ldz4_img(self, cwd, x0, w):
        self.push_snapshot()
        self.hide_chars()
        y0 = self._get_y_coord(x0)
        self.place_char(cwd, 230, x0, y0, 4, 128)
        x1 = x0 + w - 1
        y1 = self._get_y_coord(x1)
        self.place_char(cwd, 229, x1, y1, 4, 0)
        ldz4_img_fname = 'ld-x{0}-x{1}-4'.format(x0, x1)
        width = min(w + 2, 256 - x0)
        html = self._write_ld_img(cwd, ldz4_img_fname, x0, 31, width, 9)
        self.pop_snapshot()
        return html

    def _get_y_coord(self, x):
        """Return the y-coordinate of a character on the sidewalk or road with
        the given x-coordinate."""
        if x <= 6 or 15 <= x <= 163 or x >= 199:
            return 34
        return 35

    def _write_ld_img(self, cwd, fname, x, y, w, h):
        img_path = self.image_path(fname, 'LocationDescriptorImagePath')
        if self.need_image(img_path):
            self._adjust_lights_and_blinds(1, 1)
            udgs = self.get_skool_udgs(x, y, w, h, True)
            self.write_image(img_path, udgs, scale=2)
        return self.img_element(cwd, img_path)

    def play_area_objects(self, cwd, fname, x=0, y=2, w=256, h=38, scale=2, show_chars=0, show_x=8):
        img_path = self.image_path(fname, 'PlayAreaImagePath')
        if self.need_image(img_path):
            udgs = self.get_skool_udgs(x, y, w, h, show_chars, show_x)
            self._add_objects(udgs, x, y, show_x)
            self.write_image(img_path, udgs, scale=scale)
        return self.img_element(cwd, img_path)

    def command_lists(self, cwd):
        rows = []
        for address, description in sorted(self.tap_descs.items()):
            subs = {'address': address, 'description': description}
            rows.append(self.format_template('command_list', subs))
        return '\n'.join(rows)

    def place_char(self, cwd, char_num, x=None, y=None, z=None, state=None, mode=1):
        z_offset = 3
        if char_num < 222:
            # For character groups 215-221, 'mode' is the index (0-4) of the
            # character in the group
            base_addr = 65198 + 30 * (char_num - 215) + 6 * mode
        elif char_num < 230:
            base_addr = 32 + 256 * char_num + 6 * mode
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

    def hide_chars(self, cwd=None):
        for char_num in range(215, 231):
            for mode in range(5):
                self.place_char(cwd, char_num, z=0, mode=mode)

    def _has_light_switch(self, floor, xh):
        for f in range(1, 6):
            fixtures_addr = 62720 + 32 * (5 - f) + xh
            fixtures_flags = self.snapshot[fixtures_addr]
            if fixtures_flags & 32 or (fixtures_flags & 192 and f == floor):
                return True
        return False

    def _adjust_lights_and_blinds(self, lights, blinds):
        for floor in range(1, 6):
            for i in range(32):
                flags_addr = 47424 + 256 * (5 - floor) + i
                window_flags = self.snapshot[flags_addr]
                if self._has_light_switch(floor, i):
                    if lights == 1:
                        window_flags &= 223
                    elif lights > 1:
                        window_flags |= 32
                if blinds:
                    fixtures_addr = 62720 + 32 * (5 - floor) + i
                    fixture_flags = self.snapshot[fixtures_addr]
                    blind_l = fixture_flags & 16
                    blind_r = fixture_flags & 8
                    blind_c = fixture_flags & 4
                    if blinds == 1:
                        if blind_l or blind_c:
                            window_flags &= 191
                        if blind_r:
                            window_flags &= 254
                    elif blinds > 1:
                        if blind_l or blind_c:
                            window_flags |= 64
                        if blind_r:
                            window_flags |= 1
                self.snapshot[flags_addr] = window_flags

    def _initialise_characters(self, game_mode):
        for a in range(56870, 58918, 256):
            init_addr = a + 6 * (game_mode - 1)
            self.snapshot[a:a + 4] = self.snapshot[init_addr:init_addr + 4]

        sam_init_addr = 58913 + 6 * game_mode
        srb_lsb, x, y = self.snapshot[sam_init_addr:sam_init_addr + 3]
        sam_as = 0
        sam_x = 8 * (srb_lsb & 3) + 5 + x
        sam_y = ((srb_lsb - 12) & 252) // 4 + y
        sam_z = 1
        self.snapshot[58880:58883] = [sam_as, sam_x, sam_y]
        self.snapshot[58884] = sam_z

    def _get_icon(self, x, y, w, h, attr=None):
        udgs = self.screenshot(x, y, w, h)
        if attr is not None:
            for row in udgs:
                for udg in row:
                    udg.attr = attr
        return udgs

    def _add_icons(self, udgs, x, y, show_x, icon, locations):
        w = len(udgs[0])
        h = len(udgs)
        for obj_x, obj_y in locations:
            for row in range(len(icon)):
                for col in range(len(icon[0])):
                    x0 = obj_x - x + col
                    y0 = obj_y - y + row
                    if show_x > 0:
                        y0 += 1
                    if 0 <= x0 < w and 0 <= y0 < h:
                        udgs[y0][x0] = icon[row][col]

    def _add_objects(self, udgs, x, y, show_x):
        # Add telephones
        phone_icon = self._get_icon(14, 21, 2, 2, 16)
        phone_locs = []
        for floor in range(1, 6):
            for x0 in range(32):
                flags_addr = 62720 + 32 * (5 - floor) + x0
                if self.snapshot[flags_addr] & 2:
                    phone_x = 3 + 8 * x0
                    phone_y = 7 + 6 * (5 - floor)
                    phone_locs.append((phone_x, phone_y))
        self._add_icons(udgs, x, y, show_x, phone_icon, phone_locs)

        # Add fuses
        fuse_icon = self._get_icon(8, 21, 2, 2, 16)
        fuse_locs = []
        for i in range(29635, 29646, 2):
            fuse_locs.append((self.snapshot[i + 1], self.snapshot[i]))
        self._add_icons(udgs, x, y, show_x, fuse_icon, fuse_locs)

        # Add keys
        key_icon = self._get_icon(16, 23, 1, 1, 16)
        key_locs = []
        for i in range(32037, 32050, 4):
            key_locs.append((self.snapshot[i], self.snapshot[i + 1] + 2))
        self._add_icons(udgs, x, y, show_x, key_icon, key_locs)

        # Add hook
        hook_icon = self._get_icon(18, 21, 2, 2, 16)
        hook_locs = [self.snapshot[32029:32031]]
        self._add_icons(udgs, x, y, show_x, hook_icon, hook_locs)

        # Add budgie
        budgie_icon = self._get_icon(16, 21, 2, 2, 16)
        budgie_locs = [self.snapshot[32033:32035]]
        self._add_icons(udgs, x, y, show_x, budgie_icon, budgie_locs)

        # Add cash bonuses
        cash_icon = [[Udg(16, (0, 8, 62, 40, 62, 10, 62, 8))]]
        cash_locs = []
        for i in range(32069, 32086, 4):
            cash_locs.append((self.snapshot[i], self.snapshot[i + 1] + 2))
        self._add_icons(udgs, x, y, show_x, cash_icon, cash_locs)

    def _get_animatory_state_tiles_row(self, state):
        states = ((state, None),)
        states_desc = '{}: {}'.format(state, self.as_descs[state])
        row = [(states, states_desc)]
        if state == SNIPER_AS:
            row += self._sniper_animatory_state_tiles_rows()
        return row

    def _sniper_animatory_state_tiles_rows(self):
        rows = []
        for state, desc, refs in self.sniper_phases:
            rows.append((((state, None),), '{0}: Sniper ({1})'.format(SNIPER_AS, desc)))
        return rows

    def _animatory_state_row(self, cwd, state):
        subs = {
            'state_l': state,
            'state_r': state + 128,
            'desc': self.as_descs.get(state, '-'),
            'img_l': self.as_img(cwd, state),
            'img_r': self.as_img(cwd, state + 128)
        }
        lines = [self.format_template('animatory_state_row', subs)]
        if state == SNIPER_AS:
            lines += self._sniper_animatory_state_rows(cwd)
        return '\n'.join(lines)

    def _sniper_animatory_state_rows(self, cwd):
        lines = []
        subs = {'state_l': SNIPER_AS, 'state_r': SNIPER_AS + 128}
        for phase, (state, desc, refs) in enumerate(self.sniper_phases):
            fname_suffix = '_{}'.format(phase + 1)
            subs['img_l'] = self.as_img(cwd, state, fname_suffix=fname_suffix)
            subs['img_r'] = self.as_img(cwd, state + 128, fname_suffix=fname_suffix)
            subs['desc'] = desc
            lines.append(self.format_template('sniper_animatory_state_row', subs))
        return lines

    def _get_sprite_tile_img_fname(self, tile, state):
        if state & 127 in (7, 9, 10, 15, 23, 31, 39, 55, 63, 71, 79, 87, 95, 103, 111, 119):
            return '{:x}_{}.{}'.format(tile.ref + 256 * tile.udg_page, state, self.default_image_format)
        return '{:x}.{}'.format(tile.udg_addr, self.default_image_format)

    def _get_disguise_tile_data(self, disguise_id, ref_index):
        ref = self.snapshot[62 + ref_index + 256 * (223 + disguise_id)]
        if ref < 126:
            addr = ref + 57088
            return self.snapshot[addr:addr + 2048:256]
        addr = ref + 55040
        return self.snapshot[addr:addr + 4096:512]

    def expand_as(self, text, index, cwd):
        # #AS[state][(link text)]
        end, state, link_text = parse_params(text, index)
        as_file = self.relpath(cwd, self.paths['AnimatoryStates'])
        anchor = '#{}'.format(state) if state else ''
        link = self.format_link(as_file + anchor, link_text or state)
        return end, link

    def expand_disguise(self, text, index, cwd):
        # #DISGUISEid[,scale][{X,Y,W,H}](fname)
        end, img_path, crop_rect, disguise_id, scale = self.parse_image_params(text, index, 2, (1,))
        if img_path is None:
            raise MacroParsingError('Filename missing: #DISGUISE{0}'.format(text[index:end]))
        if self.need_image(img_path):
            attr = 79
            ref_reps = self.snapshot[56894:56909]
            udg_array = []
            for row in ((0, 170, 0), (2, 3, 4), (183, 6, 7)):
                udg_array.append([])
                for ref in row:
                    if ref == 0:
                        udg_data = [0] * 8
                    else:
                        udg_data = self._get_disguise_tile_data(disguise_id, ref_reps.index(ref))
                    udg_array[-1].append(Udg(attr, udg_data))
            self.write_image(img_path, udg_array, crop_rect, scale)
        return end, self.img_element(cwd, img_path)

    def expand_segment(self, text, index, cwd):
        # #SEGMENTx,y[,scale][{X,Y,W,H}][(fname)]
        img_path_id = 'ScreenshotImagePath'
        end, img_path, crop_rect, x, y, scale = self.parse_image_params(text, index, 3, (1,), img_path_id)
        if img_path is None:
            img_path = self.image_path('segment-{0}-{1}'.format(x, y), img_path_id)
        if self.need_image(img_path):
            self.push_snapshot()
            self._adjust_lights_and_blinds(1, 1)
            self.write_image(img_path, self.get_skool_udgs(x, y, 8, 6), crop_rect, scale)
            self.pop_snapshot()
        return end, self.img_element(cwd, img_path)

class ContactSamCruiseAsmWriter(AsmWriter):
    def expand_as(self, text, index):
        # #AS[state][(link text)]
        end, state, link_text = parse_params(text, index)
        return end, link_text or state

    def expand_disguise(self, text, index):
        raise UnsupportedMacroError()

    def expand_segment(self, text, index):
        raise UnsupportedMacroError()

class Udg(BaseUdg):
    def __init__(self, attr, data, mask=None, attr_addr=None, ref_addr=None, ref=None, udg_page=None, x=None, y=None, fg_udg=None):
        BaseUdg.__init__(self, attr, data, mask)
        self.attr_addr = attr_addr
        self.ref_addr = ref_addr
        # We store the UDG reference now in case the snapshot changes before
        # the reference is looked up via self.snapshot[udg.ref_addr]
        self.ref = ref
        self.udg_page = udg_page
        self.udg_addr = None if udg_page is None else ref + 256 * udg_page
        self.x = x
        self.y = y
        self.fg_udg = fg_udg
