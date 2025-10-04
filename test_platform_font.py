# Test the platform font functions
import platform

def get_platform_font_family():
    """
    Return the appropriate font family for the current platform.
    
    Returns:
        str: Font family string for CSS/Qt stylesheet usage
    """
    system = platform.system()
    if system == "Darwin":  # macOS
        return '"Helvetica Neue", Arial, sans-serif'
    elif system == "Windows":
        return '"Segoe UI", Arial, sans-serif'
    else:  # Linux and others
        return '"Ubuntu", "Liberation Sans", Arial, sans-serif'

def get_platform_monospace_font():
    """
    Return the appropriate monospace font family for the current platform.
    
    Returns:
        str: Monospace font family string for CSS/Qt stylesheet usage
    """
    system = platform.system()
    if system == "Darwin":  # macOS
        return 'Monaco, "Courier New", monospace'
    elif system == "Windows":
        return '"Consolas", "Courier New", monospace'
    else:  # Linux and others
        return '"Ubuntu Mono", "Liberation Mono", "Courier New", monospace'

if __name__ == "__main__":
    print(f"Current platform: {platform.system()}")
    print(f"Selected font family: {get_platform_font_family()}")
    print(f"Selected monospace font: {get_platform_monospace_font()}")