"""
theme.py - Chalkboard & Neon-Pastel Design System for solvertools_hub.
Enforces a consistent global QSS palette and QPainter glow rendering utilities.
"""

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath


class ChalkTheme:
    """Color tokens and styles for the Chalkboard & Neon-Pastel aesthetic."""

    # --- Surfaces ---
    BG_CHALK_BLACK = "#0F1412"    # Deep obsidian-tinted chalkboard black
    BG_SLATE_GREEN = "#16211D"    # Dark forest chalkboard green (sidebars, panels)
    BG_BOARD_RAISED = "#1E2D27"   # Elevated surface for interactive controls & cells
    BG_PANEL_ALT = "#1E2D27"      # Semantic alias for elevated panel background
    FG_CHALK_DUST = "#3A4D45"     # Muted dusty green-grey for borders and inactive slots
    BORDER_MUTED = "#3A4D45"      # Semantic alias for subtle borders

    # --- Typography ---
    FG_CHALK_WHITE = "#EAE6DF"    # Warm off-white chalk tone for high readability
    FG_CHALK_MUTED = "#96A8A0"    # Faded sage chalk for metadata, coordinates, labels

    # --- Pastels & Tokens (Expanded Palette up to 16 Colors) ---
    PASTEL_MINT = "#A8E6CF"
    PASTEL_LAVENDER = "#D7BDE2"
    PASTEL_PEACH = "#FAD7A0"
    PASTEL_SKY = "#A9CCE3"
    PASTEL_ROSE = "#F5B7B1"
    PASTEL_LEMON = "#F9E79F"
    PASTEL_CORAL = "#FF8B94"
    PASTEL_TEAL = "#56DFB2"
    PASTEL_LILAC = "#B39DDB"
    PASTEL_APRICOT = "#FFB74D"
    PASTEL_CYAN = "#81D4FA"
    PASTEL_LIME = "#C5E1A5"
    PASTEL_BERRY = "#F48FB1"
    PASTEL_SAGE = "#80CBC4"
    PASTEL_AMBER = "#FFE082"
    PASTEL_PERIWINKLE = "#9FA8DA"

    # --- Distinct High-Contrast Dynamic Palette ---
    # Maximally distinguishable hues across the spectrum, vibrant against dark slate blackboard
    DISTINCT_PALETTE = [
        "#FF4757",  # 1:  Vivid Crimson Red
        "#00D2D3",  # 2:  Bright Electric Cyan
        "#FFA502",  # 3:  Warm Gold / Amber
        "#2ED573",  # 4:  Neon Emerald Green
        "#8854D0",  # 5:  Electric Purple
        "#FF3385",  # 6:  Hot Magenta Pink
        "#3867D6",  # 7:  Royal Cobalt Blue
        "#FA8231",  # 8:  Vibrant Tangerine Orange
        "#A3CB38",  # 9:  Lime Chartreuse
        "#E84393",  # 10: Wild Orchid
        "#10AC84",  # 11: Deep Teal
        "#FD9644",  # 12: Coral Peach
        "#F5F6FA",  # 13: Chalk White
        "#4B6584",  # 14: Slate Charcoal
        "#FED330",  # 15: Sunny Sunflower Yellow
        "#6C5CE7",  # 16: Iris Violet
        "#B33939",  # 17: Deep Burgundy Wine
        "#00CEC9",  # 18: Aqua Marine
        "#B87333",  # 19: Warm Copper Bronze
        "#D63031",  # 20: Chili Red
    ]

    PASTEL_PALETTE = DISTINCT_PALETTE

    @classmethod
    def get_color(cls, index: int) -> str:
        """
        Returns a high-contrast, visually distinguishable hex color for any index.
        Uses the curated 20-color distinct spectrum, and falls back to golden-ratio
        hue stepping for arbitrary higher indices.
        """
        if 0 <= index < len(cls.DISTINCT_PALETTE):
            return cls.DISTINCT_PALETTE[index]
        import colorsys
        golden_ratio_conjugate = 0.618033988749895
        h = (0.05 + index * golden_ratio_conjugate) % 1.0
        l = 0.58 if index % 2 == 0 else 0.68
        s = 0.85
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return f"#{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}"

    @classmethod
    def get_contrast_text_color(cls, hex_color: str) -> str:
        """
        Returns '#0A0D0C' (dark charcoal) or '#FFFFFF' (pure white) based on background
        luminance to ensure crystal-clear text readability over any color.
        """
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            return "#0A0D0C" if lum > 145 else "#FFFFFF"
        return "#FFFFFF"

    # --- Neons (Emphasis, Active Cursors, Solved Paths, Alerts) ---
    NEON_CYAN = "#00F5D4"     # Glowing electric cyan (active cursor, search head)
    NEON_LIME = "#B5FF4D"     # Neon chartreuse (solved path highlights, success)
    NEON_CORAL = "#FF4D80"    # Vibrant neon pink/coral (errors, conflicts, dead ends)
    NEON_AMBER = "#FFB800"    # Neon amber warning / auxiliary highlight

    @classmethod
    def get_stylesheet(cls) -> str:
        """Returns the application-wide Qt Style Sheet (QSS)."""
        return f"""
        QMainWindow, QWidget {{
            background-color: {cls.BG_CHALK_BLACK};
            color: {cls.FG_CHALK_WHITE};
            font-family: "Consolas", "Source Code Pro", "Segoe UI", monospace;
            font-size: 13px;
        }}
        QFrame#PanelFrame {{
            background-color: {cls.BG_SLATE_GREEN};
            border: 1px solid {cls.FG_CHALK_DUST};
            border-radius: 6px;
        }}
        QListWidget {{
            background-color: {cls.BG_SLATE_GREEN};
            border: 1px solid {cls.FG_CHALK_DUST};
            border-radius: 6px;
            padding: 4px;
            outline: none;
        }}
        QListWidget::item {{
            padding: 10px 12px;
            border-radius: 4px;
            color: {cls.FG_CHALK_MUTED};
            margin-bottom: 2px;
        }}
        QListWidget::item:hover {{
            background-color: {cls.BG_BOARD_RAISED};
            color: {cls.FG_CHALK_WHITE};
        }}
        QListWidget::item:selected {{
            background-color: {cls.BG_BOARD_RAISED};
            color: {cls.NEON_CYAN};
            border-left: 3px solid {cls.NEON_CYAN};
            font-weight: bold;
        }}
        QPushButton {{
            background-color: {cls.BG_BOARD_RAISED};
            color: {cls.FG_CHALK_WHITE};
            border: 1px solid {cls.FG_CHALK_DUST};
            border-radius: 4px;
            padding: 6px 12px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            border: 1px solid {cls.PASTEL_MINT};
            color: {cls.PASTEL_MINT};
        }}
        QPushButton:pressed {{
            background-color: {cls.FG_CHALK_DUST};
        }}
        QPushButton:disabled {{
            color: {cls.FG_CHALK_DUST};
            border-color: {cls.BG_BOARD_RAISED};
            background-color: {cls.BG_CHALK_BLACK};
        }}
        QPushButton#NeonActionBtn {{
            border: 1px solid {cls.NEON_CYAN};
            color: {cls.NEON_CYAN};
        }}
        QPushButton#NeonActionBtn:hover {{
            background-color: #003B33;
        }}
        QPushButton#InstantActionBtn {{
            border: 1px solid {cls.NEON_LIME};
            color: {cls.NEON_LIME};
        }}
        QPushButton#InstantActionBtn:hover {{
            background-color: #263812;
        }}
        QPushButton#DangerActionBtn {{
            border: 1px solid {cls.NEON_CORAL};
            color: {cls.NEON_CORAL};
        }}
        QPushButton#DangerActionBtn:hover {{
            background-color: #40101C;
        }}
        QTextEdit, QPlainTextEdit {{
            background-color: {cls.BG_SLATE_GREEN};
            border: 1px solid {cls.FG_CHALK_DUST};
            border-radius: 4px;
            color: {cls.FG_CHALK_WHITE};
            padding: 6px;
        }}
        QSlider::groove:horizontal {{
            height: 6px;
            background: {cls.BG_BOARD_RAISED};
            border-radius: 3px;
        }}
        QSlider::sub-page:horizontal {{
            background: {cls.PASTEL_MINT};
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {cls.NEON_CYAN};
            width: 14px;
            margin-top: -4px;
            margin-bottom: -4px;
            border-radius: 7px;
        }}
        QSpinBox, QComboBox, QLineEdit {{
            background-color: {cls.BG_BOARD_RAISED};
            border: 1px solid {cls.FG_CHALK_DUST};
            border-radius: 4px;
            padding: 4px 8px;
            color: {cls.FG_CHALK_WHITE};
        }}
        QSpinBox:focus, QComboBox:focus, QLineEdit:focus {{
            border: 1px solid {cls.NEON_CYAN};
        }}
        QSplitter::handle {{
            background-color: {cls.FG_CHALK_DUST};
        }}
        QScrollBar:vertical {{
            background: {cls.BG_SLATE_GREEN};
            width: 10px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {cls.FG_CHALK_DUST};
            min-height: 20px;
            border-radius: 5px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {cls.PASTEL_MINT};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        """

    @staticmethod
    def draw_neon_rect(
        painter: QPainter,
        rect: QRectF,
        hex_color: str,
        radius: float = 6.0,
        glow_width: int = 6
    ) -> None:
        """Helper to render a soft dual-pass neon glow border around a QRectF."""
        base_color = QColor(hex_color)
        glow_color = QColor(base_color.red(), base_color.green(), base_color.blue(), 55)

        painter.save()
        # Outer Glow Pass
        painter.setPen(QPen(glow_color, glow_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)
        # Core Crisp Pass
        painter.setPen(QPen(base_color, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawRoundedRect(rect, radius, radius)
        painter.restore()

    @staticmethod
    def draw_neon_path(
        painter: QPainter,
        path: QPainterPath,
        hex_color: str,
        glow_width: int = 8,
        core_width: float = 2.5
    ) -> None:
        """Helper to render a soft dual-pass neon glow along an arbitrary QPainterPath."""
        base_color = QColor(hex_color)
        glow_color = QColor(base_color.red(), base_color.green(), base_color.blue(), 55)

        painter.save()
        # Outer Glow Pass
        painter.setPen(QPen(glow_color, glow_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
        # Core Crisp Pass
        painter.setPen(QPen(base_color, core_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)
        painter.restore()
