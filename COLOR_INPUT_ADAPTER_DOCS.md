# Color Input Adapter Functions - Usage Documentation

## Overview

The `ColorInputAdapter` class provides enhanced input parsing capabilities for the ColorGradientTool, allowing users to paste colors in various popular formats without worrying about exact formatting requirements.

## Key Features

- **Precise delimiters**: Colors are separated by newline, comma+newline, or semicolon+newline (never single comma to avoid confusion with commas inside color descriptions)
- **Flexible brackets**: Handles parentheses `()`, brackets `[]`, and braces `{}`
- **Case-insensitive RGB prefix**: Accepts `rgb`, `RGB`, `Rgb`, etc.
- **Backward compatibility**: Works with existing copy formats from the tool
- **Non-destructive**: Does not modify existing code - implemented as separate adapter functions

## Supported Formats

### Hex Colors

**Delimiters supported**: newline, comma+newline, semicolon+newline

**Examples**:
```
# With hash prefix
#288ceb
#a778ae
#e15e1e

# Comma+newline separated
#288ceb,
#a778ae,
#e15e1e

# Semicolon+newline separated
#288ceb;
#a778ae;
#e15e1e

# Without hash prefix
288ceb,
a778ae,
e15e1e

# Mixed format
#288ceb
a778ae
#e15e1e
```

### RGB Colors

#### RGB (0-1) Format

**Bare-bones format** (newline delimiter only):
```
0.157, 0.549, 0.922
0.655, 0.471, 0.682
0.882, 0.369, 0.118
```

**Parentheses format**:
```
(0.157, 0.549, 0.922)
(0.655, 0.471, 0.682)
(0.882, 0.369, 0.118)
```

**Brackets format**:
```
[0.157, 0.549, 0.922]
[0.655, 0.471, 0.682]
[0.882, 0.369, 0.118]
```

**Braces format**:
```
{0.157, 0.549, 0.922}
{0.655, 0.471, 0.682}
{0.882, 0.369, 0.118}
```

**RGB function formats**:
```
rgb(0.157, 0.549, 0.922)
rgb(0.655, 0.471, 0.682)
rgb(0.882, 0.369, 0.118)

rgb{0.157, 0.549, 0.922}
rgb{0.655, 0.471, 0.682}
rgb{0.882, 0.369, 0.118}

rgb[0.157, 0.549, 0.922]
rgb[0.655, 0.471, 0.682]
rgb[0.882, 0.369, 0.118]
```

**Case-insensitive RGB prefix**:
```
RGB(0.157, 0.549, 0.922)
Rgb(0.655, 0.471, 0.682)
rGB(0.882, 0.369, 0.118)
```

#### RGB (256) Format

Same bracket and function formats as RGB (0-1), but with integer values 0-255:

```
# Bare-bones
40, 140, 235
167, 120, 174
225, 94, 30

# RGB function
rgb(40, 140, 235)
rgb(167, 120, 174)
rgb(225, 94, 30)

# With semicolon+newline delimiters
rgb(40, 140, 235);
rgb(167, 120, 174);
rgb(225, 94, 30)
```

## Delimiter Rules

### Important: Comma Distinction
- **Commas inside color descriptions** (e.g., `0.157, 0.549, 0.922`) are part of the color format
- **Commas between colors** must be followed by newline (e.g., `color1,\ncolor2`)

### Hex Colors
- **All formats**: newline, comma+newline, semicolon+newline

### RGB Colors  
- **All formats**: newline, comma+newline, semicolon+newline
- Single commas without newlines are never used as color delimiters to avoid confusion with commas inside color descriptions

## API Usage

### For Hex Input
```python
from color import ColorInputAdapter

# Parse hex colors
input_text = "#288ceb, #a778ae, #e15e1e"
hex_colors = ColorInputAdapter.parse_hex_input(input_text)
# Returns: ['#288ceb', '#a778ae', '#e15e1e']
```

### For RGB Input
```python
# Parse RGB (0-1) colors
input_text = "rgb(0.157, 0.549, 0.922)\nrgb(0.655, 0.471, 0.682)"
rgb_values = ColorInputAdapter.parse_rgb_input(input_text, is_rgb256=False)
# Returns: [(0.157, 0.549, 0.922), (0.655, 0.471, 0.682)]

# Parse RGB (256) colors  
input_text = "rgb(40, 140, 235)\nrgb(167, 120, 174)"
rgb_values = ColorInputAdapter.parse_rgb_input(input_text, is_rgb256=True)
# Returns: [(40, 140, 235), (167, 120, 174)]
```

## Integration with Existing Code

The adapter functions return data in formats compatible with existing parsing functions:

- `parse_hex_input()` returns a list of normalized hex strings (e.g., `['#rrggbb', ...]`)
- `parse_rgb_input()` returns a list of tuples (e.g., `[(r,g,b), ...]`)

These can be directly used with existing `ColorParser` methods or converted using existing utility functions like `format_rgb01_from_tuple()` and `format_rgb256_from_tuple()`.

## Error Handling

- Invalid colors are silently skipped (no exceptions thrown)
- Empty input returns empty list
- Out-of-range values are ignored
- Malformed lines are skipped

## Backward Compatibility

The adapter functions fully support the current "Copy colors" output formats:

- **Hex**: `#288ceb\n#a778ae\n#e15e1e` ✓
- **RGB 256**: `rgb(40, 140, 235)\nrgb(167, 120, 174)\nrgb(225, 94, 30)` ✓
- **RGB 0-1**: `rgb(0.157, 0.549, 0.922)\nrgb(0.655, 0.471, 0.682)\nrgb(0.882, 0.369, 0.118)` ✓

This means users can now copy colors from the tool and paste them back into conversion boxes without formatting issues.