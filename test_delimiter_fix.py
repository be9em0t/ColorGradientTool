# Test for the fixed delimiter parsing
from color import ColorInputAdapter

def test_problematic_input():
    """Test the specific input format that was causing the error"""
    
    print("=== TESTING FIXED DELIMITER PARSING ===\n")
    
    # Test case that was causing the error: "could not convert string to float 'rgb(0.157'"
    # This happens when comma inside color description gets confused with color delimiter
    
    # Test 1: RGB function format with multiple colors
    problematic_input = """rgb(0.157, 0.549, 0.922)
rgb(0.655, 0.471, 0.682)
rgb(0.882, 0.369, 0.118)"""
    
    print("1. RGB function format (problematic case):")
    print("Input:", repr(problematic_input))
    try:
        result = ColorInputAdapter.parse_rgb_input(problematic_input, is_rgb256=False)
        print("✓ Success! Output:", result)
    except Exception as e:
        print("✗ Error:", e)
    print()
    
    # Test 2: Colors separated by comma+newline
    comma_newline_input = """rgb(0.157, 0.549, 0.922),
rgb(0.655, 0.471, 0.682),
rgb(0.882, 0.369, 0.118)"""
    
    print("2. Colors separated by comma+newline:")
    print("Input:", repr(comma_newline_input))
    try:
        result = ColorInputAdapter.parse_rgb_input(comma_newline_input, is_rgb256=False)
        print("✓ Success! Output:", result)
    except Exception as e:
        print("✗ Error:", e)
    print()
    
    # Test 3: Colors separated by semicolon+newline
    semicolon_newline_input = """rgb(0.157, 0.549, 0.922);
rgb(0.655, 0.471, 0.682);
rgb(0.882, 0.369, 0.118)"""
    
    print("3. Colors separated by semicolon+newline:")
    print("Input:", repr(semicolon_newline_input))
    try:
        result = ColorInputAdapter.parse_rgb_input(semicolon_newline_input, is_rgb256=False)
        print("✓ Success! Output:", result)
    except Exception as e:
        print("✗ Error:", e)
    print()
    
    # Test 4: Parentheses format
    parens_input = """(0.157, 0.549, 0.922)
(0.655, 0.471, 0.682)
(0.882, 0.369, 0.118)"""
    
    print("4. Parentheses format:")
    print("Input:", repr(parens_input))
    try:
        result = ColorInputAdapter.parse_rgb_input(parens_input, is_rgb256=False)
        print("✓ Success! Output:", result)
    except Exception as e:
        print("✗ Error:", e)
    print()
    
    # Test 5: Bare-bones format (should still work)
    barebone_input = """0.157, 0.549, 0.922
0.655, 0.471, 0.682
0.882, 0.369, 0.118"""
    
    print("5. Bare-bones format:")
    print("Input:", repr(barebone_input))
    try:
        result = ColorInputAdapter.parse_rgb_input(barebone_input, is_rgb256=False)
        print("✓ Success! Output:", result)
    except Exception as e:
        print("✗ Error:", e)
    print()
    
    # Test 6: RGB256 format
    rgb256_input = """rgb(40, 140, 235)
rgb(167, 120, 174)
rgb(225, 94, 30)"""
    
    print("6. RGB256 format:")
    print("Input:", repr(rgb256_input))
    try:
        result = ColorInputAdapter.parse_rgb_input(rgb256_input, is_rgb256=True)
        print("✓ Success! Output:", result)
    except Exception as e:
        print("✗ Error:", e)
    print()

    # Test 7: Hex colors with fixed delimiters
    hex_input = """#288ceb
#a778ae
#e15e1e"""
    
    print("7. Hex colors:")
    print("Input:", repr(hex_input))
    try:
        result = ColorInputAdapter.parse_hex_input(hex_input)
        print("✓ Success! Output:", result)
    except Exception as e:
        print("✗ Error:", e)
    print()

if __name__ == "__main__":
    test_problematic_input()
    print("Fixed delimiter parsing test completed!")