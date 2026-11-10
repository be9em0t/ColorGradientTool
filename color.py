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


def format_color_line(hex_color, format_type):
    """Format one hex color as a single text line in the given format.

    The same lines are used for the list boxes and for Copy colors, so what
    you see is exactly what you copy. Raises ValueError for an unknown format.
    """
    r01 = hex_to_rgb01(hex_color)
    if format_type == "Hex":
        return parse_hex_string(hex_color)
    if format_type == "RGB 256":
        return format_rgb256_from_tuple(tuple(int(round(x * 255)) for x in r01))
    if format_type == "RGB 0-1":
        return format_rgb01_from_tuple(r01)
    raise ValueError(f"Unknown color format: {format_type!r}")


def format_color_list(colors, format_type):
    """Convert a list of hex colors to a list of text lines in the given format."""
    return [format_color_line(c, format_type) for c in colors]


# Friendly/internal model key -> ColorAide space id.
# 'srgb' is plain gamma-encoded sRGB (what most tools call "RGB interpolation");
# 'srgb-linear' is physically additive light.
INTERPOLATION_SPACES = {
    'oklch': 'oklch',
    'oklab': 'oklab',
    'lch': 'lch',
    'lab': 'lab',
    'hsl': 'hsl',
    'hwb': 'hwb',
    'srgb': 'srgb',
    'srgb-linear': 'srgb-linear',
}


def interpolate(hex_a, hex_b, steps, mode):
    """Return `steps` hex colors from hex_a to hex_b, interpolated in `mode`.

    - Cylindrical spaces take the shortest hue path; ColorAide knows where hue
      lives in each space and treats neutral (hue-less) colors correctly.
    - The first and last colors are always exactly the requested endpoints.
    - Out-of-gamut results are gamut-mapped into sRGB.
    - Nothing is swallowed: bad input or a failure raises ValueError, so the
      caller can show it instead of displaying wrong colors.
    """
    if steps < 2:
        raise ValueError(f"A gradient needs at least 2 steps, got {steps}")
    key = str(mode).strip().lower()
    if key == 'rgb':
        key = 'srgb'
    space = INTERPOLATION_SPACES.get(key)
    if space is None:
        raise ValueError(f"Unknown color model: {mode!r}")

    start = parse_hex_string(hex_a)
    end = parse_hex_string(hex_b)
    try:
        ramp = Color.interpolate([start, end], space=space, hue='shorter')
        out = []
        for i in range(steps):
            c = ramp(i / (steps - 1)).convert('srgb')
            if not c.in_gamut():
                c = c.fit('srgb')
            out.append(c.to_string(hex=True))
    except Exception as ex:
        raise ValueError(f"Interpolation in {space} failed: {ex}") from ex

    # Pin the endpoints so rounding can never alter the colors the user chose.
    out[0] = start
    out[-1] = end
    return out


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


# ========== INPUT ADAPTER FUNCTIONS ==========
# These functions handle various popular color input formats with different delimiters and brackets

class ColorInputAdapter:
    """
    Input adapter for handling various popular color formatting patterns.
    Supports multiple delimiters and bracket formats without modifying existing parsing logic.
    """
    
    @staticmethod
    def parse_hex_input(input_text):
        """
        Parse hex color input with various delimiters.
        Colors are delimited by: newline, comma+newline, semicolon+newline
        Formats: #rrggbb or rrggbb
        
        Examples:
        - "#288ceb\n#a778ae\n#e15e1e"
        - "288ceb,\na778ae,\ne15e1e"
        - "#288ceb;\n#a778ae;\n#e15e1e"
        """
        if not input_text or not input_text.strip():
            return []
        
        # Split by color delimiters: newline, comma+newline, semicolon+newline
        import re
        # Split on: newline OR comma followed by newline OR semicolon followed by newline
        colors = re.split(r'(?:,\s*\n|\;\s*\n|\n)', input_text.strip())
        
        # Clean and validate each color
        cleaned_colors = []
        for line_no, color in enumerate(colors, start=1):
            color = color.strip().rstrip(',;')  # Remove trailing delimiters
            if not color:  # blank lines are harmless separators
                continue
            try:
                cleaned_colors.append(parse_hex_string(color))
            except ValueError:
                # Never drop a color silently: reject the whole input.
                raise ValueError(f"line {line_no}: {color!r} is not a valid hex color") from None

        return cleaned_colors
    
    @staticmethod
    def parse_rgb_input(input_text, is_rgb256=True):
        """
        Parse RGB color input with various formats and delimiters.
        
        Supported formats:
        - Bare-bones: 0.157, 0.549, 0.922 (newline delimiter only)
        - Parentheses: (0.157, 0.549, 0.922)
        - Brackets: [0.157, 0.549, 0.922]  
        - Braces: {0.157, 0.549, 0.922}
        - RGB with parentheses: rgb(0.157, 0.549, 0.922)
        - RGB with brackets: rgb[0.157, 0.549, 0.922]
        - RGB with braces: rgb{0.157, 0.549, 0.922}
        
        Color delimiters (colors are separated by):
        - newline
        - comma+newline  
        - semicolon+newline
        
        Args:
            input_text: Input string containing RGB values
            is_rgb256: True for 0-255 range, False for 0-1 range
        """
        if not input_text or not input_text.strip():
            return []
        
        import re
        
        # Split by color delimiters: newline, comma+newline, semicolon+newline
        # Split on: newline OR comma followed by newline OR semicolon followed by newline
        lines = re.split(r'(?:,\s*\n|\;\s*\n|\n)', input_text.strip())
        
        cleaned_colors = []
        for line_no, line in enumerate(lines, start=1):
            line = line.strip().rstrip(',;')  # Remove trailing delimiters
            if not line:  # blank lines are harmless separators
                continue

            rgb_values = ColorInputAdapter._extract_rgb_values(line)
            if not rgb_values or len(rgb_values) != 3:
                raise ValueError(f"line {line_no}: {line!r} is not three numbers")
            try:
                if is_rgb256:
                    # RGB 256 takes whole numbers only; 255.9 is rejected, not truncated.
                    if any('.' in v for v in rgb_values):
                        raise ValueError("RGB 256 values must be whole numbers")
                    vals = tuple(int(v) for v in rgb_values)
                    if not all(0 <= v <= 255 for v in vals):
                        raise ValueError("RGB 256 values must be 0-255")
                else:
                    vals = tuple(float(v) for v in rgb_values)
                    if not all(0.0 <= v <= 1.0 for v in vals):
                        raise ValueError("RGB 0-1 values must be between 0 and 1")
            except ValueError as ex:
                raise ValueError(f"line {line_no}: {line!r}: {ex}") from None
            cleaned_colors.append(vals)

        return cleaned_colors
    
    @staticmethod
    def _extract_rgb_values(line):
        """
        Extract RGB numeric values from a line with various bracket formats.
        Returns list of 3 numeric strings or None if not found.
        """
        import re
        
        # Pattern to match RGB values in various formats:
        # - rgb(1, 2, 3) or RGB(1, 2, 3)
        # - rgb[1, 2, 3] or RGB[1, 2, 3]  
        # - rgb{1, 2, 3} or RGB{1, 2, 3}
        # - (1, 2, 3)
        # - [1, 2, 3]
        # - {1, 2, 3}
        # - 1, 2, 3 (bare-bones)
        
        # Try RGB prefix patterns first (case insensitive)
        rgb_patterns = [
            r'(?i)rgb\s*\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)',  # rgb(r,g,b)
            r'(?i)rgb\s*\[\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\]',  # rgb[r,g,b]
            r'(?i)rgb\s*\{\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\}',  # rgb{r,g,b}
        ]
        
        for pattern in rgb_patterns:
            match = re.search(pattern, line)
            if match:
                return [match.group(1), match.group(2), match.group(3)]
        
        # Try bracket patterns without rgb prefix
        bracket_patterns = [
            r'\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)',  # (r,g,b)
            r'\[\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\]',  # [r,g,b]
            r'\{\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\}',  # {r,g,b}
        ]
        
        for pattern in bracket_patterns:
            match = re.search(pattern, line)
            if match:
                return [match.group(1), match.group(2), match.group(3)]
        
        # Try bare-bones format (just numbers and commas)
        bare_pattern = r'^\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*$'
        match = re.match(bare_pattern, line)
        if match:
            return [match.group(1), match.group(2), match.group(3)]
        
        return None