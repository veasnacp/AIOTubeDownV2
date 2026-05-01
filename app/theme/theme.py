from dataclasses import dataclass

from PySide6.QtGui import QColor

@dataclass
class ShadcnTheme:
    name: str
    background: str
    foreground: str
    card: str
    card_soft_light: str
    card_foreground: str
    popover: str
    popover_foreground: str
    primary: str
    primary_foreground: str
    secondary: str
    secondary_foreground: str
    muted: str
    muted_foreground: str
    accent: str
    accent_foreground: str
    destructive: str
    destructive_foreground: str
    border: str
    input: str
    ring: str
    chart_1: str
    chart_2: str
    chart_3: str
    chart_4: str
    chart_5: str
    sidebar: str
    sidebar_foreground: str
    sidebar_primary: str
    sidebar_primary_foreground: str
    sidebar_accent: str
    sidebar_accent_foreground: str
    sidebar_border: str
    sidebar_ring: str
    radius: str
    shadow_color: str

    def alpha(self, color_val: str, opacity: float = None) -> str:
        """
        Returns a color with modified opacity.
        Usage: theme.alpha(theme.primary, 0.2) -> 'rgba(..., 0.2)'
        """
        q_color = QColor(color_val)
        if not q_color.isValid():
            return color_val
    
        return f"rgba({q_color.red()}, {q_color.green()}, {q_color.blue()}, {opacity if opacity is not None else q_color.alphaF()})"
    
LightMode = ShadcnTheme(
    name="light",
    background="#fbfcf8",
    foreground="#0f172a",
    card="#ffffff",
    card_soft_light="#ffffff",
    card_foreground="#0f172a",
    popover="#f6f4f4",
    popover_foreground="#0f172a",
    primary="#aff33e",
    primary_foreground="#000000",
    secondary="#334155",
    secondary_foreground="#f8fafc",
    muted="#f1f5f9",
    muted_foreground="#64748b",
    accent="#f0fdf4",
    accent_foreground="#166534",
    destructive="#ef4444",
    destructive_foreground="#ffffff",
    border="#e2e8f0",
    input="#e2e8f0",
    ring="#aff33e",
    chart_1="#aff33e",
    chart_2="#334155",
    chart_3="#22c55e",
    chart_4="#64748b",
    chart_5="#94a3b8",
    sidebar="#ffffff",
    sidebar_foreground="#0f172a",
    sidebar_primary="#aff33e",
    sidebar_primary_foreground="#000000",
    sidebar_accent="#f8fafc",
    sidebar_accent_foreground="#0f172a",
    sidebar_border="#f1f5f9",
    sidebar_ring="#aff33e",
    shadow_color="#000000",
    radius="16px"
)

DarkMode = ShadcnTheme(
    name="dark",
    background="#0f1d29",
    foreground="#f8fafc",
    card="#193448",
    card_soft_light="#1e4663",
    card_foreground="#f8fafc",
    popover="#13283a",
    popover_foreground="#f8fafc",
    primary="#aff33e",
    primary_foreground="#000000",
    secondary="#1e293b",
    secondary_foreground="#f8fafc",
    muted="#1e293b",
    muted_foreground="#94a3b8",
    accent="#14532d",
    accent_foreground="#aff33e",
    destructive="#991b1b",
    destructive_foreground="#ffffff",
    border="#485770",
    input="#556277",
    ring="#aff33e",
    chart_1="#aff33e",
    chart_2="#3b82f6",
    chart_3="#22c55e",
    chart_4="#a855f7",
    chart_5="#f59e0b",
    sidebar="#020617",
    sidebar_foreground="#f8fafc",
    sidebar_primary="#aff33e",
    sidebar_primary_foreground="#000000",
    sidebar_accent="#1e293b",
    sidebar_accent_foreground="#f8fafc",
    sidebar_border="#1e293b",
    sidebar_ring="#aff33e",
    shadow_color="#000000",
    radius="16px"
)
