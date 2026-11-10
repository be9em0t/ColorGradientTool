"""Regression tests for gradient math and strict input parsing.

Run from the project root:  python -m unittest discover -s tests -t .
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from color import (  # noqa: E402
    ColorInputAdapter, format_color_line, format_color_list, interpolate,
)

MODELS = ['oklch', 'oklab', 'lch', 'lab', 'hsl', 'hwb', 'srgb', 'srgb-linear']
PAIRS = [
    ('#808080', '#ff0000'),  # neutral -> saturated (hue undefined at start)
    ('#ff0000', '#808080'),  # saturated -> neutral
    ('#ff0000', '#0000ff'),  # shortest hue path
    ('#000000', '#ffffff'),
    ('#1366db', '#d56172'),
    ('#ffffff', '#ffffff'),  # identical endpoints
]


def hue_of(hex_color):
    from coloraide import Color
    return Color(hex_color).convert('hsl')['hue']


class InterpolationTests(unittest.TestCase):
    def test_endpoints_are_exact_in_every_space(self):
        for model in MODELS:
            for a, b in PAIRS:
                for steps in (2, 3, 7, 512):
                    out = interpolate(a, b, steps, model)
                    self.assertEqual(len(out), steps)
                    self.assertEqual(out[0], a, f'{model} {a}->{b} start')
                    self.assertEqual(out[-1], b, f'{model} {a}->{b} end')

    def test_all_outputs_are_six_digit_hex(self):
        for model in MODELS:
            for a, b in PAIRS:
                for c in interpolate(a, b, 9, model):
                    self.assertRegex(c, r'^#[0-9a-f]{6}$')

    def test_hsl_hwb_red_to_blue_goes_through_magenta_not_green(self):
        for model in ('hsl', 'hwb'):
            mid = interpolate('#ff0000', '#0000ff', 3, model)[1]
            self.assertEqual(mid, '#ff00ff', model)

    def test_gamma_srgb_midpoint_is_plain_average(self):
        self.assertEqual(interpolate('#000000', '#ffffff', 3, 'srgb')[1], '#808080')

    def test_linear_srgb_midpoint_is_brighter(self):
        self.assertEqual(interpolate('#000000', '#ffffff', 3, 'srgb-linear')[1], '#bcbcbc')

    def test_neutral_start_does_not_invent_a_hue_detour(self):
        # gray -> red must stay on the gray/red side of the color wheel
        for model in ('oklch', 'lch', 'hsl', 'hwb'):
            for c in interpolate('#808080', '#ff0000', 9, model)[1:]:
                h = hue_of(c)
                self.assertTrue(h < 20 or h > 340, f'{model}: {c} hue {h}')

    def test_errors_are_raised_not_swallowed(self):
        with self.assertRaises(ValueError):
            interpolate('#ff0000', '#0000ff', 3, 'no-such-model')
        with self.assertRaises(ValueError):
            interpolate('#ff0000', 'not-a-color', 3, 'oklch')
        with self.assertRaises(ValueError):
            interpolate('#ff0000', '#0000ff', 1, 'oklch')


class FormatTests(unittest.TestCase):
    def test_line_formats(self):
        self.assertEqual(format_color_line('#1366db', 'Hex'), '#1366db')
        self.assertEqual(format_color_line('#1366db', 'RGB 256'), '19, 102, 219')
        self.assertEqual(format_color_line('#1366db', 'RGB 0-1'), '0.07451, 0.4, 0.85882')

    def test_unknown_format_raises(self):
        with self.assertRaises(ValueError):
            format_color_line('#1366db', 'CMYK')

    def test_formatted_lines_round_trip_through_the_parsers(self):
        colors = interpolate('#1366db', '#d56172', 6, 'oklch')
        self.assertEqual(
            ColorInputAdapter.parse_hex_input('\n'.join(format_color_list(colors, 'Hex'))), colors)
        rgb = ColorInputAdapter.parse_rgb_input('\n'.join(format_color_list(colors, 'RGB 256')), True)
        self.assertEqual(['#%02x%02x%02x' % t for t in rgb], colors)
        r01 = ColorInputAdapter.parse_rgb_input('\n'.join(format_color_list(colors, 'RGB 0-1')), False)
        self.assertEqual(['#%02x%02x%02x' % tuple(round(v * 255) for v in t) for t in r01], colors)


class StrictParserTests(unittest.TestCase):
    def test_invalid_hex_line_rejects_everything(self):
        with self.assertRaisesRegex(ValueError, 'line 2'):
            ColorInputAdapter.parse_hex_input('#ff0000\n#zzzzzz\n#0000ff')

    def test_invalid_rgb_line_rejects_everything(self):
        with self.assertRaisesRegex(ValueError, 'line 2'):
            ColorInputAdapter.parse_rgb_input('1, 2, 3\n4, 5\n7, 8, 9', True)

    def test_rgb256_rejects_decimals_and_out_of_range(self):
        with self.assertRaises(ValueError):
            ColorInputAdapter.parse_rgb_input('255.9, 0, 0', True)
        with self.assertRaises(ValueError):
            ColorInputAdapter.parse_rgb_input('256, 0, 0', True)

    def test_rgb01_rejects_out_of_range_and_garbage(self):
        with self.assertRaises(ValueError):
            ColorInputAdapter.parse_rgb_input('1.5, 0, 0', False)
        with self.assertRaises(ValueError):
            ColorInputAdapter.parse_rgb_input('1.2.3, 0, 0', False)

    def test_blank_lines_and_formats_still_accepted(self):
        self.assertEqual(ColorInputAdapter.parse_hex_input('#ff0000,\n\n0000ff;\n'), ['#ff0000', '#0000ff'])
        self.assertEqual(ColorInputAdapter.parse_rgb_input('rgb(1, 2, 3)\n[4, 5, 6]', True), [(1, 2, 3), (4, 5, 6)])
        self.assertEqual(ColorInputAdapter.parse_hex_input(''), [])


if __name__ == '__main__':
    unittest.main()
