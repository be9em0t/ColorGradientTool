# color.py
# Color space conversions, interpolation algorithms, and color utilities
# Extracted from ColorGradientTool.py

import math
from coloraide import Color
import colorsys

# Utility: proper sRGB <-> linear sRGB conversions (IEC 61966-2-1)
def srgb_comp_to_linear(c):
    # c in [0,1]
    if c <= 0.04045:
        return c / 12.92
    else:
        return ((c + 0.055) / 1.055) ** 2.4


def linear_comp_to_srgb(c):
    # c in [0,1]
    if c <= 0.0031308:
        return 12.92 * c
    else:
        return 1.055 * (c ** (1 / 2.4)) - 0.055


def hex_to_rgb01(hexstr):
    hexstr = hexstr.lstrip('#')
    r = int(hexstr[0:2], 16) / 255.0
    g = int(hexstr[2:4], 16) / 255.0
    b = int(hexstr[4:6], 16) / 255.0
    return (r, g, b)


def rgb01_to_hex(rgb):
    r, g, b = rgb
    return '#{:02x}{:02x}{:02x}'.format(
        max(0, min(255, int(round(r * 255)))),
        max(0, min(255, int(round(g * 255)))),
        max(0, min(255, int(round(b * 255))))
    )


def lerp(a, b, t):
    return a + (b - a) * t


def shortest_angle_interp(a1, a2, t):
    # a1, a2 in degrees [0, 360)
    d = ((a2 - a1 + 180) % 360) - 180
    return (a1 + d * t) % 360


def hex_to_rgb256(hex_color):
    """Convert hex color to RGB 256 format (0-255)"""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgb({r}, {g}, {b})"


def parse_rgb01_string(s):
    """Parse '0.123, 0.234, 0.345' or '.12, .23, 1' into (r,g,b) floats 0-1"""
    parts = [p.strip() for p in s.split(',')]
    if len(parts) != 3:
        raise ValueError('Expected three components')
    vals = []
    for p in parts:
        if p == '':
            raise ValueError('Empty component')
        v = float(p)
        if not (0.0 <= v <= 1.0):
            raise ValueError('Component out of range')
        vals.append(v)
    return tuple(vals)


def parse_rgb256_string(s):
    """Parse '0, 24, 255' into (r,g,b) ints 0-255"""
    parts = [p.strip() for p in s.split(',')]
    if len(parts) != 3:
        raise ValueError('Expected three components')
    vals = []
    for p in parts:
        if p == '':
            raise ValueError('Empty component')
        v = int(p)
        if not (0 <= v <= 255):
            raise ValueError('Component out of range')
        vals.append(v)
    return tuple(vals)


def parse_hex_string(s):
    """Parse hex like '#F8F623' or 'F8F623' into normalized '#rrggbb' lowercase"""
    h = s.strip().lstrip('#')
    if len(h) == 3:
        # expand shorthand
        h = ''.join(c*2 for c in h)
    if len(h) != 6:
        raise ValueError('Hex must be 6 digits')
    int(h, 16)  # validate
    return '#' + h.lower()


def format_rgb01_from_tuple(t):
    # format numbers with up to 5 decimals, strip trailing zeros, drop leading zero
    def fmt(v):
        # Keep a leading zero for values like 0.335 (do not drop the leading 0)
        s = f"{v:.5f}".rstrip('0').rstrip('.')
        return s
    return ', '.join(fmt(x) for x in t)


def format_rgb256_from_tuple(t):
    return ', '.join(str(int(x)) for x in t)


def hex_to_rgb01_string(hex_color):
    """Convert hex color to RGB 0-1 format string"""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return f"rgb({r:.3f}, {g:.3f}, {b:.3f})"


def format_color_list(colors, format_type):
    """Convert a list of hex colors to the specified format"""
    if format_type == "Hex":
        return colors
    elif format_type == "RGB 256":
        return [hex_to_rgb256(color) for color in colors]
    elif format_type == "RGB 0-1":
        return [hex_to_rgb01_string(color) for color in colors]
    else:
        return colors


CYLINDRICAL_SPACES = {'lch', 'oklch', 'hsl', 'hwb', 'hsv'}


def interpolate_coloraide(hex_a, hex_b, steps, space):
    """
    General-purpose interpolation using coloraide.
    space: e.g. 'oklch', 'oklab', 'lch', 'lab', 'hsl', 'hwb', 'srgb'
    Returns list of hex strings length == steps
    """
    ca = Color(hex_a)
    cb = Color(hex_b)
    # Convert endpoints into desired space
    a_conv = ca.convert(space)
    b_conv = cb.convert(space)

    a_coords = list(a_conv.coords())
    b_coords = list(b_conv.coords())

    out = []
    is_cyl = space.lower() in CYLINDRICAL_SPACES
    hue_index = (len(a_coords) - 1) if is_cyl else None

    for i in range(steps):
        t = i / (steps - 1) if steps > 1 else 0
        coords = []
        for j in range(len(a_coords)):
            if j == hue_index:
                a_h = (a_coords[j] % 360)
                b_h = (b_coords[j] % 360)
                h = shortest_angle_interp(a_h, b_h, t)
                coords.append(h)
            else:
                coords.append(lerp(a_coords[j], b_coords[j], t))
        try:
            c = Color(space, coords)
            # Fit to sRGB if out of gamut for display
            if not c.in_gamut('srgb'):
                c = c.fit('srgb')
            hex_out = c.convert('srgb').to_string(hex=True)
            out.append(hex_out)
        except Exception:
            # fallback to endpoints if something fails
            out.append(hex_a if t < 0.5 else hex_b)
    return out


def interpolate_srgb_linear(hex_a, hex_b, steps):
    """
    Interpolate in linear sRGB space (physically additive) using correct sRGB linearization.
    """
    ar, ag, ab = hex_to_rgb01(hex_a)
    br, bg, bb = hex_to_rgb01(hex_b)
    la = (srgb_comp_to_linear(ar), srgb_comp_to_linear(ag), srgb_comp_to_linear(ab))
    lb = (srgb_comp_to_linear(br), srgb_comp_to_linear(bg), srgb_comp_to_linear(bb))
    out = []
    for i in range(steps):
        t = i / (steps - 1) if steps > 1 else 0
        lr = lerp(la[0], lb[0], t)
        lg = lerp(la[1], lb[1], t)
        lbv = lerp(la[2], lb[2], t)
        r = linear_comp_to_srgb(lr)
        g = linear_comp_to_srgb(lg)
        b = linear_comp_to_srgb(lbv)
        out.append(rgb01_to_hex((r, g, b)))
    return out


def interpolate(hex_a, hex_b, steps, mode):
    m = mode.lower()
    if m == 'srgb' or m == 'rgb':
        return interpolate_srgb_linear(hex_a, hex_b, steps)
    # For everything else use coloraide's conversions and fitting
    # Map friendly names to coloraide spaces
    mapping = {
        'oklch': 'oklch',
        'oklab': 'oklab',
        'lch': 'lch',
        'lab': 'lab',
        'hsl': 'hsl',
        'hwb': 'hwb',
    }
    space = mapping.get(m, m)
    return interpolate_coloraide(hex_a, hex_b, steps, space)


class ColorParser:
    """Static class for parsing color format lines"""
    
    @staticmethod
    def parse_hex_lines(lines):
        out_hex = []
        out_rgb256 = []
        out_rgb01 = []
        for line in lines:
            hx = parse_hex_string(line)
            out_hex.append(hx)
            r01 = hex_to_rgb01(hx)
            out_rgb01.append(format_rgb01_from_tuple(r01))
            out_rgb256.append(format_rgb256_from_tuple(tuple(int(round(x*255)) for x in r01)))
        return out_hex, out_rgb256, out_rgb01

    @staticmethod
    def parse_rgb256_lines(lines):
        out_hex = []
        out_rgb256 = []
        out_rgb01 = []
        for line in lines:
            vals = parse_rgb256_string(line)
            # ensure each component is in 0-255 (parse_rgb256_string already checks)
            out_rgb256.append(format_rgb256_from_tuple(vals))
            r01 = tuple(v/255.0 for v in vals)
            out_rgb01.append(format_rgb01_from_tuple(r01))
            out_hex.append(rgb01_to_hex(r01))
        return out_hex, out_rgb256, out_rgb01

    @staticmethod
    def parse_rgb01_lines(lines):
        out_hex = []
        out_rgb256 = []
        out_rgb01 = []
        for line in lines:
            vals = parse_rgb01_string(line)
            # ensure floats within [0,1] (parse_rgb01_string checks)
            out_rgb01.append(format_rgb01_from_tuple(vals))
            out_rgb256.append(format_rgb256_from_tuple(tuple(int(round(v*255)) for v in vals)))
            out_hex.append(rgb01_to_hex(vals))
        return out_hex, out_rgb256, out_rgb01