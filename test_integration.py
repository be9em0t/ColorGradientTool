# Test the integrated ColorInputAdapter in the main application
# This simulates the conversion handlers being called with problematic inputs

from color import ColorInputAdapter, hex_to_rgb01, rgb01_to_hex, format_rgb01_from_tuple, format_rgb256_from_tuple

def test_conversion_handlers():
    """Test the conversion logic that's now integrated into main.py"""
    
    print("=== TESTING INTEGRATED COLOR CONVERSION HANDLERS ===\n")
    
    # Test 1: RGB(0-1) format (that was failing before)
    print("1. Testing RGB(0-1) conversion handler:")
    input_text = """rgb(0.157, 0.549, 0.922)
rgb(0.459, 0.722, 0.686)
rgb(0.616, 0.855, 0.157)"""
    
    print("Input:", repr(input_text))
    try:
        # Simulate the on_convert_from_rgb01 handler logic
        rgb01_tuples = ColorInputAdapter.parse_rgb_input(input_text, is_rgb256=False)
        if not rgb01_tuples:
            raise ValueError('No valid RGB(0-1) colors found')
        
        # Convert to all formats
        hexs = []
        r256 = []
        r01 = []
        for rgb01_tuple in rgb01_tuples:
            r01.append(format_rgb01_from_tuple(rgb01_tuple))
            r256_tuple = tuple(int(round(v*255)) for v in rgb01_tuple)
            r256.append(format_rgb256_from_tuple(r256_tuple))
            hexs.append(rgb01_to_hex(rgb01_tuple))
        
        print("✓ Success!")
        print("Hex:", hexs)
        print("RGB256:", r256)
        print("RGB01:", r01)
    except Exception as e:
        print("✗ Error:", e)
    print()
    
    # Test 2: RGB(256) format
    print("2. Testing RGB(256) conversion handler:")
    input_text = """rgb(40, 140, 235)
rgb(117, 184, 175)
rgb(157, 218, 40)"""
    
    print("Input:", repr(input_text))
    try:
        # Simulate the on_convert_from_rgb256 handler logic
        rgb256_tuples = ColorInputAdapter.parse_rgb_input(input_text, is_rgb256=True)
        if not rgb256_tuples:
            raise ValueError('No valid RGB(256) colors found')
        
        # Convert to all formats
        hexs = []
        r256 = []
        r01 = []
        for rgb256_tuple in rgb256_tuples:
            r256.append(format_rgb256_from_tuple(rgb256_tuple))
            r01_tuple = tuple(v/255.0 for v in rgb256_tuple)
            r01.append(format_rgb01_from_tuple(r01_tuple))
            hexs.append(rgb01_to_hex(r01_tuple))
        
        print("✓ Success!")
        print("Hex:", hexs)
        print("RGB256:", r256)
        print("RGB01:", r01)
    except Exception as e:
        print("✗ Error:", e)
    print()
    
    # Test 3: Hex format with comma+newline
    print("3. Testing Hex conversion handler:")
    input_text = """#288ceb,
#75b8af,
#9dda28"""
    
    print("Input:", repr(input_text))
    try:
        # Simulate the on_convert_from_hex handler logic
        hex_colors = ColorInputAdapter.parse_hex_input(input_text)
        if not hex_colors:
            raise ValueError('No valid hex colors found')
        
        # Convert to all formats
        hexs = hex_colors
        r256 = []
        r01 = []
        for hex_color in hex_colors:
            r01_tuple = hex_to_rgb01(hex_color)
            r01.append(format_rgb01_from_tuple(r01_tuple))
            r256_tuple = tuple(int(round(x*255)) for x in r01_tuple)
            r256.append(format_rgb256_from_tuple(r256_tuple))
        
        print("✓ Success!")
        print("Hex:", hexs)
        print("RGB256:", r256)
        print("RGB01:", r01)
    except Exception as e:
        print("✗ Error:", e)
    print()

if __name__ == "__main__":
    test_conversion_handlers()
    print("Integration testing completed!")