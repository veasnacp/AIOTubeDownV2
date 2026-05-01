from .theme import DarkMode, LightMode
from PySide6.QtGui import QColor


def get_gradient(start_color: QColor, end_color: QColor, direction: str = "vertical") -> str:
    """Generates a subtle QSS linear gradient based on a theme color."""
    # Create a slightly lighter/vibrant version for the start point
    # start_color = start_color.lighter(100).name()
    start_color_name = start_color.name()
    end_color_name = end_color.name()

    if direction == "vertical":
        return f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {start_color_name}, stop:1 {end_color_name})"
    return f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {start_color_name}, stop:1 {end_color_name})"


class ThemeProvider:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ThemeProvider, cls).__new__(cls)
            cls._instance.current_theme = LightMode  # Default
            cls._instance.subscribers = []
        return cls._instance

    def subscribe(self, widget):
        """Register a widget to receive theme updates."""
        self.subscribers.append(widget)

    def get_gradient(self, start_color: QColor, end_color: QColor, direction: str = "vertical") -> str:
        """Generates a subtle QSS linear gradient based on a theme color."""
        return get_gradient(start_color, end_color, direction)

    def set_current_theme(self, theme_name: str):
        """Manually set a theme and notify subscribers."""
        self.current_theme = DarkMode if theme_name.lower() == "dark" else LightMode

    def on_theme_change(self, new_theme):
        pass

    def apple_current_theme(self):
        self.on_theme_change(self.current_theme)
        # Update all subscribed widgets
        for widget in self.subscribers:
            if hasattr(widget, 'apply_theme'):
                widget.apply_theme(self.current_theme)

        # Update the main window background if it's the root
        # if self.subscribers:
        #     root = self.subscribers[0].window()
        #     root.setStyleSheet(
        #         f"background-color: {self.current_theme.background};")

    def set_manual_theme(self, theme_name: str):
        """Manually set a theme and notify subscribers."""
        self.current_theme = DarkMode if theme_name.lower() == "dark" else LightMode
        self.apple_current_theme()

    def toggle_theme(self):
        """Switch between Light and Dark and update all widgets."""
        self.current_theme = DarkMode if self.current_theme.name == "light" else LightMode

        self.apple_current_theme()


# Global instance
theme_provider = ThemeProvider()
