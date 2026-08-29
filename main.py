import flet as ft
import urllib.request
import json
import threading
import time

class PriceHunterApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "LBank Price Hunter"
        self.page.rtl = True
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.scroll = ft.ScrollMode.AUTO
        
        self.min_change = 50.0
        self.is_scanning = False
        
        self.setup_ui()

    def setup_ui(self):
        self.title_text = ft.Text("🎯 شکارچی تغییر قیمت LBank", size=20, weight=ft.FontWeight.BOLD)
        
        self.threshold_input = ft.TextField(
            label="حداقل درصد تغییر (۲۴h)",
            value="50",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=180
        )
        
        self.scan_btn = ft.ElevatedButton(
            "شروع اسکن",
            icon=ft.Icons.PLAY_ARROW,
            style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
            on_click=self.start_scan_thread
        )
        
        self.progress_bar = ft.ProgressBar(width=320, visible=False)
        self.status_text = ft.Text("", size=13, color=ft.Colors.GREY_400)
        self.cards_list = ft.ListView(expand=True, spacing=10, auto_scroll=False)
        
        self.page.add(
            ft.Column([
                self.title_text,
                ft.Row([self.threshold_input, self.scan_btn], alignment=ft.MainAxisAlignment.CENTER),
                self.progress_bar,
                self.status_text,
                ft.Divider(),
                self.cards_list
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12)
        )

    def start_scan_thread(self, e):
        if self.is_scanning:
            return
        self.is_scanning = True
        self.scan_btn.disabled = True
        self.progress_bar.visible = True
        self.cards_list.controls.clear()
        self.page.update()
        
        threading.Thread(target=self.run_scan, daemon=True).start()

    def http_get(self, url):
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))

    def fetch_tickers(self):
        # دریافت اطلاعات ۲۴ ساعته تمام ارزهای فیوچرز LBank
        url = "https://lbkperp.lbank.com/cfd/openApi/v1/pub/marketData"
        data = self.http_get(url)
        if data.get("result") == "true" or data.get("data"):
            return data.get("data", [])
        return []

    def run_scan(self):
        try:
            self.min_change = float(self.threshold_input.value or 50)
            self.status_text.value = "در حال دریافت بازارها از LBank..."
            self.page.update()
            
            tickers = self.fetch_tickers()
            if not tickers:
                # تلاش با اندپوینت عمومی جایگزین
                url_alt = "https://api.lbkex.com/v2/supplement/ticker/24hr.do"
                alt_data = self.http_get(url_alt)
                tickers = alt_data.get("data", [])

            total = len(tickers)
            results = []
            
            for i, item in enumerate(tickers):
                self.progress_bar.value = (i + 1) / total if total > 0 else 0
                sym = item.get("instrumentId") or item.get("symbol", "")
                
                # فیلتر جفت ارزهای تتر
                if "USDT" not in sym.upper():
                    continue

                self.status_text.value = f"بررسی {i+1}/{total}: {sym}"
                self.page.update()
                
                try:
                    # درصد تغییر و قیمت
                    change = float(item.get("priceChangePercent") or item.get("change") or 0.0)
                    price = float(item.get("lastPrice") or item.get("latestPrice") or item.get("price") or 0.0)
                    high = float(item.get("highPrice") or item.get("high") or price)
                    low = float(item.get("lowPrice") or item.get("low") or price)
                    
                    volatility = round(((high - low) / low) * 100, 2) if low > 0 else 0.0

                    if abs(change) >= self.min_change:
                        card_data = {
                            'symbol': sym.upper(),
                            'change': round(change, 2),
                            'volatility': volatility,
                            'price': price,
                            'direction': 'صعودی 📈' if change > 0 else 'نزولی 📉'
                        }
                        results.append(card_data)
                        self.add_card_to_ui(card_data)
                except Exception:
                    continue
                
            self.status_text.value = f"✅ پایان اسکن. {len(results)} نماد با تغییر بالای {self.min_change}% پیدا شد."
        except Exception as err:
            self.status_text.value = f"❌ خطا در اتصال به اینترنت: {err}"
        finally:
            self.progress_bar.visible = False
            self.scan_btn.disabled = False
            self.is_scanning = False
            self.page.update()

    def add_card_to_ui(self, item):
        is_bull = item['change'] > 0
        card_color = ft.Colors.GREEN_900 if is_bull else ft.Colors.RED_900
        
        card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(item['symbol'], size=15, weight=ft.FontWeight.BOLD),
                        ft.Text(f"{item['change']:+.2f}%", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_ACCENT if is_bull else ft.Colors.RED_ACCENT)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text(f"قیمت: ${item['price']:.6f} | نوسان: {item['volatility']}% | {item['direction']}", size=12)
                ]),
                padding=10,
                bgcolor=card_color,
                border_radius=8
            )
        )
        self.cards_list.controls.append(card)
        self.page.update()

def main(page: ft.Page):
    PriceHunterApp(page)

if __name__ == '__main__':
    ft.app(target=main)
