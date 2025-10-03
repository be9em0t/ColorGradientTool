# main.py
# PyQt6 GUI and application logic for ColorGradientTool
# Requires: PySide6 and coloraide

import sys
import math
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QComboBox, QColorDialog,
    QHBoxLayout, QVBoxLayout, QGridLayout, QSizePolicy, QStatusBar, QTextEdit
)
from PySide6.QtGui import QColor, QPainter, QPixmap, QIcon
from PySide6.QtCore import Qt, QSize, Signal
from pathlib import Path

# Import our modules
from color import (
    interpolate, format_color_list, ColorParser, 
    lerp, parse_hex_string, hex_to_rgb01, rgb01_to_hex,
    format_rgb01_from_tuple, format_rgb256_from_tuple
)
from settings import Settings

# UI spacing constants
# Gap between color swatches (px). Change this value to adjust spacing.
SWATCH_GAP = 9


class GradientPreview(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Match the height of the color swatches (80 px)
        self.setFixedHeight(80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._colors = ['#ff0000', '#0000ff']

    def set_colors(self, colors):
        self._colors = colors
        self.update_preview()

    def update_preview(self):
        w = max(200, self.width())
        # Use the widget's actual height (fixed to match swatches)
        h = max(1, self.height())
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


class MultilineEdit(QTextEdit):
    """QTextEdit that emits editingFinished on focus out, Ctrl+Enter, or Enter when single-line."""
    editingFinished = Signal()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Avoid accepting rich text from clipboard sources
        try:
            self.setAcceptRichText(False)
        except Exception:
            pass

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        try:
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
            icon_path = Path(__file__).parent / 'resources' / 'ColorGradientTool_icon.png'
            if icon_path.exists():
                ico = QIcon(str(icon_path))
                self.setWindowIcon(ico)
        except Exception:
            pass
        
        self.setMinimumSize(980, 560)

        # Initialize settings
        config_path = Path(__file__).parent / 'ColorGradient.ini'
        self.settings = Settings(config_path)
        self.settings.load()

        # Default colors from settings
        self.color_a = self.settings.color_a
        self.color_b = self.settings.color_b

        title = QLabel("Color Gradient Tool")
        title.setStyleSheet("font-size: 28px; font-weight: 600; color: #ffffff;")
        title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Tiles row
        self.tile_a = ColorTile(self.color_a)
        self.tile_b = ColorTile(self.color_b)

        # dynamic intermediate preview tiles (default to 5 between A and B => total 7)
        self.min_tiles_between = 1  # at least one between? keep semantics: min total tiles = 3 => 1 between
        self.max_tiles_between = 9  # max total tiles = 11 => 9 between
        self.tiles_between = 5
        self.preview_tiles = []
        for _ in range(self.tiles_between):
            lbl = QLabel()
            lbl.setFixedHeight(80)
            lbl.setStyleSheet('background: #777; border: 1px solid #222;')
            self.preview_tiles.append(lbl)

        # Add/remove link-like labels (styled) centered between the Tile A and Tile B labels
        self.add_link = QLabel('[+]')
        self.add_link.setStyleSheet('color: #4588C4; font-size: 14px;')
        self.add_link.setCursor(Qt.PointingHandCursor)
        self.add_link.setToolTip('Add a tile (max 11 total)')

        self.sub_link = QLabel('[-]')
        self.sub_link.setStyleSheet('color: #4588C4; font-size: 14px;')
        self.sub_link.setCursor(Qt.PointingHandCursor)
        self.sub_link.setToolTip('Remove a tile (min 3 total)')

        self.middle_label = QLabel('[tile]')
        self.middle_label.setStyleSheet('color: #4588C4; font-size: 14px;')
        self.middle_label.setAlignment(Qt.AlignCenter)

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
        self.gradient_preview = GradientPreview()

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
        tiles_layout.setSpacing(SWATCH_GAP)
        # We'll create a container layout that we can rebuild when the number of tiles changes
        self.tiles_container = QHBoxLayout()
        self.tiles_container.setSpacing(SWATCH_GAP)
        # initial population
        self.tiles_container.addWidget(self.tile_a)
        for t in self.preview_tiles:
            self.tiles_container.addWidget(t)
        self.tiles_container.addWidget(self.tile_b)

        # Insert add/remove links centered on the label row: create a small widget layout for them
        links_widget = QWidget()
        links_layout = QHBoxLayout()
        links_layout.setContentsMargins(0, 0, 0, 0)
        links_layout.setSpacing(8)
        links_layout.addWidget(self.sub_link)
        links_layout.addWidget(self.middle_label)
        links_layout.addWidget(self.add_link)
        links_widget.setLayout(links_layout)

        # Put tiles in the main tiles_layout. Place the add/remove links on the label row
        tiles_layout.addLayout(self.tiles_container)
        # Add the links widget to the label row (row 0, column 1) so it appears centered between the labels
        top_grid.addWidget(links_widget, 0, 1, alignment=Qt.AlignCenter)

        top_grid.addLayout(tiles_layout, 1, 0, 1, 3)

        # model selector and format controls under tiles with labels
        controls_layout = QGridLayout()

        # Labels above the selectors
        label_space = QLabel("Color space")
        label_space.setStyleSheet('color: #eaeff2;')
        # Help icon next to Color space (use simple text '[?]' for cross-platform reliability)
        help_icon = QLabel('[?]')
        help_icon.setStyleSheet('color: #4588C4; font-size: 13px; padding-left: 6px;')
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
        # Converter area: three multiline boxes for Hex, RGB(256), RGB(0-1)
        lbl_hex = QLabel('Hex')
        lbl_hex.setStyleSheet('color: #eaeff2;')
        lbl_rgb256 = QLabel('RGB(256)')
        lbl_rgb256.setStyleSheet('color: #eaeff2;')
        lbl_rgb01 = QLabel('RGB(0-1)')
        lbl_rgb01.setStyleSheet('color: #eaeff2;')

        self.conv_hex = MultilineEdit()
        self.conv_rgb256 = MultilineEdit()
        self.conv_rgb01 = MultilineEdit()
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
            src.setStyleSheet('')
            lines = [l.strip() for l in self.conv_hex.toPlainText().splitlines() if l.strip()]
            try:
                hexs, r256, r01 = ColorParser.parse_hex_lines(lines)
            except Exception as e:
                src.setStyleSheet('border: 2px solid #d9534f;')
                self.status.showMessage(f'Conversion failed: invalid Hex input. {e}')
                return
            # success - clear any error outlines
            self.conv_hex.setStyleSheet('')
            self.conv_rgb256.setStyleSheet('')
            self.conv_rgb01.setStyleSheet('')
            self.conv_hex.setPlainText('\n'.join(hexs))
            self.conv_rgb256.setPlainText('\n'.join(r256))
            self.conv_rgb01.setPlainText('\n'.join(r01))
            self.status.showMessage(f'Converted {len(hexs)} lines from Hex.')

        def on_convert_from_rgb256():
            src = self.conv_rgb256 
            src.setStyleSheet('')
            lines = [l.strip() for l in self.conv_rgb256.toPlainText().splitlines() if l.strip()]
            try:
                hexs, r256, r01 = ColorParser.parse_rgb256_lines(lines)
            except Exception as e:
                src.setStyleSheet('border: 2px solid #d9534f;')
                self.status.showMessage(f'Conversion failed: invalid RGB(256) input. {e}')
                return
            # success - clear any error outlines
            self.conv_hex.setStyleSheet('')
            self.conv_rgb256.setStyleSheet('')
            self.conv_rgb01.setStyleSheet('')
            self.conv_hex.setPlainText('\n'.join(hexs))
            self.conv_rgb256.setPlainText('\n'.join(r256))
            self.conv_rgb01.setPlainText('\n'.join(r01))
            self.status.showMessage(f'Converted {len(hexs)} lines from RGB(256).')

        def on_convert_from_rgb01():
            src = self.conv_rgb01
            src.setStyleSheet('')
            lines = [l.strip() for l in self.conv_rgb01.toPlainText().splitlines() if l.strip()]
            try:
                hexs, r256, r01 = ColorParser.parse_rgb01_lines(lines)
            except Exception as e:
                src.setStyleSheet('border: 2px solid #d9534f;')
                self.status.showMessage(f'Conversion failed: invalid RGB(0-1) input. {e}')
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

            # success - clear any error outlines
            self.conv_hex.setStyleSheet('')
            self.conv_rgb256.setStyleSheet('')
            self.conv_rgb01.setStyleSheet('')
            self.conv_hex.setPlainText('\n'.join(hexs))
            self.conv_rgb256.setPlainText('\n'.join(r256))
            self.conv_rgb01.setPlainText('\n'.join(r01_with_leading))
            self.status.showMessage(f'Converted {len(hexs)} lines from RGB(0-1).')

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
                color: #eaeff2;
            }
            QPushButton:hover {
                background-color: #4a5a66;
            }
            QPushButton:pressed {
                background-color: #2a3a46;
            }
        """)

        def on_convert_focused():
            # Try focused widget first
            fw = QApplication.focusWidget()
            if fw is self.conv_hex:
                on_convert_from_hex()
                return
            if fw is self.conv_rgb256:
                on_convert_from_rgb256()
                return
            if fw is self.conv_rgb01:
                on_convert_from_rgb01()
                return
            # Otherwise pick the first non-empty box
            if self.conv_hex.toPlainText().strip():
                on_convert_from_hex(); return
            if self.conv_rgb256.toPlainText().strip():
                on_convert_from_rgb256(); return
            if self.conv_rgb01.toPlainText().strip():
                on_convert_from_rgb01(); return
            # default
            on_convert_from_hex()

        btn_convert.clicked.connect(on_convert_focused)
        conv_layout.addWidget(btn_convert, 2, 1, alignment=Qt.AlignCenter)

        # Connect editingFinished signals (Enter/focus-out)
        self.conv_hex.editingFinished.connect(on_convert_from_hex)
        self.conv_rgb256.editingFinished.connect(on_convert_from_rgb256)
        self.conv_rgb01.editingFinished.connect(on_convert_from_rgb01)

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
        # link clicks
        try:
            self.add_link.mousePressEvent = lambda e: self.add_tile()
            self.sub_link.mousePressEvent = lambda e: self.remove_tile()
        except Exception:
            pass
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        self.copy_button.clicked.connect(self.copy_colors_to_clipboard)

        # Store current gradient colors for copying
        self.current_colors = []

        # initial render
        self.on_color_changed()

    def closeEvent(self, event):
        # Update settings from current UI state and save
        self.settings.model = self.settings.get_model_key(self.model_combo.currentText())
        self.settings.format = self.format_combo.currentText()
        self.settings.color_a = self.tile_a.hex
        self.settings.color_b = self.tile_b.hex
        self.settings.converter_hex = self.conv_hex.toPlainText()
        
        try:
            self.settings.save()
        except Exception:
            pass
        super().closeEvent(event)

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
        
        # Update settings in memory
        self.settings.model = self.settings.get_model_key(self.model_combo.currentText())
        self.settings.format = self.format_combo.currentText()
        self.settings.color_a = self.tile_a.hex
        self.settings.color_b = self.tile_b.hex
        self.settings.converter_hex = self.conv_hex.toPlainText()
        
        # Save settings now — user pressed Copy which indicates desired settings
        try:
            self.settings.save()
        except Exception:
            pass

        self.status.showMessage(f"Copied {len(formatted_colors)} colors in {format_type} format to clipboard.")

    def on_color_changed(self):
        a = self.tile_a.hex
        b = self.tile_b.hex
        # Map the friendly label to the internal key used by interpolate()
        sel = self.model_combo.currentText()
        model = self.settings.get_model_key(sel).lower()
        # total steps is tile A + tiles_between + tile B
        steps = 2 + len(self.preview_tiles)
        try:
            colors = interpolate(a, b, steps, model)
        except Exception as ex:
            self.status.showMessage(f"Interpolation error for mode {model}: {ex}. Falling back to sRGB.")
            colors = interpolate(a, b, steps, 'srgb')

        # Store colors for copying
        self.current_colors = colors

        # update preview tiles (dynamic)
        for i, lbl in enumerate(self.preview_tiles):
            lbl.setStyleSheet(f'background: {colors[i+1]}; border: 1px solid #222;')

        # update tile A and B (in case fitted to gamut changed them)
        self.tile_a.set_color(colors[0])
        self.tile_b.set_color(colors[-1])

        # smooth gradient (many steps)
        smooth = interpolate(colors[0], colors[-1], 512, model)
        self.gradient_preview.set_colors(smooth)
        self.status.showMessage(f"Mode: {model} — Preview updated.")

    # --- dynamic tile management ---
    def rebuild_tiles(self):
        """Rebuild the tiles_container layout according to current preview_tiles list."""
        # Remove all items from tiles_container
        while self.tiles_container.count():
            item = self.tiles_container.takeAt(0)
            w = item.widget()
            if w is not None:
                # avoid deleting tile_a/tile_b widgets; just hide others
                if w not in (self.tile_a, self.tile_b):
                    w.setParent(None)
                else:
                    # keep existing edge tiles
                    pass
        # Re-add in order
        self.tiles_container.addWidget(self.tile_a)
        for lbl in self.preview_tiles:
            # ensure label has the right fixed size
            lbl.setFixedHeight(80)
            # compute a width that will allow them to scale when window resizes by using expanding policy
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.tiles_container.addWidget(lbl)
        self.tiles_container.addWidget(self.tile_b)
        # Trigger layout update
        self.updateGeometry()
        self.on_color_changed()

    def add_tile(self):
        """Add an intermediate tile if under the maximum."""
        if len(self.preview_tiles) >= self.max_tiles_between:
            self.status.showMessage('Already at maximum of 11 tiles.')
            return
        lbl = QLabel()
        lbl.setFixedHeight(80)
        lbl.setStyleSheet('background: #777; border: 1px solid #222;')
        self.preview_tiles.append(lbl)
        self.rebuild_tiles()

    def remove_tile(self):
        """Remove an intermediate tile if above the minimum."""
        if len(self.preview_tiles) <= self.min_tiles_between:
            self.status.showMessage('Already at minimum of 3 tiles.')
            return
        lbl = self.preview_tiles.pop()
        try:
            lbl.setParent(None)
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
    app.setStyleSheet("""
        QWidget { background: #28333b; color: #fff; font-family: "Segoe UI", Roboto, Arial; }
        QLabel { color: #eaeff2; font-size: 14px; }
        /* Scrollbar styling to match controls */
        QScrollBar:vertical {
            background: #2b3a42;
            width: 12px;
            margin: 0px 0px 0px 0px;
        }
        QScrollBar::handle:vertical {
            background: #3a4a56;
            min-height: 20px;
            border: 1px solid #555;
            border-radius: 4px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QScrollBar:horizontal {
            background: #2b3a42;
            height: 12px;
            margin: 0px 0px 0px 0px;
        }
        QScrollBar::handle:horizontal {
            background: #3a4a56;
            min-width: 20px;
            border: 1px solid #555;
            border-radius: 4px;
        }
    """)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())