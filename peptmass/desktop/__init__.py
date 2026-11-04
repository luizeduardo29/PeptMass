"""Interface desktop (PyQt6). O backend do matplotlib precisa vir antes dos graficos."""

import matplotlib

matplotlib.use("QtAgg")
