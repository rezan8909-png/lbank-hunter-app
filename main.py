import flet as ft
import urllib.request
import json
import time
from datetime import datetime
import threading

class PriceChangeHunterApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "🎯 ربات شکار نوسان LBank Futures"
        self.page.rtl = True
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.scroll = ft.ScrollMode.AUTO
        
        self.is_scanning = False
        self.cache = {}
        self.cache_time = {}
        self.cache_duration = 10
        
        self.setup_ui()

    def setup_ui(self):
        self.title_text = ft.Text("🎯 شکارچی ارزهای پرنوسان فیوچرز LBank", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_400)
        self.sub_text = ft.Text("بررسی دقیق ۲۴ کندل ۱ ساعته اخیر (Swap / USDT)", size=12, color=ft.Colors.GREY_400)
        
        self.threshold_input = ft.TextField(
            label="حداقل تغییر قیمت (%)",
            value="50",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=160,
            text_align=ft.TextAlign.CENTER
        )
        
        self.scan_btn = ft.ElevatedButton(
            "شروع اسکن",
            icon=ft.Icons.PLAY_ARROW,
            style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
            on_click=self.start_scan_thread,
            height=48
        )
        
        self.progress_bar = ft.ProgressBar(width=340, visible=False)
        self.status_text = ft.Text("آماده برای اسکن", size=13, color=ft.Colors.GREY_300)
        self.summary_container = ft.Container(visible=False)
        self.cards_list = ft.ListView(expand=True, spacing=10, auto_scroll=False)
        
        self.page.add(
            ft.Column([
                self.title_text,
                self.sub_text,
                ft.Row([self.threshold_input, self.scan_btn], alignment=ft.MainAxisAlignment.CENTER),
                self.progress_bar,
                self.status_text,
                self.summary_container,
                ft.Divider(color=ft.Colors.GREY_800),
                self.cards_list
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
        )

    def http_get_json(self, url):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.loads(res.read().decode('utf-8'))

    def get_all_futures_symbols(self):
        """دریافت لیست تمامی نمادهای فعال فیوچرز LBank"""
        url = "https://lbkperp.lbank.com/cfd/openApi/v1/pub/instrument"
        try:
            res = self.http_get_json(url)
            symbols = []
            data = res.get("data", [])
            for item in data:
                # نمادهای فعال مارکت فیوچرز تتر
                inst_id = item.get("instrumentId", "")
                if inst_id and "USDT" in inst_id.upper():
                    symbols.append(inst_id)
            return symbols
        except Exception:
            # روش جایگزین دریافت نمادها
            try:
                url_alt = "https://lbkperp.lbank.com/cfd/openApi/v1/pub/marketData"
                res = self.http_get_json(url_alt)
                return [x.get("instrumentId") for x in res.get("data", []) if "USDT" in str(x.get("instrumentId", "")).upper()]
            except:
                return []

    def fetch_ohlcv(self, symbol):
        """دریافت ۲۴ کندل ۱ ساعته برای هر نماد دقیقا مطابق لاجیک fetch_ohlcv"""
        now = time.time()
        key = f"ohlcv_{symbol}"
        if key in self.cache and (now - self.cache_time.get(key, 0)) < self.cache_duration:
            return self.cache[key]
            
        url = f"https://lbkperp.lbank.com/cfd/openApi/v1/pub/kline?instrumentId={symbol}&period=1h&limit=24"
        try:
            res = self.http_get_json(url)
            klines = res.get("data", [])
            if klines:
                self.cache[key] = klines
                self.cache_time[key] = now
                return klines
        except:
            pass
        return []

    def calculate_price_change(self, ohlcv, min_change):
        """محاسبات دقیق کدهای شما بدون نیاز به pandas"""
        if len(ohlcv) < 20:
            return None
        
        # ساختار کندل: [timestamp, open, high, low, close, volume] یا دیکشنری
        closes = []
        highs = []
        lows = []
        volumes = []
        
        for k in ohlcv:
            if isinstance(k, dict):
                o = float(k.get("open", 0))
                h = float(k.get("high", 0))
                l = float(k.get("low", 0))
                c = float(k.get("close", 0))
                v = float(k.get("volume", 0) or k.get("vol", 0))
                t = int(k.get("time", 0) or k.get("timestamp", 0))
            else:
                t, o, h, l, c, v = k[0], float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])
            
            if len(closes) == 0:
                price_24h_ago = o
            closes.append(c)
            highs.append(h)
            lows.append(l)
            volumes.append(v)
            last_timestamp = t

        current_price = closes[-1]
        high_24h = max(highs)
        low_24h = min(lows)

        if price_24h_ago == 0 or low_24h == 0:
            return None

        # ========== تغییر قیمت از ۲۴ ساعت پیش تا الان ==========
        price_change = ((current_price - price_24h_ago) / price_24h_ago) * 100
        volatility = ((high_24h - low_24h) / low_24h) * 100

        # جهت حرکت
        if current_price > price_24h_ago:
            direction = "🟢 صعودی"
            emoji = "📈"
        elif current_price < price_24h_ago:
            direction = "🔴 نزولی"
            emoji = "📉"
        else:
            direction = "⚪ بدون تغییر"
            emoji = "➖"

        # شدت تغییر قیمت
        abs_change = abs(price_change)
        if abs_change >= 100:
            intensity = "💥💥💥 فوق‌العاده (۱۰۰%+)"
            rank = "🚀🚀🚀"
        elif abs_change >= 75:
            intensity = "💥💥 بسیار شدید (۷۵-۱۰۰%)"
            rank = "🚀🚀"
        elif abs_change >= 50:
            intensity = "💥 شدید (۵۰-۷۵%)"
            rank = "🚀"
        else:
            intensity = "تغییر معمولی"
            rank = "📊"

        # حجم معاملات نسبت به میانگین
        avg_volume = sum(volumes) / len(volumes) if len(volumes) > 0 else 1
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        price_range = high_24h - low_24h

        return {
            'price_change': round(price_change, 2),
            'volatility': round(volatility, 2),
            'direction': direction,
            'emoji': emoji,
            'intensity': intensity,
            'rank': rank,
            'price_24h_ago': price_24h_ago,
            'current_price': current_price,
            'high_24h': high_24h,
            'low_24h': low_24h,
            'price_range': price_range,
            'volume_ratio': round(volume_ratio, 2),
            'is_high_price_change': abs_change >= min_change,
            'last_time': datetime.fromtimestamp(last_timestamp/1000 if last_timestamp > 1e11 else last_timestamp).strftime('%H:%M')
        }

    def start_scan_thread(self, e):
        if self.is_scanning:
            return
        self.is_scanning = True
        self.scan_btn.disabled = True
        self.progress_bar.visible = True
        self.summary_container.visible = False
        self.cards_list.controls.clear()
        self.page.update()
        
        threading.Thread(target=self.run_scan, daemon=True).start()

    def run_scan(self):
        try:
            min_change = float(self.threshold_input.value or 50)
            self.status_text.value = "در حال دریافت نمادهای فیوچرز LBank..."
            self.page.update()
            
            symbols = self.get_all_futures_symbols()
            if not symbols:
                self.status_text.value = "❌ خطای دریافت نمادها. اتصال اینترنت/فیلترشکن را بررسی کنید."
                return

            total = len(symbols)
            self.status_text.value = f"تعداد {total} نماد پیدا شد. در حال بررسی کندل‌های ۲۴ ساعته..."
            self.page.update()

            results = []
            for i, sym in enumerate(symbols):
                self.progress_bar.value = (i + 1) / total
                if (i + 1) % 10 == 0 or i == total - 1:
                    self.status_text.value = f"بررسی {i+1}/{total} نماد | کشف شده: {len(results)}"
                    self.page.update()

                try:
                    ohlcv = self.fetch_ohlcv(sym)
                    data = self.calculate_price_change(ohlcv, min_change)
                    if data and data['is_high_price_change']:
                        item = {
                            'symbol': sym,
                            'price_change': data['price_change'],
                            'volatility': data['volatility'],
                            'direction': data['direction'],
                            'emoji': data['emoji'],
                            'rank': data['rank'],
                            'intensity': data['intensity'],
                            'current_price': data['current_price'],
                            'price_24h_ago': data['price_24h_ago'],
                            'high_24h': data['high_24h'],
                            'low_24h': data['low_24h'],
                            'volume_ratio': data['volume_ratio'],
                            'last_time': data['last_time']
                        }
                        results.append(item)
                        self.add_card_to_ui(item)
                except Exception:
                    continue
                time.sleep(0.04)

            # مرتب‌سازی بر اساس بیشترین تغییر
            results.sort(key=lambda x: abs(x['price_change']), reverse=True)
            self.cards_list.controls.clear()
            for r in results:
                self.add_card_to_ui(r)

            if len(results) > 0:
                self.status_text.value = f"✅ اسکن تمام شد: {len(results)} ارز با تغییر بالای {min_change}% پیدا شد."
            else:
                self.status_text.value = f"⚠️ هیچ ارزی با تغییر بالای {min_change}% در {total} نماد پیدا نشد."

        except Exception as err:
            self.status_text.value = f"❌ خطای اجرا: {err}"
        finally:
            self.progress_bar.visible = False
            self.scan_btn.disabled = False
            self.is_scanning = False
            self.page.update()

    def add_card_to_ui(self, r):
        is_bull = r['price_change'] > 0
        card_color = ft.Colors.GREEN_950 if is_bull else ft.Colors.RED_950
        border_color = ft.Colors.GREEN_500 if is_bull else ft.Colors.RED_500
        
        card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(f"{r['rank']} {r['emoji']} {r['symbol']}", size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Text(f"{r['price_change']:+.2f}%", size=17, weight=ft.FontWeight.BOLD, 
                                color=ft.Colors.GREEN_ACCENT if is_bull else ft.Colors.RED_ACCENT)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text(f"شدت: {r['intensity']}", size=12, color=ft.Colors.AMBER_200),
                    ft.Divider(height=2, color=ft.Colors.WHITE24),
                    ft.Row([
                        ft.Text(f"قیمت فعلی: ${r['current_price']:.5f}", size=12, color=ft.Colors.WHITE70),
                        ft.Text(f"۲۴ساعت پیش: ${r['price_24h_ago']:.5f}", size=12, color=ft.Colors.WHITE70),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Row([
                        ft.Text(f"دامنه نوسان: {r['volatility']}%", size=12, color=ft.Colors.WHITE70),
                        ft.Text(f"حجم: {r['volume_ratio']}x میانگین", size=12, color=ft.Colors.CYAN_200),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ], spacing=5),
                padding=12,
                bgcolor=card_color,
                border=ft.border.all(1, border_color),
                border_radius=10
            )
        )
        self.cards_list.controls.append(card)
        self.page.update()

def main(page: ft.Page):
    PriceChangeHunterApp(page)

if __name__ == '__main__':
    ft.app(target=main)
