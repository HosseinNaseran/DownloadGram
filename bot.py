import asyncio
import os
import logging
import gc
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from dotenv import load_dotenv
import yt_dlp
from aiohttp import web

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("توکن ربات در فایل .env پیدا نشد!")

CHANNEL_USERNAME = "@hossein_codes"  

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---------- دکمه عضویت ----------
def get_subscription_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔰 عضویت در کانال",
                    url="https://t.me/hossein_codes"
                )
            ]
        ]
    )
    return keyboard

# ---------- بررسی عضویت ----------
async def is_user_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["member", "creator", "administrator", "restricted"]:
            return True
        return False
    except Exception as e:
        logging.error(f"خطا در بررسی عضویت: {e}")
        return False

# ---------- دریافت لینک مستقیم (پشتیبانی از یوتیوب، اینستا، تیک‌تاک و ...) ----------
async def get_media_url(url: str):
    # تنظیمات فوق‌سبک برای yt-dlp
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist',  # استخراج حداقل اطلاعات
        'format': 'best[height<=720][ext=mp4]/best[height<=720]',  # اولویت با mp4 و کیفیت 720p
        'noplaylist': True,  # فقط خود ویدیو، نه لیست پخش
        'no_check_certificate': True,
        'prefer_ffmpeg': False,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
    }
    try:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # استخراج اطلاعات بدون دانلود
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            
            # اگر لینک مستقیم وجود داشت
            if info and info.get('url'):
                return [info['url']]
            
            # اگر فرمت‌های مختلف وجود داشت، بهترین را انتخاب کن
            if info and info.get('formats'):
                # اولویت با کیفیت 720p و فرمت mp4
                best = None
                for f in info['formats']:
                    height = f.get('height') or 0
                    ext = f.get('ext')
                    if height <= 720 and ext == 'mp4':
                        if best is None or height > best.get('height', 0):
                            best = f
                # اگر mp4 با کیفیت پایین پیدا نشد، هر فرمت دیگری را بگیر
                if not best:
                    best = max(info['formats'], key=lambda f: (f.get('height') or 0, -f.get('filesize', 0) or 0))
                if best and best.get('url'):
                    return [best['url']]
            
            # اگر لیستی از ویدیوها بود (مثل پلی‌لیست)
            if info and 'entries' in info:
                urls = []
                for entry in info['entries']:
                    if entry and entry.get('url'):
                        urls.append(entry['url'])
                return urls if urls else None
            
            # هیچ لینکی پیدا نشد
            return None
    except Exception as e:
        logging.error(f"خطا در دریافت لینک: {e}")
        # لاگ کامل خطا برای دیباگ
        logging.exception(e)
        return None

# ---------- ارسال فایل ----------
async def send_media_to_user(message: Message, url: str):
    try:
        await message.answer_video(url, supports_streaming=True)
    except Exception:
        try:
            await message.answer_photo(url)
        except Exception as e:
            logging.error(f"خطا در ارسال فایل: {e}")
            await message.answer("❌ خطا در ارسال فایل. شاید حجم آن بیشتر از ۵۰ مگابایت باشد.")
    finally:
        gc.collect()

# ---------- دستور /start ----------
@dp.message(Command("start"))
async def start_command(message: Message):
    user_id = message.from_user.id
    if not await is_user_subscribed(user_id):
        await message.answer(
            "❌ برای استفاده از این ربات، ابتدا در کانال زیر عضو شوید:\n\n"
            f"📢 @hossein_codes\n\n"
            "✅ پس از عضویت، دوباره /start را بزنید.",
            reply_markup=get_subscription_keyboard()
        )
        return
    await message.answer("سلام! 👋 لینک یک پست، ریلز، ویدیو یا استوری از اینستاگرام، یوتیوب، تیک‌تاک یا توئیتر را برای من بفرستید تا آن را برایتان دانلود کنم.")

# ---------- دستور /help ----------
@dp.message(Command("help"))
async def help_command(message: Message):
    user_id = message.from_user.id
    if not await is_user_subscribed(user_id):
        await message.answer(
            "❌ برای استفاده از این ربات، ابتدا در کانال زیر عضو شوید:\n\n"
            f"📢 @hossein_codes\n\n"
            "✅ پس از عضویت، دوباره /help را بزنید.",
            reply_markup=get_subscription_keyboard()
        )
        return
    await message.answer(
        "👇 چطور کار می‌کند؟\n"
        "1. لینک پست را از اینستاگرام، یوتیوب، تیک‌تاک یا توئیتر کپی کنید.\n"
        "2. لینک را در همین چت برای من ارسال کنید.\n"
        "3. من فایل(های) آن را برای شما ارسال می‌کنم."
    )

# ---------- دریافت پیام‌ها ----------
@dp.message()
async def handle_download_link(message: Message):
    user_id = message.from_user.id
    if not await is_user_subscribed(user_id):
        await message.answer(
            "❌ برای استفاده از این ربات، ابتدا در کانال زیر عضو شوید:\n\n"
            f"📢 @hossein_codes\n\n"
            "✅ پس از عضویت، دوباره لینک را ارسال کنید.",
            reply_markup=get_subscription_keyboard()
        )
        return

    supported_sites = ["instagram.com", "youtube.com", "youtu.be", "tiktok.com", "twitter.com", "x.com"]
    
    if not any(site in message.text for site in supported_sites):
        await message.answer(
            "❌ لطفاً یک لینک معتبر از سایت‌های زیر ارسال کنید:\n"
            "• اینستاگرام (instagram.com)\n"
            "• یوتیوب (youtube.com)\n"
            "• تیک‌تاک (tiktok.com)\n"
            "• توئیتر (twitter.com / x.com)"
        )
        return

    processing_msg = await message.answer("⏳ در حال دریافت اطلاعات از لینک...")
    media_urls = await get_media_url(message.text)

    if not media_urls:
        await processing_msg.edit_text("❌ خطا: امکان دانلود این محتوا وجود ندارد. لطفاً از لینک معتبر استفاده کنید.")
        return

    if len(media_urls) > 1:
        await processing_msg.edit_text(f"📸 تعداد {len(media_urls)} رسانه در این پست پیدا شد. در حال ارسال...")
        for url in media_urls:
            await send_media_to_user(message, url)
        await message.answer("✅ تمام فایل‌ها ارسال شدند.")
    else:
        await processing_msg.edit_text("📥 در حال دانلود و ارسال...")
        await send_media_to_user(message, media_urls[0])
        await message.answer("✅ دانلود و ارسال با موفقیت انجام شد.")

# ---------- راه‌اندازی وب‌سرور برای Render ----------
async def health(request):
    return web.Response(text="Bot is running!")

async def start_bot():
    asyncio.create_task(dp.start_polling(bot))
    app = web.Application()
    app.router.add_get('/health', health)
    app.router.add_get('/', health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
    await site.start()
    logging.info("Web server and bot are running.")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(start_bot())