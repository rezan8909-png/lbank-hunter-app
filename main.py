import flet as ft
import urllib.request
import urllib.error
import urllib.parse
import json
import time
import threading
from datetime import datetime


class PriceChangeHunterApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "شکارچی نوسان LBank Futures"
        self.page.rtl = True
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.scroll = ft.ScrollMode.AUTO
        self.page.padding = 12

        self.is_scanning = False
        self.cache = {}
        self.cache_time = {}
        self.cache_duration = 10
        self.max_error_length = 3000

        self.setup_ui()

    # -------------------------------------------------
    # رابط کاربری
    # -------------------------------------------------

    def setup_ui(self):
 فیوچرز LBank.Text(
            "شکارچی ارزهای پرنوسان فیوچرز LBank",
            size=20,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.AMBER_400,
            text_align=ft.TextAlign.CENTER,
        )

        self.sub_text = ft.Text(
            "بررسی ۲۴ کندل یک‌ساعته اخیر در بازار Swap / USDT",
            size=12,
            color=ft.Colors.GREY_400,
            text_align=ft.TextAlign.CENTER,
        )

        self.threshold_input = ft.TextField(
            label="حداقل تغییر قیمت (%)",
            value="1",
            width=170,
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.CENTER,
        )

        self.scan_btn = ft.ElevatedButton(
            text="شروع اسکن",
            icon=ft.Icons.PLAY_ARROW,
            height=48,
            on_click=self.start_scan_thread,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.GREEN_700,
                color=ft.Colors.WHITE,
            ),
        )

        self.progress_bar = ft.ProgressBar(
            width=360,
            visible=False,
        )

        self.status_text = ft.Text(
            "آماده برای اسکن",
            size=13,
            color=ft.Colors.GREY_300,
            selectable=True,
            text_align=ft.TextAlign.CENTER,
        )

        self.summary_text = ft.Text(
            "",
            size=12,
            color=ft.Colors.CYAN_200,
            visible=False,
            selectable=True,
            text_align=ft.TextAlign.CENTER,
        )

        self.cards_list = ft.ListView(
            expand=True,
            spacing=10,
            auto_scroll=False,
        )

        self.page.add(
            ft.Column(
                [
                    self.title_text,
                    self.sub_text,
                    ft.Row(
                        [
                            self.threshold_input,
                            self.scan_btn,
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        wrap=True,
                    ),
                    self.progress_bar,
                    self.status_text,
                    self.summary_text,
                    ft.Divider(color=ft.Colors.GREY_800),
                    self.cards_list,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
                expand=True,
            )
        )

    def set_status(self, text, color=None):
        self.status_text.value = text
        if color:
            self.status_text.color = color
        self.page.update()

    # -------------------------------------------------
    # ارتباط HTTP
    # -------------------------------------------------

    def http_get_json(self, url):
        headers = {
            "User-Agent":Kit/ "Mozilla/5.0 (Linux; Android 10) "
                "AppleWebKit/537.36 Chrome/120.0 Mobile Safari/537.36"
            ),
            "Accept": "application/json,text/plain,*/*",
            "Connection": "close",
        }

        request = urllib.request.Request(
            url,
            headers=headers,
            method="GET",
        )

        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                http_code = getattr(response, "status", 200)
                raw = response.read().decode("utf-8", errors="replace")

                if http_code != 200:
                    raise Exception(
                        f"HTTP {http_code}\n"
                        f"URL: {url}\n"
                        f"پاسخ: {raw[:1000]}"
                    )

                if not raw.strip():
                    raise Exception(
                        f"پاسخ خالی از سرور دریافت شد.\nURL: {url}"
                    )

                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    raise Exception(
                        f"پاسخ سرور JSON معتبر نیست.\n"
                        f"URL: {url}\n"
                        f"پاسخ: {raw[:1500]}"
                    )

        except urllib.error.HTTPError as error:
            try:
                body = error.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""

            raise Exception(
                f"HTTP Error {error.code}\n"
                f"URL: {url}\n"
                f"پاسخ: {body[:1500]}"
            )

        except urllib.error.URLError as error:
            raise Exception(
                f"خطای اتصال\n"
                f"URL: {url}\n"
                f"دلیل: {error.reason}"
            )

        except TimeoutError:
            raise Exception(
                f"Timeout؛ سرور در زمان تعیین‌شده پاسخ نداد.\n"
                f"URL: {url}"
            )

        except Exception as error:
            raise Exception(
                f"{type(error).__name__}: {error}\n"
                f"URL: {url}"
            )

    # -------------------------------------------------
    # استخراج نمادها
    # -------------------------------------------------

    def extract_list_from_response(self, response):
        """
        تلاش برای استخراج لیست از ساختارهای مختلف پاسخ API.
        """

        if isinstance(response, list):
            return response

        if not isinstance(response, dict):
            return []

        possible_keys = [
            "data",
            "list",
            "rows",
            "result",
            "instruments",
            "symbols",
            "markets",
            "items",
        ]

        for key in possible_keys:
            value = response.get(key)

            if isinstance(value, list):
                return value

            if isinstance(value, dict):
                nested = self.extract_list_from_response(value)
                if nested:
                    return nested

        return []

    def normalize_symbol(self, value):
        if value is None:
            return ""

        symbol = str(value).strip()

        if not symbol:
            return ""

        return symbol

    def get_symbol_from_item(self, item):
        if isinstance(item, str):
            return self.normalize_symbol(item)

        if not isinstance(item, dict):
            return ""

                   "symbol",
            "symbolName",
            "inst_id",
            "symbol",
            "symbolName",
            "instId",
            "inst_id",
            "market",
            "pair",
            "contract",
            "contractName",
        ]

        for key in possible_keys:
            value = item.get(key)
            if value:
                return self.normalize_symbol(value)

        return ""

    def is_usdt_symbol(self, symbol):
        normalized = (
            symbol.upper()
            .replace("/", "")
            .replace("-", "")
            .replace("_", "")
            .replace(":", "")
        )

        return normalized.endswith("USDT") or "USDT" in normalized

    def get_all_futures_symbols(self):
        """
        دریافت نمادهای بازار فیوچرز.
        پاسخ‌های مختلف بررسی می‌شوند تا در صورت تغییر ساختار API
        خطای واقعی نمایش داده شود.
        """

        urls = [
            "https://lbkperp.lbank.com/cfd/openApi/v1/pub/instrument",
            "https://lbkperp.lbank.com/cfd/openApi/v1/pub/marketData",
            "https://lbkperp.lbank.com/cfd/openApi/v1/pub/ticker",
        ]

        errors = []

        for url in urls:
            try:
                response = self.http_get_json(url)
                rows = self.extract_list_from_response(response)

                if not rows:
                    errors.append(
                        f"آدرس:\n{url}\n"
                        f"لیست داده پیدا نشد.\n"
                        f"پاسخ سرور:\n"
                        f"{json.dumps(response, ensure_ascii=False)[:1200]}"
                    )
                    continue

                symbols = []

                for item in rows:
                    symbol = self.get_symbol_from_item(item)

                    if symbol and self.is_usdt_symbol(symbol):
                        symbols.append(symbol)

                symbols = list(dict.fromkeys(symbols))

                if symbols:
                    return symbols

                errors.append(
                    f"آدرس:\n{url}\n"
                    f"داده دریافت شد اما نماد USDT استخراج نشد.\n"
                    f"نمونه پاسخ:\n"
                    f"{json.dumps(response, ensure_ascii=False)[:1200]}"
                )

            except Exception as error:
                errors.append(str(error))

        error_text = "\n\n--------------------\n\n".join(errors)

        raise Exception(
            "دریافت نمادهای فیوچرز ناموفق بود.\n\n"
            + error_text[: self.max_error_length]
        )

    # -------------------------------------------------
    # دریافت کندل‌ها
    # -------------------------------------------------

    def build_kline_urls(self, symbol):
        encoded_symbol = urllib.parse.quote(symbol, safe="")

        return [
            (
                "https://lbkperp.lbank.com/cfd/openApi/v1/pub/kline"
                f"?instrumentId={encoded_symbol}&period=1h&limit=24"
            ),
            (
                "https://lbkperp.lbank.com/cfd/openApi/v1/pub/kline"
                f"?symbol={encoded_symbol}&period=1h&limit=24"
            ),
        ]

    def fetch_ohlcv(self, symbol):
        now = time.time()
        cache_key = f"ohlcv_{symbol}"

        if (
            cache_key in self.cache
            and now - self.cache_time.get(cache_key, 0)
            < self.cache_duration
        ):
            return self.cache[cache_key]

        urls = self.build_kline_urls(symbol)
        errors = []

        for url in urls:
            try:
                response = self.http_get_json(url)
                rows = self.extract_list_from_response(response)

                if rows:
                    self.cache[cache_key] = rows
                    self.cache_time[cache_key] = now
                    return rows

                errors.append(
                    f"پاسخ کندل برای {symbol} خالی است:\n"
                    f"{json.dumps(response, ensure_ascii=False)[:700]}"
                )

            except Exception as error:
                errors.append(str(error))

        raise Exception(
            f"دریافت کندل برای {symbol} ناموفق بود.\n"
            + "\n".join(errors)[:1800]
        )

    # -------------------------------------------------
    # تبدیل و محاسبات
    # -------------------------------------------------

    def parse_kline(self, kline):
        """
        پشتیبانی از کندل‌های لیستی و دیکشنری.
        فرمت استاندارد:
        [timestamp, open, high, low, close, volume]
        """

        if isinstance(kline, dict):
            timestamp = (
                kline.get("timestamp")
                or kline.get("time")
                or kline.get("ts")
                or kline.get("id")
                or 0
            )

            open_price = (
                kline.get("open")
                or kline.get("openPrice")
                or kline.get("o")
                or 0
            )

            high_price = (
                kline.get("high")
                or kline.get("highPrice")
                or kline.get("h")
                or 0
            )

            low_price = (
                kline.get("low")
                or kline.get("lowPrice")
                or kline.get("l")
                or 0
            )

            close_price = (
                kline.get("close")
                or kline.get("closePrice")
                or kline.get("c")
                or 0
            )

            volume = (
                kline.get("volume")
                or kline.get("vol")
                or kline.get("baseVolume")
                or kline.get("v")
                or 0
            )

        elif isinstance(kline, (list, tuple)) and len(kline) >= 6:
            timestamp = kline[0]
            open_price = kline[1]
            high_price = kline[2]
            low_price = kline[3]
            close_price = kline[4]
            volume = kline[5]

        else:
            raise ValueError(f"فرمت کندل ناشناخته است: {kline}")

        timestamp = int(float(timestamp or 0))
        open_price = float(open_price)
        high_price = float(high_price)
        low_price = float(low_price)
        close_price = float(close_price)
        volume = float(volume or 0)

        if timestamp > 0 and timestamp < 100000000000:
            timestamp *= 1000

        return {
            "timestamp": timestamp,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": volume,
        }

    def calculate_price_change(self, ohlcv, minimum_change):
        if not ohlcv or len(ohlcv) < 20:
            return None

        candles = []

        for row in ohlcv:
            try:
                candle = self.parse_kline(row)

                if (
                    candle["open"] > 0
                    and candle["high"] > 0
                    and candle["low"] > 0
                    and candle["close"] > 0
                ):
                    candles.append(candle)

            except Exception:
                continue

        if len(candles) < 20:
            return None

        candles.sort(key=lambda x: x["timestamp"])

        first_candle = candles[0]
        last_candle = candles[-1]

        price_24h_ago = first_candle["open"]
        current_price = last_candle["close"]

        highs = [x["high"] for x in candles]
        lows = [x["low"] for x in candles]
        volumes = [x["volume"] for x in candles]

        high_24h = max(highs)
        low_24h = min(lows)

        if price_24h_ago <= 0 or low_24h <= 0:
            return None

        price_change = (
            (current_price - price_24h_ago) / price_24h_ago
        ) * 100

        volatility = ((high_24h - low_24h) / low_24h) * 100

        absolute_change = abs(price_change)

        if current_price > price_24h_ago:
            direction = "صعودی"
            emoji = "📈"
        elif current_price < price_24h_ago:
            direction = "نزولی"
            emoji = "📉"
        else:
            direction = "بدون تغییر"
            emoji = "➖"

        if absolute_change >= 100:
            intensity = "فوق‌العاده؛ بیشتر از ۱۰۰٪"
            rank = "🚀🚀🚀"
        elif absolute_change >= 75:
            intensity = "بسیار شدید؛ بین ۷۵ تا ۱۰۰٪"
            rank = "🚀🚀"
        elif absolute_change >= 50:
            intensity = "شدید؛ بین ۵۰ تا ۷۵٪"
            rank = "🚀"
        else:
            intensity = "تغییر معمولی"
            rank = "📊"

        average_volume = (
            sum current_volume = / len(volumes)
            if volumes
            else 0
        )

        current_volume = volumes[-1] if volumes else 0

        if average_volume > 0:
            volume_ratio = current_volume / average_volume
        else:
            volume_ratio = 0

        last_time = "نامشخص"

        if last_candle["timestamp"] > 0:
            try:
                last_time = datetime.fromtimestamp(
                    last_candle["timestamp"] / 1000
                ).strftime("%H:%M")
            except Exception:
                pass

        return {
            "price_change": round(price_change, 2),
            "volatility": round(volatility, 2),
            "direction": direction,
            "emoji": emoji,
            "intensity": intensity,
            "rank": rank,
            "price_24h_ago": price_24h_ago,
            "current_price": current_price,
            "high_24h": high_24h,
            "low_24h": low_24h,
            "volume_ratio": round(volume_ratio, 2),
            "last_time": last_time,
            "is_high_price_change": absolute_change >= minimum_change,
        }

    # -------------------------------------------------
    # اسکن
    # -------------------------------------------------

    def start_scan_thread(self, event):
        if self.is_scanning:
            return

        self.is_scanning = True
        self.scan_btn.disabled = True
        self.progress_bar.visible = True
        self.progress_bar.value = 0
        self.summary_text.visible = False
        self.cards_list.controls.clear()

        self.set_status("شروع اتصال به LBank...", ft.Colors.AMBER_300)

        thread = threading.Thread(
            target=self.run_scan,
            daemon=True,
        )
        thread.start()

    def run_scan(self):
        try:
            try:
                minimum_change = float(
                    (self.threshold_input.value or "1")
                    .replace(",", ".")
                    .strip()
                )
            except Exception:
                minimum_change = 1.0

            if minimum_change < 0:
                minimum_change = 0

            self.set_status(
                "در حال دریافت نمادهای فیوچرز از LBank...",
                ft.Colors.AMBER_300,
            )

            symbols = self.get_all_futures_symbols()

            if not symbols:
                raise Exception("لیست نمادها خالی دریافت شد.")

            total = len(symbols)

            self.set_status(
                f"{total} نماد پیدا شد؛ دریافت کندل‌ها آغاز شد...",
                ft.Colors.CYAN_300,
            )

            results = []
            first_symbol_error = None

            for index, symbol in enumerate(symbols):
                try:
                    candles = self.fetch_ohlcv(symbol)

                    result = self.calculate_price_change(
                        candles,
                        minimum_change,
                    )

                    if result and result["is_high_price_change"]:
                        result["symbol"] = symbol
                        results.append(result)

                except Exception as error:
                    if first_symbol_error is None:
                        first_symbol_error = f"{symbol}: {error}"

                self.progress_bar.value = (index + 1) / total

                if index == 0 or (index + 1) % 5 == 0 or index == total - 1:
                    self.status_text.value = (
                        f"بررسی {index + 1}/{total} | "
                        f"نتایج: {len(results)}"
                    )
                    self.page.update()

                time.sleep(0.08)

            results.sort(
                key=lambda item: abs(item["price_change"]),
                reverse=True,
            )

            self.cards_list.controls.clear()

            for result in results:
                self.add_card_to_ui(result)

            if results:
                self.summary_text.value = (
                    f"تعداد نتایج: {len(results)} | "
                    f"حداقل تغییر: {minimum_change}%"
                )
                self.summary_text.visible = True

                self.status_text.value = (
                    f"اسکن تمام شد؛ {len(results)} ارز پیدا شد."
                )
                self.status_text.color = ft.Colors.GREEN_300

            else:
                message = (
                    f"هیچ ارزی با تغییر حداقل "
                    f"{minimum_change}% پیدا نشد."
                )

                if first_symbol_error:
                    message += (
                        "\n\nنمونه خطای دریافت کندل:\n"
                        + first_symbol_error[:1800]
                    )

                self.status_text.value = message
                self.status_text.color = ft.Colors.ORANGE_300

            self.page.update()

        except Exception as error:
            error_text = (
                f"خطای واقعی برنامه:\n\n"
                f"{type(error).__name__}: {error}"
            )

            self.status_text.value = error_text[: self.max_error_length]
            self.status_text.color = ft.Colors.RED_300
            self.page.update()

        finally:
            self.progress_bar.visible = False
            self.scan_btn.disabled = False
            self.is_scanning = False
            self.page.update()

    # -------------------------------------------------
    # کارت نتیجه
    # -------------------------------------------------

    def format_price(self, value):
        try:
            value = float(value)

            if value >= 1000:
                return f"{value:,.2f}"
            if value >= 1:
                return f"{value:,.5f}"
            if value >= 0.0001:
                return f"{value:.8f}"

            return f"{value:.12f}"

        except Exception:
            return str(value)

    def add_card_to_ui(self, result):
        is_bullish = result["price_change"] >= 0

        if is_bullish:
            card_color = ft.Colors.GREEN_950
            border_color = ft.Colors.GREEN_500
            change_color = ft.Colors.GREEN_ACCENT
        else:
            card_color = ft.Colors.RED_950
            border_color = ft.Colors.RED_500
            change_color = ft.Colors.RED_ACCENT

        card = ft.Card(
            content=ft.Container(
                padding=12,
                bgcolor=card_color,
                border=ft.border.all(1, border_color),
                border_radius=10,
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(
                                    f'{result["rank"]} '
                                    f'{result["emoji"]} '
                                    f'{result["symbol"]}',
                                    size=15,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.WHITE,
                                    selectable=True,
                                ),
                                ft.Text(
                                    f'{result["price_change"]:+.2f}%',
                                    size=17,
                                    weight=ft.FontWeight.BOLD,
                                    color=change_color,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Text(
                            f'جهت: {result["direction"]} | '
                            f'شدت: {result["intensity"]}',
                            size=12,
                            color=ft.Colors.AMBER_200,
                        ),
                        ft.Divider(
                            height=2,
                            color=ft.Colors.WHITE24,
                        ),
                        ft.Row(
                            [
                                ft.Text(
                                    "قیمت فعلی: "
                                    + self.format_price(
                                        result["current_price"]
                                    ),
                                    size=12,
                                    color=ft.Colors.WHITE70,
                                ),
                                ft.Text(
                                    "۲۴ ساعت پیش: "
                                    + self.format_price(
                                        result["price_24h_ago"]
                                    ),
                                    size=12,
                                    color=ft.Colors.WHITE70,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Row(
                            [
                                ft.Text(
                                    f'دامنه نوسان: '
                                    f'{result["volatility"]:.2f}%',
                                    size=12,
                                    color=ft.Colors.WHITE70,
                                ),
                                ft.Text(
                                    f'حجم: '
                                    f'{result["volume_ratio"]:.2f}x میانگین',
                                    size=12,
                                    color=ft.Colors.CYAN_200,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Text(
                            f'بیشترین قیمت: '
                            f'{self.format_price(result["high_24h"])} | '
                            f'کمترین قیمت: '
                            f'{self.format_price(result["low_24h"])} | '
                            f'زمان: {result["last_time"]}',
                            size=11,
                            color=ft.Colors.WHITE60,
                            selectable=True,
                        ),
                    ],
                    spacing=5,
                ),
            )
        )

        self.cards_list.controls.append(card)


def main(page: ft.Page):
    PriceChangeHunterApp(page)


if __name__ == "__main__":
    ft.app(target=main)
