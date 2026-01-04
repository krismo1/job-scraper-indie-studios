"""
Scraper Base con Playwright
Proyecto: Sistema de Búsqueda Indie/Outsourcing
Autor: Cristian Meza Venegas

Clase base para todos los scrapers usando Playwright
"""

from playwright.sync_api import sync_playwright, Page, Browser
from bs4 import BeautifulSoup
import time
from datetime import datetime
from typing import List, Dict, Optional


class PlaywrightScraper:
    """
    Clase base para scrapers con Playwright

    Ventajas de Playwright:
    - Ejecuta JavaScript como navegador real
    - Evita detección anti-bot
    - Captura contenido dinámico
    - Simula interacciones humanas
    """

    def __init__(self, headless: bool = True, delay: int = 2):
        """
        Inicializar scraper

        Args:
            headless: Si True, navegador invisible. Si False, ves el navegador.
            delay: Segundos de espera entre acciones (simular humano)
        """
        self.headless = headless
        self.delay = delay
        self.playwright = None
        self.browser = None
        self.page = None

    def start_browser(self):
        """Iniciar navegador Playwright"""
        print(f"[{self._timestamp()}] Iniciando navegador...")

        self.playwright = sync_playwright().start()

        # Iniciar Chromium con configuración anti-detección
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )

        # Crear contexto con User-Agent real
        context = self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )

        self.page = context.new_page()
        print(f"[{self._timestamp()}] ✓ Navegador iniciado")

    def navigate_to(self, url: str, wait_selector: str = None):
        """
        Navegar a URL y esperar carga

        Args:
            url: URL objetivo
            wait_selector: Selector CSS a esperar (opcional)
        """
        print(f"[{self._timestamp()}] Navegando a: {url}")

        try:
            # Navegar con timeout de 30 segundos
            self.page.goto(url, wait_until="domcontentloaded", timeout=60000)


            # Esperar selector específico si se proporciona
            if wait_selector:
                print(f"[{self._timestamp()}] Esperando selector: {wait_selector}")
                self.page.wait_for_selector(wait_selector, timeout=15000)

            # Delay para simular lectura humana
            time.sleep(self.delay)

            print(f"[{self._timestamp()}] ✓ Página cargada")
            return True

        except Exception as e:
            print(f"[{self._timestamp()}] ✗ Error navegando: {e}")
            return False

    def get_html(self) -> str:
        """Obtener HTML completo de la página actual"""
        return self.page.content()

    def parse_html(self, html: str) -> BeautifulSoup:
        """Convertir HTML a objeto BeautifulSoup"""
        return BeautifulSoup(html, 'html.parser')

    def scroll_page(self, times: int = 3):
        """
        Hacer scroll para cargar contenido dinámico

        Args:
            times: Número de scrolls hacia abajo
        """
        print(f"[{self._timestamp()}] Haciendo scroll {times} veces...")

        for i in range(times):
            self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(self.delay)
            print(f"[{self._timestamp()}] Scroll {i+1}/{times}")

    def screenshot(self, filename: str):
        """Capturar screenshot de la página"""
        self.page.screenshot(path=filename)
        print(f"[{self._timestamp()}] ✓ Screenshot guardado: {filename}")

    def close_browser(self):
        """Cerrar navegador y limpiar recursos"""
        print(f"[{self._timestamp()}] Cerrando navegador...")

        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

        print(f"[{self._timestamp()}] ✓ Navegador cerrado")

    def _timestamp(self) -> str:
        """Timestamp para logs"""
        return datetime.now().strftime('%H:%M:%S')

    def __enter__(self):
        """Context manager: iniciar"""
        self.start_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager: cerrar"""
        self.close_browser()