import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from dotenv import load_dotenv
import yt_dlp

# بارگذاری متغیرهای محیطی
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("توکن ربات در فایل .env پیدا نشد!")

# شناسه کانال (با @ یا بدون آن)
CHANNEL_USERNAME = "hossein_codes"  # یا "hossein_codes"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---------- دکمه عضویت ----------
def get_subscription_keyboard():
    """ساخت دکمه با لینک دعوت به کانال"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔰 عضویت در کانال",
                    url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"  # لینک مستقیم کانال
                )
            ]
        ]
    )
    return keyboard

# ---------- تابع بررسی عضویت ----------
async def is_user_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["member", "creator", "administrator", "restricted"]:
            return True
        return False
    except Exception as e:
        logging.error(f"خطا در بررسی عضویت: {e}")
        return False

# ---------- تابع دانلود ----------
async def get_instagram_media_url(url: str):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    try:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            if 'entries' in info:
                urls = [entry['url'] for entry in info['entries'] if entry.get('url')]
                return urls
            elif info.get('url'):
                return [info['url']]
            else:
                return None
    except Exception as e:
        logging.error(f"خطا در دانلود: {e}")
        return None

# ---------- ارسال فایل به کاربر ----------
async def send_media_to_user(message: Message, url: str):
    try:
        await message.answer_video(url, supports_streaming=True)
    except Exception:
        try:
            await message.answer_photo(url)
        except Exception as e:
            logging.error(f"خطا در ارسال فایل: {e}")
            await message.answer("❌ خطا در ارسال فایل. شاید حجم آن بیشتر از ۵۰ مگابایت باشد.")

# ---------- دستور /start ----------
@dp.message(Command("start"))
async def start_command(message: Message):
    user_id = message.from_user.id
    if not await is_user_subscribed(user_id):
        await message.answer(
            "❌ برای استفاده از این ربات، ابتدا در کانال زیر عضو شوید:\n\n"
            f"📢 {CHANNEL_USERNAME}\n\n"
            "✅ پس از عضویت، دوباره /start را بزنید.",
            reply_markup=get_subscription_keyboard()  # نمایش دکمه
        )
        return
    await message.answer("سلام! 👋 لینک یک پست، ریلز یا استوری از اینستاگرام را برای من بفرستید تا آن را برایتان دانلود کنم.")

# ---------- دستور /help ----------
@dp.message(Command("help"))
async def help_command(message: Message):
    user_id = message.from_user.id
    if not await is_user_subscribed(user_id):
        await message.answer(
            "❌ برای استفاده از این ربات، ابتدا در کانال زیر عضو شوید:\n\n"
            f"📢 {CHANNEL_USERNAME}\n\n"
            "✅ پس از عضویت، دوباره /help را بزنید.",
            reply_markup=get_subscription_keyboard()
        )
        return
    await message.answer(
        "👇 چطور کار می‌کند؟\n"
        "1. لینک پست را از اینستاگرام کپی کنید.\n"
        "2. لینک را در همین چت برای من ارسال کنید.\n"
        "3. من فایل(های) آن را برای شما ارسال می‌کنم."
    )

# ---------- دریافت پیام‌های معمولی ----------
@dp.message()
async def handle_instagram_link(message: Message):
    user_id = message.from_user.id
    if not await is_user_subscribed(user_id):
        await message.answer(
            "❌ برای استفاده از این ربات، ابتدا در کانال زیر عضو شوید:\n\n"
            f"📢 {CHANNEL_USERNAME}\n\n"
            "✅ پس از عضویت، دوباره لینک را ارسال کنید.",
            reply_markup=get_subscription_keyboard()
        )
        return

    if "instagram.com" in message.text:
        processing_msg = await message.answer("⏳ در حال دریافت اطلاعات از اینستاگرام...")
        media_urls = await get_instagram_media_url(message.text)

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
    else:
        await message.answer("لطفاً یک لینک معتبر از اینستاگرام ارسال کنید.")
        
# ---------- راه‌اندازی وب‌سرور برای Render ----------
from aiohttp import web

async def health(request):
    return web.Response(text="ربات در حال اجراست!")

async def start_bot():
    # اجرای ربات تلگرام
    asyncio.create_task(dp.start_polling(bot))
    
    # راه‌اندازی یک وب‌سرور ساده برای Render
    app = web.Application()
    app.router.add_get('/health', health)  # برای بررسی سلامت
    app.router.add_get('/', health)        # صفحه اصلی
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
    await site.start()
    
    logging.info("وب‌سرور و ربات با موفقیت اجرا شدند.")
    # تا ابد منتظر می‌ماند
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(start_bot())