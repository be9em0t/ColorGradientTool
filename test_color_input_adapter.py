# Color Input Adapter Test Examples
# This file demonstrates all the supported input formats for the ColorInputAdapter class

from color import ColorInputAdapter

def test_hex_input_formats():
    """Test various hex input formats with different delimiters"""
    
    print("=== HEX INPUT FORMAT TESTING ===\n")
    
    # Test 1: Newline delimited hex colors
    hex_newline = """#288ceb
#a778ae
#e15e1e"""
    
    print("1. Newline delimited hex colors:")
    print("Input:", repr(hex_newline))
    result = ColorInputAdapter.parse_hex_input(hex_newline)
    print("Output:", result)
    print()
    
    # Test 2: Comma delimited hex colors (comma+newline format)
    hex_comma = "#288ceb,\n#a778ae,\n#e15e1e"
    
    print("2. Comma+newline delimited hex colors:")
    print("Input:", repr(hex_comma))
    result = ColorInputAdapter.parse_hex_input(hex_comma)
    print("Output:", result)
    print()
    
    # Test 3: Semicolon delimited hex colors (semicolon+newline format)
    hex_semicolon = "#288ceb;\n#a778ae;\n#e15e1e"
    
    print("3. Semicolon+newline delimited hex colors:")
    print("Input:", repr(hex_semicolon))
    result = ColorInputAdapter.parse_hex_input(hex_semicolon)
    print("Output:", result)
    print()
    
    # Test 4: Hex colors without # prefix (comma+newline format)
    hex_no_prefix = "288ceb,\na778ae,\ne15e1e"
    
    print("4. Hex colors without # prefix:")
    print("Input:", repr(hex_no_prefix))
    result = ColorInputAdapter.parse_hex_input(hex_no_prefix)
    print("Output:", result)
    print()
    
    # Test 5: Mixed format (some with #, some without)
    hex_mixed = "#288ceb\na778ae\n#e15e1e"
    
    print("5. Mixed format (some with #, some without):")
    print("Input:", repr(hex_mixed))
    result = ColorInputAdapter.parse_hex_input(hex_mixed)
    print("Output:", result)
    print()


def test_rgb_input_formats():
    """Test various RGB input formats"""
    
    print("=== RGB INPUT FORMAT TESTING ===\n")
    
    # RGB 0-1 format tests
    print("--- RGB (0-1) Format Tests ---\n")
    
    # Test 1: Bare-bones format (newline delimiter only)
    rgb01_barebone = """0.157, 0.549, 0.922
0.655, 0.471, 0.682
0.882, 0.369, 0.118"""
    
    print("1. Bare-bones RGB(0-1) - newline delimited:")
    print("Input:", repr(rgb01_barebone))
    result = ColorInputAdapter.parse_rgb_input(rgb01_barebone, is_rgb256=False)
    print("Output:", result)
    print()
    
    # Test 2: Parentheses format
    rgb01_parens = """(0.157, 0.549, 0.922)
(0.655, 0.471, 0.682)
(0.882, 0.369, 0.118)"""
    
    print("2. Parentheses RGB(0-1):")
    print("Input:", repr(rgb01_parens))
    result = ColorInputAdapter.parse_rgb_input(rgb01_parens, is_rgb256=False)
    print("Output:", result)
    print()
    
    # Test 3: Brackets format
    rgb01_brackets = """[0.157, 0.549, 0.922]
[0.655, 0.471, 0.682]
[0.882, 0.369, 0.118]"""
    
    print("3. Brackets RGB(0-1):")
    print("Input:", repr(rgb01_brackets))
    result = ColorInputAdapter.parse_rgb_input(rgb01_brackets, is_rgb256=False)
    print("Output:", result)
    print()
    
    # Test 4: Braces format
    rgb01_braces = """{0.157, 0.549, 0.922}
{0.655, 0.471, 0.682}
{0.882, 0.369, 0.118}"""
    
    print("4. Braces RGB(0-1):")
    print("Input:", repr(rgb01_braces))
    result = ColorInputAdapter.parse_rgb_input(rgb01_braces, is_rgb256=False)
    print("Output:", result)
    print()
    
    # Test 5: rgb() function format
    rgb01_func = """rgb(0.157, 0.549, 0.922)
rgb(0.655, 0.471, 0.682)
rgb(0.882, 0.369, 0.118)"""
    
    print("5. rgb() function RGB(0-1):")
    print("Input:", repr(rgb01_func))
    result = ColorInputAdapter.parse_rgb_input(rgb01_func, is_rgb256=False)
    print("Output:", result)
    print()
    
    # Test 6: rgb{} format
    rgb01_func_braces = """rgb{0.157, 0.549, 0.922}
rgb{0.655, 0.471, 0.682}
rgb{0.882, 0.369, 0.118}"""
    
    print("6. rgb{} function RGB(0-1):")
    print("Input:", repr(rgb01_func_braces))
    result = ColorInputAdapter.parse_rgb_input(rgb01_func_braces, is_rgb256=False)
    print("Output:", result)
    print()
    
    # Test 7: rgb[] format
    rgb01_func_brackets = """rgb[0.157, 0.549, 0.922]
rgb[0.655, 0.471, 0.682]
rgb[0.882, 0.369, 0.118]"""
    
    print("7. rgb[] function RGB(0-1):")
    print("Input:", repr(rgb01_func_brackets))
    result = ColorInputAdapter.parse_rgb_input(rgb01_func_brackets, is_rgb256=False)
    print("Output:", result)
    print()
    
    # Test 8: Case insensitive RGB prefix
    rgb01_uppercase = """RGB(0.157, 0.549, 0.922)
Rgb(0.655, 0.471, 0.682)
rGB(0.882, 0.369, 0.118)"""
    
    print("8. Case insensitive RGB prefix:")
    print("Input:", repr(rgb01_uppercase))
    result = ColorInputAdapter.parse_rgb_input(rgb01_uppercase, is_rgb256=False)
    print("Output:", result)
    print()
    
    # RGB 256 format tests
    print("--- RGB (256) Format Tests ---\n")
    
    # Test 9: Bare-bones RGB256
    rgb256_barebone = """40, 140, 235
167, 120, 174
225, 94, 30"""
    
    print("9. Bare-bones RGB(256):")
    print("Input:", repr(rgb256_barebone))
    result = ColorInputAdapter.parse_rgb_input(rgb256_barebone, is_rgb256=True)
    print("Output:", result)
    print()
    
    # Test 10: RGB256 with semicolon+newline delimiters
    rgb256_semicolon = "rgb(40, 140, 235);\nrgb(167, 120, 174);\nrgb(225, 94, 30)"
    
    print("10. RGB(256) with semicolon+newline delimiters:")
    print("Input:", repr(rgb256_semicolon))
    result = ColorInputAdapter.parse_rgb_input(rgb256_semicolon, is_rgb256=True)
    print("Output:", result)
    print()


def test_copy_format_compatibility():
    """Test compatibility with current copy format outputs"""
    
    print("=== COPY FORMAT COMPATIBILITY TESTING ===\n")
    
    # Test current copy formats from the requirements
    
    # Current Hex copy format
    copied_hex = """#288ceb
#a778ae
#e15e1e"""
    
    print("Current Hex copy format:")
    print("Input:", repr(copied_hex))
    result = ColorInputAdapter.parse_hex_input(copied_hex)
    print("Parsed:", result)
    print()
    
    # Current RGB 256 copy format (not supported by old parser)
    copied_rgb256 = """rgb(40, 140, 235)
rgb(167, 120, 174)
rgb(225, 94, 30)"""
    
    print("Current RGB 256 copy format:")
    print("Input:", repr(copied_rgb256))
    result = ColorInputAdapter.parse_rgb_input(copied_rgb256, is_rgb256=True)
    print("Parsed:", result)
    print()
    
    # Current RGB 0-1 copy format (not supported by old parser)
    copied_rgb01 = """rgb(0.157, 0.549, 0.922)
rgb(0.655, 0.471, 0.682)
rgb(0.882, 0.369, 0.118)"""
    
    print("Current RGB 0-1 copy format:")
    print("Input:", repr(copied_rgb01))
    result = ColorInputAdapter.parse_rgb_input(copied_rgb01, is_rgb256=False)
    print("Parsed:", result)
    print()


if __name__ == "__main__":
    print("Color Input Adapter - Comprehensive Format Testing")
    print("=" * 60)
    print()
    
    test_hex_input_formats()
    test_rgb_input_formats()
    test_copy_format_compatibility()
    
    print("Testing completed!")