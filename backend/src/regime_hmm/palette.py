"""
Shared regime color palette.
Colors are assigned by regime id (id % len(REGIME_COLORS)) so the plot and the
frontend report always agree on which color belongs to which regime.
"""

REGIME_COLORS = [
    "#00E5FF",  # cyan
    "#FF2E63",  # red-pink
    "#7CFF4F",  # lime
    "#FFD400",  # yellow
    "#B266FF",  # violet
    "#FF8A00",  # orange
    "#FF4FD8",  # magenta
    "#3D7BFF",  # blue
    "#00FFA3",  # mint
    "#F5F5F5",  # white
]

def regime_color(regime) -> str:
    return REGIME_COLORS[int(regime) % len(REGIME_COLORS)]
