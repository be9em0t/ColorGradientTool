# main.py
# PyQt6 GUI and application logic for ColorGradientTool
# Requires: PySide6 and coloraide

# Description: 
# This is a Color Gradient Tool that allows generating gradients 
# with different amount of intermediate steps from certain "seed" tiles: 
# A (left, first), B (right, last) and C (center, only when 3-color mode is active). 
# The gradients can be generated using different color spaces (sRGB, LAB etc) 
# and can be represented using different color modes (Hex, RGB etc.). 
# Finally, we have some limited color mode conversion functionality 
# useful when a numebr of color values need to be converted between Hex, RGB(0-1) or RGB(256).

# Rules:
# 1. All values are explicit and can be changed only by stored INI settings, 
# direct user input and explicit color finction called directly as a result of user input.
# Never "massage" a value to fit some implicit logic.  
# 2. Edit the code strictly limited to the user prompt. 
# Never overachieve the prompt in an effort to cover edge cases or perceived minor improvements. 
# If such cases arise please ASK THE USER FOR EXLICIT PERMISSION.
# 3. Minimize code changes and optimize for simplicity. 
# It's better to be minimal and add code later, when it becomes explicitly necessary, 
# than to stuff boilerplate code for edge cases that cause hard to track errors.

import sys
import math
import os
import platform
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QComboBox, QColorDialog,
    QHBoxLayout, QVBoxLayout, QGridLayout, QSizePolicy, QStatusBar, QTextEdit
)
from PySide6.QtGui import QColor, QPainter, QPixmap, QIcon, QPainterPath
from PySide6.QtCore import Qt, QSize, Signal
from pathlib import Path

# Import our modules
from color import (
    interpolate, format_color_list, ColorParser, ColorInputAdapter,
    lerp, parse_hex_string, hex_to_rgb01, rgb01_to_hex,
    format_rgb01_from_tuple, format_rgb256_from_tuple
)
from settings import Settings


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


def get_config_path():
    """
    Get the appropriate configuration file path based on whether the app is packaged.
    
    For packaged macOS apps: ~/Library/Application Support/ColorGradientTool/ColorGradient.ini
    For development: ./ColorGradient.ini (relative to script)
    """
    # Check if we're running as a PyInstaller bundle
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # We're in a PyInstaller bundle - use Application Support directory
        if sys.platform == 'darwin':  # macOS
            app_support = Path.home() / 'Library' / 'Application Support' / 'ColorGradientTool'
            app_support.mkdir(parents=True, exist_ok=True)
            config_path = app_support / 'ColorGradient.ini'
            
            # Copy default settings from bundle if user config doesn't exist
            if not config_path.exists():
                try:
                    # Try to find the bundled ini file
                    bundle_ini = Path(sys._MEIPASS) / 'ColorGradient.ini'
                    if bundle_ini.exists():
                        import shutil
                        shutil.copy2(bundle_ini, config_path)
                except Exception:
                    pass  # If copying fails, Settings class will use defaults
            
            return config_path
        else:
            # For other platforms (Windows), use a similar approach
            app_data = Path.home() / 'AppData' / 'Roaming' / 'ColorGradientTool'
            app_data.mkdir(parents=True, exist_ok=True)
            return app_data / 'ColorGradient.ini'
    else:
        # Development mode - use the original behavior
        return Path(__file__).parent / 'ColorGradient.ini'

# UI spacing constants moved to INI settings
# Tile count boundaries (hardcoded for UI stability)
MIN_TILES_BETWEEN = 1  # Minimum intermediate tiles for all gradients
MAX_TILES_AB = 9      # Maximum intermediate tiles for AB gradient (total 11: A + 9 + B)
MAX_TILES_AC = 5      # Maximum intermediate tiles for AC gradient
MAX_TILES_CB = 5      # Maximum intermediate tiles for CB gradient (total max 13: A + 5 + C + 5 + B)

# UI sizing constants (hardcoded for consistent layout)
DEFAULT_TILE_HEIGHT = 80        # Default tile height in pixels
MINIMUM_TILE_WIDTH = 20  # Absolute minimum for extreme cases (usability vs predictability tradeoff)
GRADIENT_PREVIEW_HEIGHT = 80    # Height of gradient preview bar
MINIMUM_WINDOW_WIDTH = 600      # Minimum window width in pixels
MINIMUM_WINDOW_HEIGHT = 560     # Minimum window height in pixels

# UI color constants
LINK_COLOR = '#4CA7F8' #'#4588C4'          # Color for clickable link-style labels and highlights


class GradientPreview(QLabel):
    def __init__(self, parent=None, border_radius=4):
        super().__init__(parent)
        # Match the height of the color swatches
        self.setFixedHeight(GRADIENT_PREVIEW_HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._colors = ['#ff0000', '#0000ff']
        self.border_radius = border_radius
        # Apply rounded corners styling
        self.setStyleSheet(f'border-radius: {self.border_radius}px;')

    def set_colors(self, colors):
        self._colors = colors
        self.update_preview()

    def update_preview(self):
        w = max(200, self.width())
        # Use the widget's actual height (fixed to match swatches)
        h = max(1, self.height())
        pix = QPixmap(w, h)
        pix.fill(Qt.transparent)  # Start with transparent background
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create rounded rectangle path
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, self.border_radius, self.border_radius)
        painter.setClipPath(path)
        
        # Draw gradient within the clipped rounded rectangle
        img = pix.toImage()
        steps = len(self._colors)
        stops_rgb = [QColor(c).getRgb() for c in self._colors]
        for x in range(w):
            t = x / (w - 1) if w > 1 else 0
            pos = t * (steps - 1)
            i = int(math.floor(pos))
            j = min(steps - 1, i + 1)
            local_t = pos - i
            c1 = stops_rgb[i]
            c2 = stops_rgb[j]
            r = int(round(lerp(c1[0], c2[0], local_t)))
            g = int(round(lerp(c1[1], c2[1], local_t)))
            b = int(round(lerp(c1[2], c2[2], local_t)))
            for y in range(h):
                img.setPixelColor(x, y, QColor(r, g, b))
        painter.drawImage(0, 0, img)
        painter.end()
        self.setPixmap(pix)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_preview()


class MultilineEdit(QTextEdit):
    """QTextEdit that emits editingFinished on focus out, Ctrl+Enter, or Enter when single-line."""
    editingFinished = Signal()
    focusChanged = Signal(bool)  # Signal for focus changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Avoid accepting rich text from clipboard sources
        try:
            self.setAcceptRichText(False)
        except Exception:
            pass
        self._is_focused = False

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._is_focused = True
        try:
            self.focusChanged.emit(True)
        except Exception:
            pass

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self._is_focused = False
        try:
            self.focusChanged.emit(False)
            self.editingFinished.emit()
        except Exception:
            pass

    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()
        if key in (Qt.Key_Return, Qt.Key_Enter):
            # Ctrl/Cmd+Enter -> submit
            if mods & (Qt.ControlModifier | Qt.MetaModifier):
                try:
                    self.editingFinished.emit()
                except Exception:
                    pass
                return
            # If the content is single-line, Enter should submit instead of inserting newline
            if '\n' not in self.toPlainText():
                try:
                    self.editingFinished.emit()
                except Exception:
                    pass
                return
        super().keyPressEvent(event)

    def insertFromMimeData(self, source):
        # Ensure pasted content is treated as plain text (strip formatting)
        try:
            text = source.text()
            self.insertPlainText(text)
        except Exception:
            # Fallback to default behavior
            super().insertFromMimeData(source)

    def set_source_highlight(self, is_source=False):
        """Set visual indication that this box is the source for conversion"""
        # Define the base style
        base_style = f"""
            QTextEdit {{
                background-color: #3a4a56;
                border-radius: 5px;
                padding: 1px 1px 1px 6px;
                color: #eaeff2;
                font-family: {get_platform_monospace_font()};
                selection-background-color: #4a5a66;
            }}
            QTextEdit:focus {{
                border: 2px solid #eaeff2;
            }}
        """
        
        if is_source:
            # Source highlighting with blue border
            source_style = base_style.replace(
                'border-radius: 5px;',
                f'border: 2px solid {LINK_COLOR};\n                border-radius: 5px;'
            )
            self.setStyleSheet(source_style)
        else:
            # Normal style with subtle border
            normal_style = base_style.replace(
                'border-radius: 4px;',
                'border: 1px solid #555;\n                border-radius: 4px;'
            )
            self.setStyleSheet(normal_style)
    
    def set_error_style(self):
        """Set error styling for conversion failures"""
        # padding: 4px 8px;
        error_style = f"""
            QTextEdit {{
                background-color: #3a4a56;
                border: 2px solid #d9534f;
                border-radius: 5px;
                padding: 1px 1px 1px 6px;
                color: #eaeff2;
                font-family: {get_platform_monospace_font()};
                selection-background-color: #4a5a66;
            }}
            QTextEdit:focus {{
                border: 2px solid #d9534f;
            }}
        """
        self.setStyleSheet(error_style)
    
    def clear_error_style(self):
        """Clear error styling and return to normal"""
        self.set_source_highlight(False)


class ColorTile(QPushButton):
    def __init__(self, hexcolor, size=(140, 80), is_master=False, master_border_color='#808080', border_radius=4):
        super().__init__()
        self.hex = hexcolor
        self.is_master = is_master
        self.master_border_color = master_border_color
        self.border_radius = border_radius
        self.setFixedSize(QSize(*size))
        self._update_style()

    def set_color(self, hexcolor):
        self.hex = hexcolor
        self._update_style()
    
    def set_size(self, width, height):
        self.setFixedSize(QSize(width, height))
    
    def _update_style(self):
        if self.is_master:
            # Master tiles get an inner border
            self.setStyleSheet(f'background: {self.hex}; border: 2px solid {self.master_border_color}; border-radius: {self.border_radius}px;')
        else:
            # Regular preview tiles
            self.setStyleSheet(f'background: {self.hex}; border: 1px solid #222; border-radius: {self.border_radius}px;')




class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Color Gradient Tool")
        
        # Set window icon (relative to script folder)
        try:
            icon_path = Path(__file__).parent / 'resources' / 'ColorGradientTool_icon.png'
            if icon_path.exists():
                ico = QIcon(str(icon_path))
                self.setWindowIcon(ico)
        except Exception:
            pass
        
        self.setMinimumSize(MINIMUM_WINDOW_WIDTH, MINIMUM_WINDOW_HEIGHT)

        # Initialize settings with proper path for packaged apps
        config_path = get_config_path()
        self.settings = Settings(config_path)
        self.settings.load()

        # 3-color mode state
        self.three_mode = self.settings.three_mode

        title = QLabel("Color Gradient Tool")
        title.setStyleSheet("font-size: 28px; font-weight: 600; color: #ffffff;")
        title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Tiles row - master tiles with border (use settings colors directly)
        self.tile_a = ColorTile(self.settings.color_a, is_master=True, master_border_color=self.settings.master_tile_border_color, border_radius=self.settings.tile_border_radius)
        self.tile_b = ColorTile(self.settings.color_b, is_master=True, master_border_color=self.settings.master_tile_border_color, border_radius=self.settings.tile_border_radius)
        self.tile_c = ColorTile(self.settings.color_c, is_master=True, master_border_color=self.settings.master_tile_border_color, border_radius=self.settings.tile_border_radius)

        # dynamic intermediate preview tiles - use global constants
        self.min_tiles_between = MIN_TILES_BETWEEN
        self.max_tiles_ab = MAX_TILES_AB
        self.max_tiles_ac = MAX_TILES_AC  
        self.max_tiles_cb = MAX_TILES_CB
        
        # 2-color mode: AB gradient tiles
        self.preview_tiles_ab = []
        for _ in range(self.settings.ab_count):
            lbl = QLabel()
            lbl.setFixedSize(80, DEFAULT_TILE_HEIGHT)  # Initial size, will be updated by update_tile_sizes()
            lbl.setStyleSheet(f'background: #777; border: 1px solid #222; border-radius: {self.settings.tile_border_radius}px;')
            lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.preview_tiles_ab.append(lbl)
        
        # 3-color mode: AC gradient tiles (left side)
        self.preview_tiles_ac = []
        for _ in range(self.settings.ac_count):
            lbl = QLabel()
            lbl.setFixedSize(80, DEFAULT_TILE_HEIGHT)
            lbl.setStyleSheet(f'background: #777; border: 1px solid #222; border-radius: {self.settings.tile_border_radius}px;')
            lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.preview_tiles_ac.append(lbl)
        
        # 3-color mode: CB gradient tiles (right side)
        self.preview_tiles_cb = []
        for _ in range(self.settings.cb_count):
            lbl = QLabel()
            lbl.setFixedSize(80, DEFAULT_TILE_HEIGHT)
            lbl.setStyleSheet(f'background: #777; border: 1px solid #222; border-radius: {self.settings.tile_border_radius}px;')
            lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.preview_tiles_cb.append(lbl)

        # Add/remove link-like labels (styled) centered between the Tile A and Tile B labels
        # 2-color mode controls
        self.add_link = QLabel('[+]')
        self.add_link.setStyleSheet(f'color: {LINK_COLOR}; font-size: 14px;')
        self.add_link.setCursor(Qt.PointingHandCursor)
        self.add_link.setToolTip('Add a tile (max 11 total)')

        self.sub_link = QLabel('[-]')
        self.sub_link.setStyleSheet(f'color: {LINK_COLOR}; font-size: 14px;')
        self.sub_link.setCursor(Qt.PointingHandCursor)
        self.sub_link.setToolTip('Remove a tile (min 3 total)')

        # 3-color mode controls (left side - AC gradient)
        self.add_link_left = QLabel('[+]')
        self.add_link_left.setStyleSheet(f'color: {LINK_COLOR}; font-size: 14px;')
        self.add_link_left.setCursor(Qt.PointingHandCursor)
        self.add_link_left.setToolTip('Add a tile to left gradient (A-C)')

        self.sub_link_left = QLabel('[-]')
        self.sub_link_left.setStyleSheet(f'color: {LINK_COLOR}; font-size: 14px;')
        self.sub_link_left.setCursor(Qt.PointingHandCursor)
        self.sub_link_left.setToolTip('Remove a tile from left gradient (A-C)')

        # 3-color mode controls (right side - CB gradient)
        self.add_link_right = QLabel('[+]')
        self.add_link_right.setStyleSheet(f'color: {LINK_COLOR}; font-size: 14px;')
        self.add_link_right.setCursor(Qt.PointingHandCursor)
        self.add_link_right.setToolTip('Add a tile to right gradient (C-B)')

        self.sub_link_right = QLabel('[-]')
        self.sub_link_right.setStyleSheet(f'color: {LINK_COLOR}; font-size: 14px;')
        self.sub_link_right.setCursor(Qt.PointingHandCursor)
        self.sub_link_right.setToolTip('Remove a tile from right gradient (C-B)')

        self.middle_label = QLabel('[enable 3-tile]')
        self.middle_label.setStyleSheet(f'color: {LINK_COLOR}; font-size: 14px;')
        self.middle_label.setAlignment(Qt.AlignCenter)
        self.middle_label.setCursor(Qt.PointingHandCursor)
        self.middle_label.setToolTip('Click to enable/disable 3-color mode')

        # Color model selector (friendly labels shown; use mapping to internal keys)
        self.model_combo = QComboBox()
        model_mappings = self.settings.get_model_mappings()
        for label in model_mappings.keys():
            self.model_combo.addItem(label)
        
        # Set current model from settings
        current_label = self.settings.get_model_label(self.settings.model)
        self.model_combo.setCurrentText(current_label)
        self.model_combo.setFixedWidth(260)
        
        # Apply same styling as the format selector so controls look consistent
        self.model_combo.setStyleSheet("""
            QComboBox {
                background-color: #3a4a56;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
                color: #eaeff2;
            }
        """)

        # Format selector for copy functionality
        self.format_combo = QComboBox()
        formats = ['Hex', 'RGB 256', 'RGB 0-1']
        for f in formats:
            self.format_combo.addItem(f)
        self.format_combo.setCurrentText(self.settings.format)
        self.format_combo.setFixedWidth(120)
        self.format_combo.setStyleSheet("""
            QComboBox {
                background-color: #3a4a56;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
                color: #eaeff2;
            }
        """)

        # Copy button
        self.copy_button = QPushButton('Copy colors')
        self.copy_button.setFixedWidth(120)
        self.copy_button.setStyleSheet("""
            QPushButton {
                background-color: #3a4a56;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
                color: #eaeff2;
            }
            QPushButton:hover {
                background-color: #4a5a66;
            }
            QPushButton:pressed {
                background-color: #2a3a46;
            }
        """)

        # Gradient preview
        self.gradient_preview = GradientPreview(border_radius=self.settings.tile_border_radius)

        # Layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(18)
        # Reduce bottom margin slightly (was 20) to tighten space below status bar
        main_layout.setContentsMargins(20, 20, 20, 10)
        main_layout.addWidget(title)

        top_grid = QGridLayout()
        top_grid.setHorizontalSpacing(20)
        # Reduce vertical gap between label row and tiles
        top_grid.setVerticalSpacing(6)
        # Labels for the edge tiles
        label_a = QLabel("Tile A")
        label_a.setStyleSheet('color: #eaeff2;')
        top_grid.addWidget(label_a, 0, 0, alignment=Qt.AlignLeft)
        label_b = QLabel("Tile B")
        label_b.setStyleSheet('color: #eaeff2;')
        top_grid.addWidget(label_b, 0, 2, alignment=Qt.AlignRight)

        tiles_layout = QHBoxLayout()
        tiles_layout.setSpacing(self.settings.swatch_gap)
        # We'll create a container layout that we can rebuild when the number of tiles changes
        self.tiles_container = QHBoxLayout()
        self.tiles_container.setSpacing(self.settings.swatch_gap)
        # initial population will be done by rebuild_tiles() in initialization

        # Insert add/remove links centered on the label row: create a small widget layout for them
        self.links_widget = QWidget()
        self.links_layout = QHBoxLayout()
        self.links_layout.setContentsMargins(0, 0, 0, 0)
        self.links_layout.setSpacing(8)
        # Initial population will be done by update_mode_ui()
        self.links_widget.setLayout(self.links_layout)

        # Put tiles in the main tiles_layout. Place the add/remove links on the label row
        tiles_layout.addLayout(self.tiles_container)
        # Add the links widget to the label row (row 0, column 1) so it appears centered between the labels
        top_grid.addWidget(self.links_widget, 0, 1, alignment=Qt.AlignCenter)

        top_grid.addLayout(tiles_layout, 1, 0, 1, 3)

        # model selector and format controls under tiles with labels
        controls_layout = QGridLayout()

        # Labels above the selectors
        label_space = QLabel("Color space")
        label_space.setStyleSheet('color: #eaeff2;')
        # Help icon next to Color space (use simple text '[?]' for cross-platform reliability)
        help_icon = QLabel('[?]')
        help_icon.setStyleSheet(f'color: {LINK_COLOR}; font-size: 13px; padding-left: 6px;')
        help_icon.setToolTip(
            """
<b>Color space descriptions</b><br><br>
OKLCH — OKLCH (OKLab LCh) — Perceptual Lightness‑Chroma‑Hue (based on the OKLab color space; good for perceptual interpolation)<br><br>
OKLab — OKLab — Perceptual L‑a‑b color space (lightness and two opponent axes; designed for more uniform perceived differences)<br><br>
LCh — LCh (CIE LCh / LCh(ab)) — Lightness‑Chroma‑Hue (cylindrical form of CIE Lab*; useful for intuitive hue/chroma edits)<br><br>
Lab — CIE Lab* (Lab) — Lightness and two color opponent channels (device‑independent, perceptually oriented)<br><br>
HWB — HWB — Hue‑Whiteness‑Blackness (simple paint‑like model: mix hue with white and black; intuitive for designers)<br><br>
HSL — HSL — Hue‑Saturation‑Lightness (common cylindrical RGB model for adjusting hue and perceived lightness)
"""
        )
        # Also make clicking it open a QMessageBox with the same content for accessibility
        def show_help():
            from PySide6.QtWidgets import QMessageBox
            msg = QMessageBox(self)
            msg.setWindowTitle('Color space help')
            msg.setTextFormat(Qt.RichText)
            msg.setText(help_icon.toolTip())
            msg.exec()
        try:
            help_icon.mousePressEvent = lambda e: show_help()
        except Exception:
            pass
        label_format = QLabel("Color format")
        label_format.setStyleSheet('color: #eaeff2;')

        # Place the label and help icon together
        hl = QHBoxLayout()
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)
        hl.addWidget(label_space)
        hl.addWidget(help_icon)
        helper_widget = QWidget()
        helper_widget.setLayout(hl)
        controls_layout.addWidget(helper_widget, 0, 0, alignment=Qt.AlignLeft)
        controls_layout.addWidget(label_format, 0, 1, alignment=Qt.AlignLeft)

        # Controls row
        controls_layout.addWidget(self.model_combo, 1, 0)
        controls_layout.addWidget(self.format_combo, 1, 1)
        controls_layout.addWidget(self.copy_button, 1, 2)
        # spacer column
        controls_layout.setColumnStretch(3, 1)

        top_grid.addLayout(controls_layout, 2, 0, 1, 3)

        main_layout.addLayout(top_grid)

        # gradient preview
        gl = QVBoxLayout()
        # tighten spacing so the label sits closer to the preview
        gl.setSpacing(6)
        gl.addWidget(QLabel("Gradient preview"))
        gl.addWidget(self.gradient_preview)
        main_layout.addLayout(gl)

        # --- Color format converter fields (independent utility) ---
        conv_layout = QGridLayout()
        # tighten vertical spacing so converter labels sit closer to boxes
        conv_layout.setVerticalSpacing(6)
        # Converter area: three multiline boxes for Hex, RGB 256, RGB 0-1
        lbl_hex = QLabel('Hex')
        lbl_hex.setStyleSheet('color: #eaeff2;')
        lbl_rgb256 = QLabel('RGB 256')
        lbl_rgb256.setStyleSheet('color: #eaeff2;')
        lbl_rgb01 = QLabel('RGB 0-1 ')
        lbl_rgb01.setStyleSheet('color: #eaeff2;')

        self.conv_hex = MultilineEdit()
        self.conv_rgb256 = MultilineEdit()
        self.conv_rgb01 = MultilineEdit()
        
        # Apply initial styling using the new methods
        self.conv_hex.set_source_highlight(False)
        self.conv_rgb256.set_source_highlight(False)
        self.conv_rgb01.set_source_highlight(False)
        
        # Limit box height to ~4 lines so scrollbar appears for longer lists
        fm = self.conv_hex.fontMetrics()
        line_h = fm.lineSpacing()
        max_h = line_h * 4 + 10
        self.conv_hex.setMaximumHeight(max_h)
        self.conv_rgb256.setMaximumHeight(max_h)
        self.conv_rgb01.setMaximumHeight(max_h)

        # Layout labels above the respective boxes
        conv_layout.addWidget(lbl_hex, 0, 0)
        conv_layout.addWidget(lbl_rgb256, 0, 1)
        conv_layout.addWidget(lbl_rgb01, 0, 2)

        conv_layout.addWidget(self.conv_hex, 1, 0)
        conv_layout.addWidget(self.conv_rgb256, 1, 1)  
        conv_layout.addWidget(self.conv_rgb01, 1, 2)

        # Initialize converter hex from settings or default to tile A
        if self.settings.converter_hex:
            self.conv_hex.setPlainText(self.settings.converter_hex)
        else:
            self.conv_hex.setPlainText(self.tile_a.hex)

        # Conversion handlers
        def on_convert_from_hex():
            src = self.conv_hex
            src.clear_error_style()
            input_text = self.conv_hex.toPlainText()
            try:
                # Use the new ColorInputAdapter for flexible parsing
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
                
            except Exception as e:
                src.set_error_style()
                self.status.showMessage(f'Conversion failed: invalid Hex input. {e}')
                return
            # success - clear any error styles and restore normal styling
            self.conv_hex.clear_error_style()
            self.conv_rgb256.clear_error_style()
            self.conv_rgb01.clear_error_style()
            self.conv_hex.setPlainText('\n'.join(hexs))
            self.conv_rgb256.setPlainText('\n'.join(r256))
            self.conv_rgb01.setPlainText('\n'.join(r01))
            self.status.showMessage(f'Converted {len(hexs)} lines from Hex.')

        def on_convert_from_rgb256():
            src = self.conv_rgb256 
            src.clear_error_style()
            input_text = self.conv_rgb256.toPlainText()
            try:
                # Use the new ColorInputAdapter for flexible parsing
                rgb256_tuples = ColorInputAdapter.parse_rgb_input(input_text, is_rgb256=True)
                if not rgb256_tuples:
                    raise ValueError('No valid RGB 256 colors found')
                
                # Convert to all formats
                hexs = []
                r256 = []
                r01 = []
                for rgb256_tuple in rgb256_tuples:
                    r256.append(format_rgb256_from_tuple(rgb256_tuple))
                    r01_tuple = tuple(v/255.0 for v in rgb256_tuple)
                    r01.append(format_rgb01_from_tuple(r01_tuple))
                    hexs.append(rgb01_to_hex(r01_tuple))
                
            except Exception as e:
                src.set_error_style()
                self.status.showMessage(f'Conversion failed: invalid RGB 256 input. {e}')
                return
            # success - clear any error styles and restore normal styling
            self.conv_hex.clear_error_style()
            self.conv_rgb256.clear_error_style()
            self.conv_rgb01.clear_error_style()
            self.conv_hex.setPlainText('\n'.join(hexs))
            self.conv_rgb256.setPlainText('\n'.join(r256))
            self.conv_rgb01.setPlainText('\n'.join(r01))
            self.status.showMessage(f'Converted {len(hexs)} lines from RGB 256.')

        def on_convert_from_rgb01():
            src = self.conv_rgb01
            src.clear_error_style()
            input_text = self.conv_rgb01.toPlainText()
            try:
                # Use the new ColorInputAdapter for flexible parsing
                rgb01_tuples = ColorInputAdapter.parse_rgb_input(input_text, is_rgb256=False)
                if not rgb01_tuples:
                    raise ValueError('No valid RGB 0-1 colors found')
                
                # Convert to all formats
                hexs = []
                r256 = []
                r01 = []
                for rgb01_tuple in rgb01_tuples:
                    r01.append(format_rgb01_from_tuple(rgb01_tuple))
                    r256_tuple = tuple(int(round(v*255)) for v in rgb01_tuple)
                    r256.append(format_rgb256_from_tuple(r256_tuple))
                    hexs.append(rgb01_to_hex(rgb01_tuple))
                
            except Exception as e:
                src.set_error_style()
                self.status.showMessage(f'Conversion failed: invalid RGB 0-1 input. {e}')
                return
            
            # Ensure RGB(0-1) output has leading zeros for floats
            r01_with_leading = []
            for line in r01:
                parts = [p.strip() for p in line.split(',')]
                formatted = []
                for p in parts:
                    # normalize float format to have leading zero
                    try:
                        fv = float(p)
                        s = f"{fv:.5f}".rstrip('0').rstrip('.')
                        if s.startswith('.'):
                            s = '0' + s
                        formatted.append(s)
                    except Exception:
                        formatted.append(p)
                r01_with_leading.append(', '.join(formatted))

            # success - clear any error styles and restore normal styling
            self.conv_hex.clear_error_style()
            self.conv_rgb256.clear_error_style()
            self.conv_rgb01.clear_error_style()
            self.conv_hex.setPlainText('\n'.join(hexs))
            self.conv_rgb256.setPlainText('\n'.join(r256))
            self.conv_rgb01.setPlainText('\n'.join(r01_with_leading))
            self.status.showMessage(f'Converted {len(hexs)} lines from RGB 0-1.')

        # Single Convert button (will act on focused box or first non-empty)
        btn_convert = QPushButton('Convert colors')
        btn_convert.setFixedWidth(120)
        # Match styling of the existing Copy Colors button
        btn_convert.setStyleSheet("""
            QPushButton {
                background-color: #3a4a56;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
                margin: 8px 0px 0px 0px;
                color: #eaeff2;
            }
            QPushButton:hover {
                background-color: #4a5a66;
            }
            QPushButton:pressed {
                background-color: #2a3a46;
            }
        """)

        def update_source_highlighting(source_box):
            """Update visual highlighting to show which box is the conversion source"""
            # Clear all highlights first
            self.conv_hex.set_source_highlight(False)
            self.conv_rgb256.set_source_highlight(False)
            self.conv_rgb01.set_source_highlight(False)
            
            # Highlight the source box
            if source_box:
                source_box.set_source_highlight(True)

        def on_convert_focused():
            # Try focused widget first
            fw = QApplication.focusWidget()
            source_box = None
            
            if fw is self.conv_hex:
                source_box = self.conv_hex
                on_convert_from_hex()
            elif fw is self.conv_rgb256:
                source_box = self.conv_rgb256
                on_convert_from_rgb256()
            elif fw is self.conv_rgb01:
                source_box = self.conv_rgb01
                on_convert_from_rgb01()
            else:
                # Otherwise pick the first non-empty box
                if self.conv_hex.toPlainText().strip():
                    source_box = self.conv_hex
                    on_convert_from_hex()
                elif self.conv_rgb256.toPlainText().strip():
                    source_box = self.conv_rgb256
                    on_convert_from_rgb256()
                elif self.conv_rgb01.toPlainText().strip():
                    source_box = self.conv_rgb01
                    on_convert_from_rgb01()
                else:
                    # default
                    source_box = self.conv_hex
                    on_convert_from_hex()
            
            # Update visual highlighting
            update_source_highlighting(source_box)

        btn_convert.clicked.connect(on_convert_focused)
        conv_layout.addWidget(btn_convert, 2, 1, alignment=Qt.AlignCenter)

        # Connect editingFinished signals (Enter/focus-out)
        self.conv_hex.editingFinished.connect(lambda: (on_convert_from_hex(), update_source_highlighting(self.conv_hex)))
        self.conv_rgb256.editingFinished.connect(lambda: (on_convert_from_rgb256(), update_source_highlighting(self.conv_rgb256)))
        self.conv_rgb01.editingFinished.connect(lambda: (on_convert_from_rgb01(), update_source_highlighting(self.conv_rgb01)))
        
        # Connect focus tracking for visual feedback
        def on_hex_focus_changed(has_focus):
            if has_focus and self.conv_hex.toPlainText().strip():
                update_source_highlighting(self.conv_hex)
        
        def on_rgb256_focus_changed(has_focus):
            if has_focus and self.conv_rgb256.toPlainText().strip():
                update_source_highlighting(self.conv_rgb256)
        
        def on_rgb01_focus_changed(has_focus):
            if has_focus and self.conv_rgb01.toPlainText().strip():
                update_source_highlighting(self.conv_rgb01)
        
        self.conv_hex.focusChanged.connect(on_hex_focus_changed)
        self.conv_rgb256.focusChanged.connect(on_rgb256_focus_changed)
        self.conv_rgb01.focusChanged.connect(on_rgb01_focus_changed)
        
        # Save converter_hex content when it changes
        def save_converter_hex():
            self.settings.converter_hex = self.conv_hex.toPlainText()
            try:
                self.settings.save()
            except Exception:
                pass
        
        self.conv_hex.textChanged.connect(save_converter_hex)

        main_layout.addLayout(conv_layout)

        # small gap before the status bar (about half a line height now)
        try:
            spacing = max(6, self.fontMetrics().lineSpacing() // 2)
        except Exception:
            spacing = 7
        main_layout.addSpacing(spacing)

        # status bar
        self.status = QStatusBar()
        self.status.showMessage("coloraide: perceptual modes available (OKLCH/OKLAB/LCH/LAB/HWB/HSL).")
        main_layout.addWidget(self.status)

        self.setLayout(main_layout)

        # signals
        self.tile_a.clicked.connect(self.open_color_a_dialog)
        self.tile_b.clicked.connect(self.open_color_b_dialog)
        self.tile_c.clicked.connect(self.open_color_c_dialog)
        # link clicks
        try:
            # 2-color mode controls
            self.add_link.mousePressEvent = lambda e: self.add_tile_ab()
            self.sub_link.mousePressEvent = lambda e: self.remove_tile_ab()
            
            # 3-color mode controls
            self.add_link_left.mousePressEvent = lambda e: self.add_tile_ac()
            self.sub_link_left.mousePressEvent = lambda e: self.remove_tile_ac()
            self.add_link_right.mousePressEvent = lambda e: self.add_tile_cb()
            self.sub_link_right.mousePressEvent = lambda e: self.remove_tile_cb()
            
            # Mode toggle
            self.middle_label.mousePressEvent = lambda e: self.toggle_three_mode()
        except Exception:
            pass
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        self.copy_button.clicked.connect(self.copy_colors_to_clipboard)

        # Store current gradient colors for copying
        self.current_colors = []

        # initial render - set up UI for current mode
        self.update_mode_ui()
        self.rebuild_tiles()

    def update_tile_sizes(self):
        """Calculate and update tile widths to maintain uniform appearance"""
        # Get current window width (use minimum width if not yet shown)
        available_width = max(self.width(), self.minimumWidth()) - 40  # account for margins
        
        if self.three_mode:
            # Calculate total tiles and gaps for 3-color mode: A + AC + C + CB + B
            total_tiles = 3 + len(self.preview_tiles_ac) + len(self.preview_tiles_cb)
        else:
            # Calculate total tiles and gaps for 2-color mode: A + AB + B
            total_tiles = 2 + len(self.preview_tiles_ab)
        
        total_gaps = (total_tiles - 1) * self.settings.swatch_gap
        
        # Simple tile width calculation: available space divided equally between all tiles
        calculated_width = (available_width - total_gaps) // total_tiles if total_tiles > 0 else MINIMUM_TILE_WIDTH
        tile_width = max(MINIMUM_TILE_WIDTH, calculated_width)
        tile_height = DEFAULT_TILE_HEIGHT
        
        # Update master tiles
        self.tile_a.set_size(tile_width, tile_height)
        self.tile_b.set_size(tile_width, tile_height)
        self.tile_c.set_size(tile_width, tile_height)
        
        # Update preview tiles based on mode
        if self.three_mode:
            for lbl in self.preview_tiles_ac:
                lbl.setFixedSize(tile_width, tile_height)
            for lbl in self.preview_tiles_cb:
                lbl.setFixedSize(tile_width, tile_height)
        else:
            for lbl in self.preview_tiles_ab:
                lbl.setFixedSize(tile_width, tile_height)

    def resizeEvent(self, event):
        """Update tile sizes when window is resized"""
        super().resizeEvent(event)
        self.update_tile_sizes()

    def closeEvent(self, event):
        # Update settings from current UI state and save
        self.settings.model = self.settings.get_model_key(self.model_combo.currentText())
        self.settings.format = self.format_combo.currentText()
        self.settings.color_a = self.tile_a.hex
        self.settings.color_b = self.tile_b.hex
        self.settings.color_c = self.tile_c.hex
        self.settings.converter_hex = self.conv_hex.toPlainText()
        self.settings.three_mode = self.three_mode
        self.settings.ab_count = len(self.preview_tiles_ab)
        self.settings.ac_count = len(self.preview_tiles_ac)
        self.settings.cb_count = len(self.preview_tiles_cb)
        
        try:
            self.settings.save()
        except Exception:
            pass
        super().closeEvent(event)

    def open_color_a_dialog(self):
        col = QColorDialog.getColor(QColor(self.tile_a.hex), self, "Choose Tile A")
        if col.isValid():
            old_color = self.tile_a.hex
            self.tile_a.set_color(col.name())
            # Update settings and save immediately
            self.settings.color_a = self.tile_a.hex
            try:
                self.settings.save()
                self.status.showMessage(f"Color A updated: {old_color} → {self.tile_a.hex} (saved to INI)")
            except Exception:
                self.status.showMessage(f"Color A updated: {old_color} → {self.tile_a.hex} (save failed)")
            self.on_color_changed()

    def open_color_b_dialog(self):
        col = QColorDialog.getColor(QColor(self.tile_b.hex), self, "Choose Tile B")
        if col.isValid():
            old_color = self.tile_b.hex
            self.tile_b.set_color(col.name())
            # Update settings and save immediately
            self.settings.color_b = self.tile_b.hex
            try:
                self.settings.save()
                self.status.showMessage(f"Color B updated: {old_color} → {self.tile_b.hex} (saved to INI)")
            except Exception:
                self.status.showMessage(f"Color B updated: {old_color} → {self.tile_b.hex} (save failed)")
            self.on_color_changed()

    def open_color_c_dialog(self):
        col = QColorDialog.getColor(QColor(self.tile_c.hex), self, "Choose Tile C")
        if col.isValid():
            old_color = self.tile_c.hex
            self.tile_c.set_color(col.name())
            # Update settings and save immediately
            self.settings.color_c = self.tile_c.hex
            try:
                self.settings.save()
                self.status.showMessage(f"Color C updated: {old_color} → {self.tile_c.hex} (saved to INI)")
            except Exception:
                self.status.showMessage(f"Color C updated: {old_color} → {self.tile_c.hex} (save failed)")
            self.on_color_changed()

    def on_model_changed(self, model=None):
        if model is None:
            model = self.model_combo.currentText()
        # Update settings and save immediately
        self.settings.model = self.settings.get_model_key(model)
        try:
            self.settings.save()
        except Exception:
            pass
        self.on_color_changed()

    def on_format_changed(self, format_type=None):
        if format_type is None:
            format_type = self.format_combo.currentText()
        # Update settings and save immediately
        self.settings.format = format_type
        try:
            self.settings.save()
        except Exception:
            pass

    def toggle_three_mode(self):
        """Toggle between 2-color and 3-color mode"""
        self.three_mode = not self.three_mode
        self.settings.three_mode = self.three_mode
        
        # Debug: Verify colors are preserved in settings
        current_a = self.settings.color_a
        current_b = self.settings.color_b
        current_c = self.settings.color_c
        
        # Update UI to reflect mode change
        self.update_mode_ui()
        
        # Save settings immediately
        try:
            self.settings.save()
        except Exception:
            pass
        
        # Rebuild tiles and update gradients
        self.rebuild_tiles()
        
        # Status message with color verification
        mode_text = '3-color' if self.three_mode else '2-color'
        self.status.showMessage(f"Switched to {mode_text} mode. Colors: A={current_a}, B={current_b}, C={current_c}")

    def update_mode_ui(self):
        """Update UI elements to reflect current mode"""
        # Ensure tile colors are synced with settings
        self.tile_a.set_color(self.settings.color_a)
        self.tile_b.set_color(self.settings.color_b)
        self.tile_c.set_color(self.settings.color_c)
        
        # Clear existing links layout
        while self.links_layout.count():
            item = self.links_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        if self.three_mode:
            # 3-color mode: [-][+] [Tile C] [-][+]
            self.middle_label.setText('[Tile C]')
            self.middle_label.setToolTip('Click to disable 3-color mode')
            
            self.links_layout.addWidget(self.sub_link_left)
            self.links_layout.addWidget(self.add_link_left)
            self.links_layout.addWidget(self.middle_label)
            self.links_layout.addWidget(self.sub_link_right)
            self.links_layout.addWidget(self.add_link_right)
        else:
            # 2-color mode: [-] [tile] [+]
            self.middle_label.setText('[enable 3-tile]')
            self.middle_label.setToolTip('Click to enable 3-color mode')
            
            self.links_layout.addWidget(self.sub_link)
            self.links_layout.addWidget(self.middle_label)
            self.links_layout.addWidget(self.add_link)

    def copy_colors_to_clipboard(self):
        """Copy the current gradient colors to clipboard in the selected format"""
        if not self.current_colors:
            self.status.showMessage("No colors to copy.")
            return
        
        format_type = self.format_combo.currentText()
        formatted_colors = format_color_list(self.current_colors, format_type)
        
        # Join colors with newlines for easy copying
        color_text = '\n'.join(formatted_colors)
        
        clipboard = QApplication.clipboard()
        clipboard.setText(color_text)
        
        # Settings are already saved after each user input, no need to save again here

        self.status.showMessage(f"Copied {len(formatted_colors)} colors in {format_type} format to clipboard.")

    def on_color_changed(self):
        a = self.tile_a.hex
        b = self.tile_b.hex
        c = self.tile_c.hex
        # Map the friendly label to the internal key used by interpolate()
        sel = self.model_combo.currentText()
        model = self.settings.get_model_key(sel).lower()
        
        if self.three_mode:
            # 3-color mode: create AC and CB gradients using exact INI counts
            ac_steps = 2 + self.settings.ac_count  # A + AC preview tiles + C
            cb_steps = 2 + self.settings.cb_count  # C + CB preview tiles + B
            
            try:
                ac_colors = interpolate(a, c, ac_steps, model)
                cb_colors = interpolate(c, b, cb_steps, model)
            except Exception as ex:
                self.status.showMessage(f"Interpolation error for mode {model}: {ex}. Falling back to sRGB.")
                ac_colors = interpolate(a, c, ac_steps, 'srgb')
                cb_colors = interpolate(c, b, cb_steps, 'srgb')
            
            # Update only visible AC preview tiles
            for i, lbl in enumerate(self.preview_tiles_ac):
                if i < len(ac_colors) - 2:  # Exclude A and C
                    lbl.setStyleSheet(f'background: {ac_colors[i+1]}; border: 1px solid #222; border-radius: {self.settings.tile_border_radius}px;')
            
            # Update only visible CB preview tiles
            for i, lbl in enumerate(self.preview_tiles_cb):
                if i < len(cb_colors) - 2:  # Exclude C and B
                    lbl.setStyleSheet(f'background: {cb_colors[i+1]}; border: 1px solid #222; border-radius: {self.settings.tile_border_radius}px;')
            
            # Combine all colors for copying (AC without last + CB)
            all_colors = ac_colors[:-1] + cb_colors  # Remove duplicate C from AC
            self.current_colors = all_colors
            
            # Update master tiles with exact colors from gradients
            self.tile_a.set_color(ac_colors[0])
            self.tile_c.set_color(ac_colors[-1])  # Should equal cb_colors[0]
            self.tile_b.set_color(cb_colors[-1])
            
            # Smooth gradient for preview (A to C to B)
            smooth_ac = interpolate(a, c, 256, model)
            smooth_cb = interpolate(c, b, 256, model)
            smooth = smooth_ac[:-1] + smooth_cb  # Remove duplicate C
            
        else:
            # 2-color mode: create AB gradient using exact INI count
            steps = 2 + self.settings.ab_count
            try:
                colors = interpolate(a, b, steps, model)
            except Exception as ex:
                self.status.showMessage(f"Interpolation error for mode {model}: {ex}. Falling back to sRGB.")
                colors = interpolate(a, b, steps, 'srgb')

            # Store colors for copying
            self.current_colors = colors

            # Update only visible AB preview tiles
            for i, lbl in enumerate(self.preview_tiles_ab):
                if i < len(colors) - 2:  # Exclude A and B
                    lbl.setStyleSheet(f'background: {colors[i+1]}; border: 1px solid #222; border-radius: {self.settings.tile_border_radius}px;')

            # Update master tiles with exact colors from gradient
            self.tile_a.set_color(colors[0])
            self.tile_b.set_color(colors[-1])

            # Smooth gradient for preview
            smooth = interpolate(colors[0], colors[-1], 512, model)
        
        self.gradient_preview.set_colors(smooth)
        mode_text = "3-color" if self.three_mode else "2-color"
        self.status.showMessage(f"Mode: {model} ({mode_text}) — Preview updated.")

    # --- dynamic tile management ---
    def rebuild_tiles(self):
        """Rebuild the tiles_container layout according to current mode and preview tiles."""
        # Remove all items from tiles_container
        while self.tiles_container.count():
            item = self.tiles_container.takeAt(0)
            w = item.widget()
            if w is not None:
                # avoid deleting tile_a/tile_b/tile_c widgets; just hide others
                if w not in (self.tile_a, self.tile_b, self.tile_c):
                    w.setParent(None)
                else:
                    # keep existing master tiles but hide them for now
                    pass
        
        if self.three_mode:
            # 3-color mode: Show A, C, B and AC/CB gradients; hide AB gradients
            self.tile_a.show()
            self.tile_b.show()
            self.tile_c.show()
            
            # Hide AB gradient tiles
            for lbl in self.preview_tiles_ab:
                lbl.hide()
            
            # Show and add AC gradient tiles
            for lbl in self.preview_tiles_ac:
                lbl.show()
                lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            
            # Show and add CB gradient tiles
            for lbl in self.preview_tiles_cb:
                lbl.show()
                lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            
            # Layout: A + AC tiles + C + CB tiles + B
            self.tiles_container.addWidget(self.tile_a)
            for lbl in self.preview_tiles_ac:
                self.tiles_container.addWidget(lbl)
            self.tiles_container.addWidget(self.tile_c)
            for lbl in self.preview_tiles_cb:
                self.tiles_container.addWidget(lbl)
            self.tiles_container.addWidget(self.tile_b)
            
        else:
            # 2-color mode: Show A, B and AB gradients; hide C and AC/CB gradients
            self.tile_a.show()
            self.tile_b.show()
            self.tile_c.hide()
            
            # Hide AC and CB gradient tiles
            for lbl in self.preview_tiles_ac:
                lbl.hide()
            for lbl in self.preview_tiles_cb:
                lbl.hide()
            
            # Show AB gradient tiles
            for lbl in self.preview_tiles_ab:
                lbl.show()
                lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            
            # Layout: A + AB tiles + B
            self.tiles_container.addWidget(self.tile_a)
            for lbl in self.preview_tiles_ab:
                self.tiles_container.addWidget(lbl)
            self.tiles_container.addWidget(self.tile_b)
        
        # Update tile sizes and spacing
        self.update_tile_sizes()
        # Trigger layout update
        self.updateGeometry()
        self.on_color_changed()

    # 2-color mode tile management
    def add_tile_ab(self):
        """Add an intermediate tile to AB gradient if under the maximum."""
        if len(self.preview_tiles_ab) >= self.max_tiles_ab:
            self.status.showMessage(f'Already at maximum of {2 + self.max_tiles_ab} tiles.')
            return
        lbl = QLabel()
        lbl.setFixedSize(80, DEFAULT_TILE_HEIGHT)  # Initial size, will be updated by update_tile_sizes()
        lbl.setStyleSheet(f'background: #777; border: 1px solid #222; border-radius: {self.settings.tile_border_radius}px;')
        lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.preview_tiles_ab.append(lbl)
        # Update settings and save immediately
        self.settings.ab_count = len(self.preview_tiles_ab)
        try:
            self.settings.save()
        except Exception:
            pass
        self.rebuild_tiles()

    def remove_tile_ab(self):
        """Remove an intermediate tile from AB gradient if above the minimum."""
        if len(self.preview_tiles_ab) <= self.min_tiles_between:
            self.status.showMessage(f'Already at minimum of {2 + self.min_tiles_between} tiles.')
            return
        lbl = self.preview_tiles_ab.pop()
        try:
            lbl.setParent(None)
        except Exception:
            pass
        # Update settings and save immediately
        self.settings.ab_count = len(self.preview_tiles_ab)
        try:
            self.settings.save()
        except Exception:
            pass
        self.rebuild_tiles()

    # 3-color mode tile management
    def add_tile_ac(self):
        """Add an intermediate tile to AC gradient (left side)."""
        if len(self.preview_tiles_ac) >= self.max_tiles_ac:
            self.status.showMessage(f'Already at maximum of {self.max_tiles_ac} tiles for AC gradient.')
            return
        lbl = QLabel()
        lbl.setFixedSize(80, DEFAULT_TILE_HEIGHT)
        lbl.setStyleSheet(f'background: #777; border: 1px solid #222; border-radius: {self.settings.tile_border_radius}px;')
        lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.preview_tiles_ac.append(lbl)
        # Update settings and save immediately
        self.settings.ac_count = len(self.preview_tiles_ac)
        try:
            self.settings.save()
        except Exception:
            pass
        self.rebuild_tiles()

    def remove_tile_ac(self):
        """Remove an intermediate tile from AC gradient (left side)."""
        if len(self.preview_tiles_ac) <= self.min_tiles_between:
            self.status.showMessage(f'AC gradient already at minimum of {self.min_tiles_between} tiles.')
            return
        lbl = self.preview_tiles_ac.pop()
        try:
            lbl.setParent(None)
        except Exception:
            pass
        # Update settings and save immediately
        self.settings.ac_count = len(self.preview_tiles_ac)
        try:
            self.settings.save()
        except Exception:
            pass
        self.rebuild_tiles()

    def add_tile_cb(self):
        """Add an intermediate tile to CB gradient (right side)."""
        if len(self.preview_tiles_cb) >= self.max_tiles_cb:
            self.status.showMessage(f'Already at maximum of {self.max_tiles_cb} tiles for CB gradient.')
            return
        lbl = QLabel()
        lbl.setFixedSize(80, DEFAULT_TILE_HEIGHT)
        lbl.setStyleSheet(f'background: #777; border: 1px solid #222; border-radius: {self.settings.tile_border_radius}px;')
        lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.preview_tiles_cb.append(lbl)
        # Update settings and save immediately
        self.settings.cb_count = len(self.preview_tiles_cb)
        try:
            self.settings.save()
        except Exception:
            pass
        self.rebuild_tiles()

    def remove_tile_cb(self):
        """Remove an intermediate tile from CB gradient (right side)."""
        if len(self.preview_tiles_cb) <= self.min_tiles_between:
            self.status.showMessage(f'CB gradient already at minimum of {self.min_tiles_between} tiles.')
            return
        lbl = self.preview_tiles_cb.pop()
        try:
            lbl.setParent(None)
        except Exception:
            pass
        # Update settings and save immediately
        self.settings.cb_count = len(self.preview_tiles_cb)
        try:
            self.settings.save()
        except Exception:
            pass
        self.rebuild_tiles()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Set application icon (so the OS may use it for the app/window)
    try:
        icon_path = Path(__file__).parent / 'resources' / 'ColorGradientTool_icon.png'
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
    except Exception:
        pass
    # On macOS the app-switcher (Cmd-Tab) and some system UI use the app bundle icon
    # rather than the Qt window icon. If pyobjc (AppKit) is installed we can set the
    # NSApplication icon at runtime which usually fixes the Alt-Tab/Cmd-Tab icon when
    # running as a plain script. This is optional and will silently fail if pyobjc
    # isn't available.
    try:
        if sys.platform == 'darwin':
            # Import here to avoid adding a hard dependency for other platforms
            from AppKit import NSImage, NSApplication
            img = NSImage.alloc().initWithContentsOfFile_(str(icon_path))
            if img:
                NSApplication.sharedApplication().setApplicationIconImage_(img)
    except Exception:
        # If pyobjc isn't installed or something else fails, ignore.
        pass
    app.setStyleSheet(f"""
        QWidget {{ background: #28333b; color: #fff; font-family: {get_platform_font_family()}; }}
        QLabel {{ color: #eaeff2; font-size: 14px; }}
        /* Scrollbar styling to match controls */
        QScrollBar:vertical {{
            background: #2b3a42;
            width: 12px;
            margin: 0px 0px 0px 0px;
        }}
        QScrollBar::handle:vertical {{
            background: #3a4a56;
            min-height: 20px;
            border: 1px solid #555;
            border-radius: 4px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QScrollBar:horizontal {{
            background: #2b3a42;
            height: 12px;
            margin: 0px 0px 0px 0px;
        }}
        QScrollBar::handle:horizontal {{
            background: #3a4a56;
            min-width: 20px;
            border: 1px solid #555;
            border-radius: 4px;
        }}
    """)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())