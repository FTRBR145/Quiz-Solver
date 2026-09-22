import time
from pathlib import Path
from typing import Optional, Tuple
from playwright.sync_api import sync_playwright, BrowserContext, Page, Locator


class BrowserAgent:
    """Agent pengendali browser Playwright untuk membaca soal kuis dan berpindah antar nomor."""

    NEXT_SELECTORS = [
        # Indonesian selectors
        "button:has-text('Berikutnya')",
        "button:has-text('Selanjutnya')",
        "button:has-text('Lanjut')",
        "button:has-text('Soal Berikutnya')",
        "button:has-text('Simpan & Lanjut')",
        "button:has-text('Simpan dan Lanjutkan')",
        "a:has-text('Berikutnya')",
        "a:has-text('Selanjutnya')",
        "input[type='button'][value*='Berikutnya']",
        "input[type='submit'][value*='Berikutnya']",
        "input[type='button'][value*='Selanjutnya']",
        "input[type='submit'][value*='Selanjutnya']",
        # English selectors
        "button:has-text('Next')",
        "button:has-text('Next Question')",
        "button:has-text('Save & Next')",
        "button:has-text('Continue')",
        "a:has-text('Next')",
        "input[type='button'][value*='Next']",
        "input[type='submit'][value*='Next']",
        # Class / ID based
        "#btn-next",
        "#next-btn",
        "#btnNext",
        ".btn-next",
        ".next-button",
        ".next-btn",
        "[aria-label*='Next']",
        "[aria-label*='Berikutnya']",
        "[aria-label*='Selanjutnya']"
    ]

    FINISH_SELECTORS = [
        "button:has-text('Selesai')",
        "button:has-text('Kumpulkan')",
        "button:has-text('Kirim')",
        "button:has-text('Submit')",
        "button:has-text('Finish')",
        "a:has-text('Selesai')",
        "input[type='submit'][value*='Selesai']",
        "input[type='submit'][value*='Submit']",
        "#btn-submit",
        "#btn-finish"
    ]

    def __init__(self, user_data_dir: Optional[str] = None):
        self.playwright = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.user_data_dir = user_data_dir or str(Path("./browser_profile").resolve())

    def start(self, headless: bool = False, initial_url: Optional[str] = None):
        """Memulai browser dengan sesi tersimpan."""
        self.playwright = sync_playwright().start()

        # Gunakan persistent context agar login / session cookie tetap tersimpan
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=headless,
            viewport={"width": 1280, "height": 800},
            args=["--start-maximized"]
        )

        pages = self.context.pages
        self.page = pages[0] if pages else self.context.new_page()

        if initial_url:
            self.page.goto(initial_url, wait_until="domcontentloaded")

    def get_current_question_content(self) -> str:
        """
        Mengekstrak teks atau cuplikan HTML dari area soal yang sedang aktif (terlihat) di layar.
        """
        if not self.page:
            raise RuntimeError("Browser belum dimulai!")

        # Jalankan ekstraksi konten pintar di browser dengan validasi visibility
        extracted_text = self.page.evaluate("""
            () => {
                const isVisible = (el) => {
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
                    return !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                };

                // Cari container yang paling spesifik untuk soal yang sedang AKTIF/TERLIHAT
                const candidateSelectors = [
                    '[data-question]',
                    '.question-card',
                    '.question-container',
                    '.quiz-question',
                    '.soal-container',
                    '.pertanyaan-wrapper',
                    '.soal',
                    '.card-question',
                    '.card-body',
                    'fieldset',
                    'form',
                    'main',
                    '#content'
                ];

                for (const selector of candidateSelectors) {
                    const elements = document.querySelectorAll(selector);
                    for (const el of elements) {
                        if (!isVisible(el)) continue;
                        const text = el.innerText ? el.innerText.trim() : '';
                        if (text.length > 20 && (text.includes('?') || text.includes('.') || text.includes('A.') || text.includes('a.'))) {
                            return text;
                        }
                    }
                }

                // Fallback: ambil teks dari elemen yang terlihat di body
                return document.body.innerText;
            }
        """)

        return extracted_text or ""

    def click_next(self, wait_seconds: float = 1.0) -> bool:
        """
        Mencari dan mengklik tombol 'Next' / 'Berikutnya' yang sedang aktif/terlihat.
        Mengembalikan True jika tombol ditemukan dan diklik, False jika tidak ditemukan.
        """
        if not self.page:
            return False

        for selector in self.NEXT_SELECTORS:
            try:
                # Cari elemen yang terlihat (visible)
                locators = self.page.locator(selector)
                count = locators.count()
                for i in range(count):
                    loc = locators.nth(i)
                    if loc.is_visible(timeout=300) and loc.is_enabled(timeout=300):
                        loc.click()
                        time.sleep(wait_seconds)
                        try:
                            self.page.wait_for_load_state("domcontentloaded", timeout=2000)
                        except Exception:
                            pass
                        return True
            except Exception:
                continue

        return False

    def is_finish_available(self) -> bool:
        """Mengecek apakah tombol Selesai / Submit / Finish yang terlihat sudah muncul di layar."""
        if not self.page:
            return False

        for selector in self.FINISH_SELECTORS:
            try:
                locators = self.page.locator(selector)
                count = locators.count()
                for i in range(count):
                    loc = locators.nth(i)
                    if loc.is_visible(timeout=300):
                        return True
            except Exception:
                continue
        return False

    def select_option(self, best_option_label: Optional[str], answer_text: Optional[str]) -> bool:
        """
        Mencoba memilih/mengklik radio button atau opsi yang cocok di halaman web (untuk Mode Otomatis).
        """
        if not self.page or not best_option_label:
            return False

        label_clean = best_option_label.strip().upper()

        # Strategi 1: Cari radio button / label berdasarkan label huruf (misal: "A", "B", dsb.)
        possible_selectors = [
            f"label:has-text('{label_clean}.')",
            f"label:has-text('{label_clean} ')",
            f"input[value='{label_clean}']",
            f"input[value='{label_clean.lower()}']",
            f"button:has-text('{label_clean}')"
        ]

        if answer_text and len(answer_text.strip()) > 3:
            short_answer = answer_text.strip()[:25]
            possible_selectors.append(f"label:has-text('{short_answer}')")

        for sel in possible_selectors:
            try:
                locator = self.page.locator(sel).first
                if locator.is_visible(timeout=500):
                    locator.click()
                    return True
            except Exception:
                continue

        return False

    def close(self):
        """Menutup browser dan mengakhiri sesi Playwright."""
        try:
            if self.context:
                self.context.close()
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass

