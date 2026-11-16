"""PeptMass desktop: a mesma interface da versao web numa janela propria.

O programa sobe o servidor web do PeptMass so para este computador
(127.0.0.1, porta livre) e o mostra num QWebEngineView. Assim o executavel
e o container tem exatamente as mesmas telas e funcoes: Inicio, Massa,
Fragmentacao, Dados experimentais, Biblioteca e Como usar, nos tres idiomas.

Dados (banco, peptideos salvos, preferencias) ficam em ~/.peptmass, como na
versao web rodando localmente.
"""

import os
import socket
import sys
import threading
import time

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices, QIcon
from PyQt6.QtWebEngineCore import (
    QWebEngineDownloadRequest, QWebEnginePage, QWebEngineProfile)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication, QFileDialog, QMainWindow, QMessageBox

HOST = "127.0.0.1"
LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets",
                    "logo-mini-128.png")


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def _wait_port(port, timeout=30.0):
    end = time.time() + timeout
    while time.time() < end:
        try:
            with socket.create_connection((HOST, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


class LocalServer:
    """Servidor web do PeptMass numa thread, so em 127.0.0.1."""

    def __init__(self):
        from waitress.server import create_server
        from peptmass.web import create_app

        # modo executavel: libera o botao "Instalar leitor de .raw"
        os.environ["PEPTMASS_DESKTOP"] = "1"
        self.port = _free_port()
        app = create_app()
        self._server = create_server(
            app, host=HOST, port=self.port, threads=8,
            max_request_body_size=app.config["MAX_CONTENT_LENGTH"] + 16 * 1024 * 1024)
        self._thread = threading.Thread(target=self._server.run, daemon=True)

    def start(self):
        self._thread.start()
        return _wait_port(self.port)

    def stop(self):
        try:
            self._server.close()
        except Exception:
            pass

    @property
    def url(self):
        return f"http://{HOST}:{self.port}/"


class Page(QWebEnginePage):
    """Links para fora do PeptMass (PubChem, WADA...) abrem no navegador."""

    def __init__(self, profile, parent, origin):
        super().__init__(profile, parent)
        self._origin = origin

    def _is_local(self, url):
        return url.scheme() in ("http", "https") and url.host() == HOST \
            and url.port() == self._origin.port()

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        if is_main_frame and url.scheme() in ("http", "https") \
                and not self._is_local(url):
            QDesktopServices.openUrl(url)
            return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)

    def createWindow(self, _type):
        # target="_blank": abre no navegador do sistema
        page = QWebEnginePage(self.profile(), self)
        page.urlChanged.connect(lambda u, p=page: (
            QDesktopServices.openUrl(u), p.deleteLater()))
        return page


class Window(QMainWindow):
    def __init__(self, server):
        super().__init__()
        self.server = server
        self.setWindowTitle("PeptMass")
        if os.path.exists(LOGO):
            self.setWindowIcon(QIcon(LOGO))
        self.resize(1440, 920)

        # perfil persistente: idioma, modo de cor e o peptideo em edicao
        # (cookies e localStorage) sobrevivem ao fechar o programa
        storage = os.path.join(os.path.expanduser("~"), ".peptmass", "janela")
        os.makedirs(storage, exist_ok=True)
        self.profile = QWebEngineProfile("PeptMass", self)
        self.profile.setPersistentStoragePath(storage)
        self.profile.setCachePath(os.path.join(storage, "cache"))
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        self.profile.downloadRequested.connect(self._download)

        self.view = QWebEngineView(self)
        self.page = Page(self.profile, self.view, QUrl(server.url))
        self.view.setPage(self.page)
        self.page.titleChanged.connect(
            lambda t: self.setWindowTitle(t or "PeptMass"))
        self.setCentralWidget(self.view)
        self.view.load(QUrl(server.url))

    def _download(self, req: QWebEngineDownloadRequest):
        """Exportacoes (CSV, Excel, PDF, TXT, Skyline): pergunta onde salvar."""
        name = req.downloadFileName() or "peptmass"
        start = os.path.join(os.path.expanduser("~"), "Downloads", name)
        path, _flt = QFileDialog.getSaveFileName(self, "Salvar", start)
        if not path:
            req.cancel()
            return
        req.setDownloadDirectory(os.path.dirname(path))
        req.setDownloadFileName(os.path.basename(path))
        req.accept()

    def closeEvent(self, event):
        self.server.stop()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PeptMass")
    try:
        server = LocalServer()
        ok = server.start()
    except Exception as exc:  # noqa: BLE001 - mostra o erro ao usuario
        ok, server = False, None
        detail = str(exc)
    else:
        detail = ""
    if not ok:
        QMessageBox.critical(
            None, "PeptMass",
            "Não foi possível iniciar o PeptMass.\n\n" + (detail or
                                                          "O servidor interno não respondeu."))
        sys.exit(1)
    win = Window(server)
    win.show()
    code = app.exec()
    server.stop()
    sys.exit(code)
