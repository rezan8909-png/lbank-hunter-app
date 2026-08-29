import flet as ft
import urllib.request
import json
import threading

class FuturesHunterApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "LBank Futures Scanner"
        self.page.rtl = True
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.scroll = ft.ScrollMode.AUTO
        self.is_scanning = False
        
        self.setup_ui()

    def setup_ui(self):
        self.title_text = ft.Text("⚡ اسکنر فیوچرز LBank", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_400)
        self.sub_text = ft.Text("فقط قراردادهای پرپچوال USDT (Futures)", size=12, color=ft.Colors.GREY_400)
        
        self.threshold_input = ft.TextField(
            label="حداقل درصد تغییر (۲۴h)",
            value="3",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=180,
            text_align=ft.TextAlign.CENTER
        )
        
        self.scan_btn = ft.ElevatedButton(
            "شروع اسکن فیوچرز",
            icon=ft.Icons.BOLT,
            style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
            on_click=self.start_scan_thread,
            height=48
        )
        
        self.progress_bar = ft.ProgressBar(width=340, visible=False)
        self.status_text = ft.Text("آماده برای اسکن بازار فیوچرز...", size=13, color=ft.Colors.GREY_400)
        self.cards_list = ft.ListView(expand=True, spacing=10, auto_scroll=False)
        
        self.page.add(
            ft.Column([
                self.title_text,
                self.sub_text,
                ft.Row([self.threshold_input, self.scan_btn], alignment=ft.MainAxisAlignment.CENTER),
                self.progress_bar,
                self.status_text,
                ft.Divider(color=ft.Colors.GREY_800),
                self.cards_list
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
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
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36',
            'Accept': 'application/json'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as response:
            return json.loads(response.read().decode('utf-8'))

    def fetch_futures_tickers(self):
        """دریافت اختصاصی لیست تیکرهای فیوچرز LBank"""
        futures_endpoints = [
            # اندپوینت رسمی CFD/Futures
            "https://lbkperp.lbank.com/cfd/openApi/v1/pub/marketData",
            # اندپوینت رسمی عمومی قراردادهای پرپچوال
            "https://api.lbank.info/v2/supplement/futures/ticker.do"
        ]
        
        for url in futures_endpoints:
            try:
                res = self.http_get(url)
                if isinstance(res, dict):
                    data = res.get("data")
                    if isinstance(data, list) and len(data) > 0:
                        return data
                    elif isinstance(data, dict):
                        return list(data.values())
                elif isinstance(res, list) and len(res) > 0:
                    return res
            except Exception:
                continue
        return []

    def run_scan(self):
        try:
            raw_input = self.threshold_input.value or "3"
            min_change = float(raw_input.strip())
            
            self.status_text.value = "در حال اتصال به مارکت فیوچرز LBank..."
            self.page.update()
            
            tickers = self.fetch_futures_tickers()
            total = len(tickers)
            
            if total == 0:
                self.status_text.value = "❌ خطای دریافت اطلاعات فیوچرز. فیلترشکن را بررسی کنید."
                return

            self.status_text.value = f"در حال فیلتر {total} نماد فیوچرز..."
            self.page.update()
            
            results = []
            
            for item in tickers:
                # استخراج شناسه نماد فیوچرز (معمولا به فرمت BTC_USDT یا BTCUSDT یا instrumentId)
                sym = item.get("instrumentId") or item.get("symbol") or item.get("contractCode") or ""
                sym = str(sym).upper().replace("-", "_")
                
                # فیلتر قطعی فقط قراردادهای فیوچرز مبتنی بر USDT
                if "USDT" not in sym:
                    continue

                # استخراج درصد تغییر ۲۴ ساعته فیوچرز
                raw_change = (
                    item.get("priceChangePercent") or 
                    item.get("change") or 
                    item.get("changePercent") or 
                    item.get("percent") or 0.0
                )
                try:
                    change = float(raw_change)
                    # اصلاح اگر مقدار کسری بود (مثلاً 0.04 -> 4.0%)
                    if -1.0 < change < 1.0 and change != 0:
                        change = change * 100.0
                except:
                    change = 0.0

                # آخرین قیمت معامله شده فیوچرز
                raw_price = (
                    item.get("lastPrice") or 
                    item.get("latestPrice") or 
                    item.get("markPrice") or 
                    item.get("price") or 0.0
                )
                try:
                    price = float(raw_price)
                except:
                    price = 0.0

                # بالاترین و پایین‌ترین قیمت ۲۴ ساعت گذشته
                raw_high = item.get("highPrice") or item.get("high") or item.get("high24hr") or price
                raw_low = item.get("lowPrice") or item.get("low") or item.get("low24hr") or price
                try:
                    high = float(raw_high)
                    low = float(raw_low)
                    volatility = round(((high - low) / low) * 100, 2) if low > 0 else 0.0
                except:
                    volatility = 0.0

                # حجم ۲۴ ساعته فیوچرز در صورت وجود
                raw_volume = item.get("volume24h") or item.get("volume") or item.get("turnover") or 0.0
                try:
                    volume = float(raw_volume)
                except:
                    volume = 0.0

                # اعمال فیلتر حداقل درصد تغییر
                if abs(change) >= min_change:
                    card_data = {
                        'symbol': sym,
                        'change': round(change, 2),
                        'volatility': volatility,
                        'price': price,
                        'volume': volume,
                        'direction': '🟢 LONG / صعودی' if change > 0 else '🔴 SHORT / نزولی'
                    }
                    results.append(card_data)
                    self.add_card_to_ui(card_data)

            if len(results) > 0:
                self.status_text.value = f"✅ اسکن تمام شد: {len(results)} نماد فیوچرز با تغییر بالای {min_change}% یافت شد."
            else:
                self.status_text.value = f"⚠️ نماد فیوچرز با تغییر بالای {min_change}% پیدا نشد."

        except Exception as err:
            self.status_text.value = f"❌ خطا: {err}"
        finally:
            self.progress_bar.visible = False
            self.scan_btn.disabled = False
            self.is_scanning = False
            self.page.update()

    def add_card_to_ui(self, item):
        is_bull = item['change'] >= 0
        card_color = ft.Colors.GREEN_950 if is_bull else ft.Colors.RED_950
        border_color = ft.Colors.GREEN_400 if is_bull else ft.Colors.RED_400
        
        card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Row([
                            ft.Icon(ft.Icons.SHOW_CHART if is_bull else ft.Icons.CALL_RECEIVED, 
                                    color=ft.Colors.GREEN_ACCENT if is_bull else ft.Colors.RED_ACCENT, size=20),
                            ft.Text(item['symbol'], size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
                        ], spacing=6),
                        ft.Text(f"{item['change']:+.2f}%", size=18, weight=ft.FontWeight.BOLD, 
                                color=ft.Colors.GREEN_ACCENT if is_bull else ft.Colors.RED_ACCENT)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(height=2, color=ft.Colors.WHITE24),
                    ft.Row([
                        ft.Text(f"قیمت: ${item['price']:.5f}", size=13, color=ft.Colors.WHITE70),
                        ft.Text(f"دامنه نوسان: {item['volatility']}%", size=13, color=ft.Colors.WHITE70)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Row([
                        ft.Text(item['direction'], size=13, weight=ft.FontWeight.BOLD, 
                                color=ft.Colors.GREEN_300 if is_bull else ft.Colors.RED_300)
                    ], alignment=ft.MainAxisAlignment.END)
                ], spacing=6),
                padding=12,
                bgcolor=card_color,
                border=ft.border.all(1, border_color),
                border_radius=10
            )
        )
        self.cards_list.controls.append(card)
        self.page.update()

def main(page: ft.Page):
    FuturesHunterApp(page)

if __name__ == '__main__':
    ft.app(target=main)
