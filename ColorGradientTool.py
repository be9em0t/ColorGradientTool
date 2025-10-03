# color_gradient_tool
# Requires: PySide6 and coloraide
# Generate color gradients in different colorspaces and 
# copy values in different formats

# ToDO:
# Edit colors in-place
# Add more/less swatches
# Add midpoint color

import sys
import math
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QComboBox, QColorDialog,
    QHBoxLayout, QVBoxLayout, QGridLayout, QSizePolicy, QStatusBar, QLineEdit
)
from PySide6.QtGui import QColor, QPainter, QPixmap, QIcon
from PySide6.QtCore import Qt, QSize

# coloraide (required)
from coloraide import Color

import colorsys
import configparser
from pathlib import Path

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
        s = f"{v:.5f}".rstrip('0').rstrip('.')
        if s.startswith('0.'):
            s = s[1:]
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


# -------------------- Qt UI --------------------

class GradientPreview(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._colors = ['#ff0000', '#0000ff']

    def set_colors(self, colors):
        self._colors = colors
        self.update_preview()

    def update_preview(self):
        w = max(200, self.width())
        h = max(40, self.height())
        pix = QPixmap(w, h)
        painter = QPainter(pix)
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


class ColorTile(QPushButton):
    def __init__(self, hexcolor, size=(140, 80)):
        super().__init__()
        self.hex = hexcolor
        self.setFixedSize(QSize(*size))
        self.setStyleSheet(f'background: {hexcolor}; border: 1px solid #222;')

    def set_color(self, hexcolor):
        self.hex = hexcolor
        self.setStyleSheet(f'background: {hexcolor}; border: 1px solid #222;')

    def mousePressEvent(self, e):
        col = QColorDialog.getColor(QColor(self.hex), self.window(), "Choose color")
        if col.isValid():
            hexc = col.name()
            self.set_color(hexc)
            self.parent().on_color_changed()
        super().mousePressEvent(e)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Color Gradient Tool — coloraide")
        # Set window icon (relative to script folder)
        try:
            icon_path = Path(__file__).parent / 'color_colors_themes_icon.png'
            if icon_path.exists():
                ico = QIcon(str(icon_path))
                self.setWindowIcon(ico)
        except Exception:
            pass
        self.setMinimumSize(980, 560)

        # Default colors
        self.color_a = '#e31b23'  # bright red
        self.color_b = '#00b0e6'  # cyan-ish

        title = QLabel("Color Gradient Tool")
        title.setStyleSheet("font-size: 28px; font-weight: 600; color: #ffffff;")
        title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Tiles row
        self.tile_a = ColorTile(self.color_a)
        self.tile_b = ColorTile(self.color_b)

        # five intermediate preview tiles
        self.preview_tiles = [QLabel() for _ in range(5)]
        for lbl in self.preview_tiles:
            lbl.setFixedSize(140, 80)
            lbl.setStyleSheet('background: #777; border: 1px solid #222;')

        # Color model selector (matching your screenshot options)
        self.model_combo = QComboBox()
        models = ['OKLCH', 'HSL', 'LAB', 'HWB', 'sRGB', 'OKLAB', 'LCH']
        for m in models:
            self.model_combo.addItem(m)
        self.model_combo.setCurrentText('OKLCH')
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
        self.format_combo.setCurrentText('Hex')
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
        self.copy_button = QPushButton('Copy Colors')
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
        self.gradient_preview = GradientPreview()

        # Layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(18)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.addWidget(title)

        top_grid = QGridLayout()
        top_grid.setHorizontalSpacing(20)
        top_grid.addWidget(QLabel("Tile A"), 0, 0, alignment=Qt.AlignLeft)

        tiles_layout = QHBoxLayout()
        tiles_layout.setSpacing(18)
        tiles_layout.addWidget(self.tile_a)
        for t in self.preview_tiles:
            tiles_layout.addWidget(t)
        tiles_layout.addWidget(self.tile_b)

        top_grid.addLayout(tiles_layout, 1, 0, 1, 3)

        # model selector and format controls under tiles with labels
        controls_layout = QGridLayout()

        # Labels above the selectors
        label_space = QLabel("Color space")
        label_space.setStyleSheet('color: #eaeff2;')
        label_format = QLabel("Color format")
        label_format.setStyleSheet('color: #eaeff2;')

        controls_layout.addWidget(label_space, 0, 0, alignment=Qt.AlignLeft)
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
        gl.addWidget(QLabel("Gradient preview"))
        gl.addWidget(self.gradient_preview)
        main_layout.addLayout(gl)

        # --- Color format converter fields (independent utility) ---
        conv_layout = QGridLayout()
        lbl_rgb01 = QLabel('RGB(0-1)')
        lbl_rgb256 = QLabel('RGB(256)')
        lbl_hex = QLabel('Hex')
        lbl_rgb01.setStyleSheet('color: #eaeff2;')
        lbl_rgb256.setStyleSheet('color: #eaeff2;')
        lbl_hex.setStyleSheet('color: #eaeff2;')

        self.conv_rgb01 = QLineEdit()
        self.conv_rgb256 = QLineEdit()
        self.conv_hex = QLineEdit()

        # Place labels above the fields
        conv_layout.addWidget(lbl_rgb01, 0, 0)
        conv_layout.addWidget(lbl_rgb256, 0, 1)
        conv_layout.addWidget(lbl_hex, 0, 2)

        conv_layout.addWidget(self.conv_rgb01, 1, 0)
        conv_layout.addWidget(self.conv_rgb256, 1, 1)
        conv_layout.addWidget(self.conv_hex, 1, 2)

        # Initialize converter hex to tile A by default; load_config() will override if INI has a value
        self.conv_hex.setText(self.tile_a.hex)

        # Initialize other fields from the hex value
        try:
            hx = parse_hex_string(self.conv_hex.text())
            r01 = hex_to_rgb01(hx)
            r256 = hex_to_rgb256(hx)
            self.conv_rgb01.setText(format_rgb01_from_tuple(r01))
            self.conv_rgb256.setText(format_rgb256_from_tuple(tuple(int(round(x*255)) for x in r01)))
            # store normalized hex
            self.conv_hex.setText(hx)
        except Exception:
            pass

        # Handlers (avoid recursion with a flag)
        self._conv_updating = False

        def on_rgb01_changed():
            if self._conv_updating:
                return
            txt = self.conv_rgb01.text()
            try:
                vals = parse_rgb01_string(txt)
                # update others
                self._conv_updating = True
                self.conv_rgb256.setText(format_rgb256_from_tuple(tuple(int(round(v*255)) for v in vals)))
                hx = rgb01_to_hex(vals)
                self.conv_hex.setText(hx)
                # clear validation styling on success
                self.conv_rgb01.setStyleSheet('')
                self.conv_rgb256.setStyleSheet('')
                self.conv_hex.setStyleSheet('')
                self._conv_updating = False
            except Exception:
                # invalid input - indicate visually
                try:
                    self.conv_rgb01.setStyleSheet('border: 2px solid #d9534f;')
                except Exception:
                    pass
                self._conv_updating = False

        def on_rgb256_changed():
            if self._conv_updating:
                return
            txt = self.conv_rgb256.text()
            try:
                vals = parse_rgb256_string(txt)
                self._conv_updating = True
                r01 = tuple(v/255.0 for v in vals)
                self.conv_rgb01.setText(format_rgb01_from_tuple(r01))
                hx = rgb01_to_hex(r01)
                self.conv_hex.setText(hx)
                # clear validation styling on success
                self.conv_rgb256.setStyleSheet('')
                self.conv_rgb01.setStyleSheet('')
                self.conv_hex.setStyleSheet('')
                self._conv_updating = False
            except Exception:
                # invalid input - indicate visually
                try:
                    self.conv_rgb256.setStyleSheet('border: 2px solid #d9534f;')
                except Exception:
                    pass
                self._conv_updating = False

        def on_hex_changed():
            if self._conv_updating:
                return
            txt = self.conv_hex.text()
            try:
                hx = parse_hex_string(txt)
                self._conv_updating = True
                r01 = hex_to_rgb01(hx)
                self.conv_rgb01.setText(format_rgb01_from_tuple(r01))
                self.conv_rgb256.setText(format_rgb256_from_tuple(tuple(int(round(x*255)) for x in r01)))
                self.conv_hex.setText(hx)
                # Persist converter hex in ini under [ui].converter_hex
                try:
                    cfg = configparser.ConfigParser()
                    if self.config_path.exists():
                        cfg.read(self.config_path)
                    if not cfg.has_section('ui'):
                        cfg.add_section('ui')
                    cfg.set('ui', 'converter_hex', hx)
                    with open(self.config_path, 'w', encoding='utf-8') as f:
                        cfg.write(f)
                except Exception:
                    pass
                # clear validation styling on success
                self.conv_hex.setStyleSheet('')
                self.conv_rgb01.setStyleSheet('')
                self.conv_rgb256.setStyleSheet('')
                self._conv_updating = False
            except Exception:
                # invalid input - indicate visually
                try:
                    self.conv_hex.setStyleSheet('border: 2px solid #d9534f;')
                except Exception:
                    pass
                self._conv_updating = False

        # Update only when the user finishes editing (focus out or Enter)
        self.conv_rgb01.editingFinished.connect(on_rgb01_changed)
        self.conv_rgb256.editingFinished.connect(on_rgb256_changed)
        self.conv_hex.editingFinished.connect(on_hex_changed)

        main_layout.addLayout(conv_layout)

        # status bar
        self.status = QStatusBar()
        self.status.showMessage("coloraide: perceptual modes available (OKLCH/OKLAB/LCH/LAB/HWB/HSL).")
        main_layout.addWidget(self.status)

        self.setLayout(main_layout)

        # config file path (use explicit filename ColorGradient.ini for consistency)
        self.config_path = Path(__file__).parent / 'ColorGradient.ini'

        # Load previous settings if present
        self.load_config()

        # signals
        self.tile_a.clicked.connect(self.open_color_a_dialog)
        self.tile_b.clicked.connect(self.open_color_b_dialog)
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        self.copy_button.clicked.connect(self.copy_colors_to_clipboard)

        # Store current gradient colors for copying
        self.current_colors = []

        # initial render
        self.on_color_changed()

    def closeEvent(self, event):
        # Save settings when window is closed
        try:
            self.save_config()
        except Exception:
            pass
        super().closeEvent(event)

    def load_config(self):
        """Load last-used settings from ColorGradient.ini"""
        cfg = configparser.ConfigParser()
        if not self.config_path.exists():
            return
        try:
            cfg.read(self.config_path)
            if cfg.has_section('ui'):
                model = cfg.get('ui', 'model', fallback=None)
                fmt = cfg.get('ui', 'format', fallback=None)
                a = cfg.get('ui', 'color_a', fallback=None)
                b = cfg.get('ui', 'color_b', fallback=None)
                ch = cfg.get('ui', 'converter_hex', fallback=None)
                if model and model in [self.model_combo.itemText(i) for i in range(self.model_combo.count())]:
                    self.model_combo.setCurrentText(model)
                if fmt and fmt in [self.format_combo.itemText(i) for i in range(self.format_combo.count())]:
                    self.format_combo.setCurrentText(fmt)
                if a:
                    self.tile_a.set_color(a)
                if b:
                    self.tile_b.set_color(b)
                # Apply converter_hex if present (avoid triggering handlers)
                if ch:
                    try:
                        self._conv_updating = True
                        hx = parse_hex_string(ch)
                        self.conv_hex.setText(hx)
                        r01 = hex_to_rgb01(hx)
                        self.conv_rgb01.setText(format_rgb01_from_tuple(r01))
                        self.conv_rgb256.setText(format_rgb256_from_tuple(tuple(int(round(x*255)) for x in r01)))
                    except Exception:
                        pass
                    finally:
                        self._conv_updating = False
        except Exception:
            # ignore config errors
            return

    def save_config(self):
        """Save current settings to ColorGradient.ini"""
        cfg = configparser.ConfigParser()
        cfg['ui'] = {
            'model': self.model_combo.currentText(),
            'format': self.format_combo.currentText(),
            'color_a': self.tile_a.hex,
            'color_b': self.tile_b.hex,
            'converter_hex': self.conv_hex.text(),
        }
        with open(self.config_path, 'w', encoding='utf-8') as f:
            cfg.write(f)

    def open_color_a_dialog(self):
        col = QColorDialog.getColor(QColor(self.tile_a.hex), self, "Choose Tile A")
        if col.isValid():
            self.tile_a.set_color(col.name())
            self.on_color_changed()

    def open_color_b_dialog(self):
        col = QColorDialog.getColor(QColor(self.tile_b.hex), self, "Choose Tile B")
        if col.isValid():
            self.tile_b.set_color(col.name())
            self.on_color_changed()

    def on_model_changed(self, model=None):
        if model is None:
            model = self.model_combo.currentText()
        self.on_color_changed()

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
        
        # Save settings now — user pressed Copy which indicates desired settings
        try:
            self.save_config()
        except Exception:
            pass

        self.status.showMessage(f"Copied {len(formatted_colors)} colors in {format_type} format to clipboard.")

    def on_color_changed(self):
        a = self.tile_a.hex
        b = self.tile_b.hex
        model = self.model_combo.currentText()
        steps = 7  # tile A + 5 mid + tile B
        try:
            colors = interpolate(a, b, steps, model)
        except Exception as ex:
            self.status.showMessage(f"Interpolation error for mode {model}: {ex}. Falling back to sRGB.")
            colors = interpolate_srgb_linear(a, b, steps)

        # Store colors for copying
        self.current_colors = colors

        # update preview tiles (middle 5)
        for i, lbl in enumerate(self.preview_tiles):
            lbl.setStyleSheet(f'background: {colors[i+1]}; border: 1px solid #222;')

        # update tile A and B (in case fitted to gamut changed them)
        self.tile_a.set_color(colors[0])
        self.tile_b.set_color(colors[-1])

        # smooth gradient (many steps)
        smooth = interpolate(colors[0], colors[-1], 512, model)
        self.gradient_preview.set_colors(smooth)
        self.status.showMessage(f"Mode: {model} — Preview updated.")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Set application icon (so the OS may use it for the app/window)
    try:
        icon_path = Path(__file__).parent / 'color_colors_themes_icon.png'
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
    app.setStyleSheet("""
        QWidget { background: #28333b; color: #fff; font-family: "Segoe UI", Roboto, Arial; }
        QLabel { color: #eaeff2; font-size: 14px; }
    """)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())