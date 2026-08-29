import flet as ft
import ccxt
import pandas as pd
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
        self.exchange = ccxt.lbank({
            'enableRateLimit': True,
            'timeout': 30000,
            'options': {'defaultType': 'swap'}
        })
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

    def fetch_ohlcv(self, symbol):
        try:
            clean_symbol = symbol.replace(':USDT', '')
            return self.exchange.fetch_ohlcv(clean_symbol, '1h', limit=24)
        except:
            return []

    def run_scan(self):
        try:
            self.min_change = float(self.threshold_input.value or 50)
            self.status_text.value = "در حال دریافت نمادها از LBank..."
            self.page.update()
            
            markets = self.exchange.load_markets()
            symbols = [s for s, m in markets.items() if m.get('type') == 'swap' and m.get('active', False) and ('/USDT' in s or ':USDT' in s)]
            
            total = len(symbols)
            results = []
            
            for i, sym in enumerate(symbols):
                self.progress_bar.value = (i + 1) / total
                self.status_text.value = f"بررسی {i+1}/{total}: {sym}"
                self.page.update()
                
                ohlcv = self.fetch_ohlcv(sym)
                if len(ohlcv) >= 20:
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    p_open = df['open'].iloc[0]
                    p_close = df['close'].iloc[-1]
                    high_24h = df['high'].max()
                    low_24h = df['low'].min()
                    
                    change = ((p_close - p_open) / p_open) * 100
                    volatility = ((high_24h - low_24h) / low_24h) * 100
                    
                    if abs(change) >= self.min_change:
                        item = {
                            'symbol': sym,
                            'change': round(change, 2),
                            'volatility': round(volatility, 2),
                            'price': p_close,
                            'direction': 'صعودی 📈' if change > 0 else 'نزولی 📉'
                        }
                        results.append(item)
                        self.add_card_to_ui(item)
                        
                time.sleep(0.02)
                
            self.status_text.value = f"✅ پایان اسکن. {len(results)} نماد پیدا شد."
        except Exception as err:
            self.status_text.value = f"❌ خطا: {err}"
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
