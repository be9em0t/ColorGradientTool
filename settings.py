# settings.py
# Configuration management for ColorGradientTool
# Handles INI file loading/saving and application state persistence

import configparser
from pathlib import Path


class Settings:
    """Manages application settings and INI file persistence"""
    
    def __init__(self, config_path):
        self.config_path = Path(config_path)
        
        # Default settings - these correspond to INI keys
        self.model = 'oklch'
        self.format = 'Hex'
        self.color_a = '#e31b23'
        self.color_b = '#00b0e6'
        self.converter_hex = ''
        
        # Model mappings for friendly labels
        self.model_label_to_key = {
            'OKLCH (OKLab LCh)': 'oklch',
            'LCh (CIE LCh)': 'lch',
            'OKLab': 'oklab',
            'CIE Lab': 'lab',
            'HWB (Hue‑Whiteness‑Blackness)': 'hwb',
            'HSL (Hue‑Saturation‑Lightness)': 'hsl',
            'sRGB': 'srgb',
        }
    
    def load(self):
        """Load settings from INI file"""
        cfg = configparser.ConfigParser()
        if not self.config_path.exists():
            return
        
        try:
            cfg.read(self.config_path)
            if cfg.has_section('ui'):
                self.model = cfg.get('ui', 'model', fallback=self.model)
                self.format = cfg.get('ui', 'format', fallback=self.format)
                self.color_a = cfg.get('ui', 'color_a', fallback=self.color_a)
                self.color_b = cfg.get('ui', 'color_b', fallback=self.color_b)
                converter_hex = cfg.get('ui', 'converter_hex', fallback=self.converter_hex)
                
                # Decode escaped newlines stored in the INI
                if converter_hex:
                    self.converter_hex = converter_hex.replace('\\n', '\n')
        except Exception:
            # Ignore config errors and use defaults
            pass
    
    def save(self):
        """Save current settings to INI file"""
        cfg = configparser.ConfigParser()
        cfg['ui'] = {
            'model': self.model,
            'format': self.format,
            'color_a': self.color_a,
            'color_b': self.color_b,
            # Encode newlines as '\\n' so configparser writes a single-line value reliably
            'converter_hex': self.converter_hex.replace('\n', '\\n'),
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            cfg.write(f)
    
    def get_model_mappings(self):
        """Return friendly label -> internal key mappings"""
        return self.model_label_to_key
    
    def get_model_key(self, friendly_label):
        """Get internal model key from friendly label"""
        return self.model_label_to_key.get(friendly_label, friendly_label)
    
    def get_model_label(self, internal_key):
        """Get friendly label from internal model key"""
        for label, key in self.model_label_to_key.items():
            if key == internal_key.lower():
                return label
        return internal_key