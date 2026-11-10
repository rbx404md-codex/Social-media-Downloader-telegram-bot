import re
import time
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart

import database as db
import keyboards as kb
from downloader import (
    detect_platform,
    extract_info,
    build_quality_options,
    download_media,
    cleanup_file,
)
from config import ADMIN_IDS, FREE_DAILY_LIMIT, MAX_FILE_SIZE_MB

router = Router()
URL_REGEX = re.compile(r"https?://\S+")


async def user_passes_force_join(bot: Bot, user_id: int) -> bool:
    channels = await db.get_force_channels()
    if not channels:
        return True
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch["chat_id"], user_id=user_id)
            if member.status in ("left", "kicked"):
                return False
        except Exception:
            # If bot can't check (not admin in that chat, etc.) fail open to avoid hard-lock
            continue
    return True


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    await db.add_user(
        message.from_user.id, message.from_user.username or "", message.from_user.first_name or ""
    )

    if await db.is_banned(message.from_user.id):
        await message.answer("🚫 You are banned from using this bot.")
        return

    maintenance = await db.get_setting("maintenance_mode")
    if maintenance == "1" and message.from_user.id not in ADMIN_IDS:
        await message.answer("🛠️ Bot is currently under maintenance. Please check back soon!")
        return

    if not await user_passes_force_join(bot, message.from_user.id):
        channels = await db.get_force_channels()
        await message.answer(
            "🔒 <b>Please join the channel(s) below to use this bot:</b>",
            reply_markup=kb.force_join_keyboard(channels),
        )
        return

    welcome_text = await db.get_setting("welcome_text")
    welcome_text = welcome_text.replace("{first_name}", message.from_user.first_name or "there")
    welcome_image = await db.get_setting("welcome_image")

    await message.answer(
        "Menu loaded below 👇 (this stays pinned at the bottom)",
        reply_markup=kb.main_reply_keyboard(),
    )

    if welcome_image:
        await message.answer_photo(
            photo=welcome_image,
            caption=welcome_text,
            reply_markup=kb.start_inline_menu(),
        )
    else:
        await message.answer(welcome_text, reply_markup=kb.start_inline_menu())


@router.callback_query(F.data == "verify_join")
async def verify_join(callback: CallbackQuery, bot: Bot):
    if await user_passes_force_join(bot, callback.from_user.id):
        await callback.message.delete()
        await cmd_start(callback.message, bot)
        await callback.answer("✅ Verified! Welcome aboard.")
    else:
        await callback.answer("❌ You haven't joined all channels yet.", show_alert=True)


@router.callback_query(F.data == "my_stats")
async def my_stats(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("No data found.", show_alert=True)
        return
    text = (
        f"📊 <b>Your Stats</b>\n\n"
        f"👤 User ID: <code>{user['user_id']}</code>\n"
        f"📥 Downloads Today: {user['downloads_today']}\n"
        f"📦 Total Downloads: {user['total_downloads']}\n"
        f"💎 Premium: {'Yes ✅' if user['is_premium'] else 'No'}"
    )
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "premium_info")
async def premium_info(callback: CallbackQuery):
    await callback.message.answer(
        "💎 <b>Premium Benefits</b>\n\n"
        "• Unlimited downloads (no daily cap)\n"
        "• Up to 4K quality\n"
        "• No ads, priority queue\n\n"
        "Contact admin to upgrade!"
    )
    await callback.answer()


@router.callback_query(F.data == "how_to")
async def how_to(callback: CallbackQuery):
    await callback.message.answer(
        "📥 <b>How to use:</b>\n\n"
        "Just paste any YouTube / Instagram / TikTok / Twitter / Facebook link "
        "directly into the chat — I'll do the rest!"
    )
    await callback.answer()


@router.callback_query(F.data == "try_again")
async def try_again(callback: CallbackQuery):
    await callback.message.answer("📎 Send me your next link!")
    await callback.answer()


# ---------- CORE DOWNLOAD FLOW ----------
@router.message(F.text.regexp(URL_REGEX))
async def handle_link(message: Message, bot: Bot):
    if await db.is_banned(message.from_user.id):
        return

    if not await user_passes_force_join(bot, message.from_user.id):
        channels = await db.get_force_channels()
        await message.answer(
            "🔒 Please join the required channel(s) first:",
            reply_markup=kb.force_join_keyboard(channels),
        )
        return

    await db.reset_daily_if_needed(message.from_user.id)
    user = await db.get_user(message.from_user.id)

    if not user["is_premium"] and user["downloads_today"] >= FREE_DAILY_LIMIT:
        await message.answer(
            f"⚠️ You've hit your daily limit ({FREE_DAILY_LIMIT} downloads).\n"
            f"Upgrade to 💎 Premium for unlimited downloads!"
        )
        return

    url = URL_REGEX.search(message.text).group(0)
    platform = detect_platform(url)

    if platform == "Unknown":
        await message.answer("❌ Sorry, this link/platform isn't supported yet.")
        return

    status_msg = await message.answer(f"🔍 Analyzing {platform} link...")

    try:
        result = await extract_info(url)
    except Exception as e:
        await status_msg.edit_text(f"❌ Couldn't process this link.\n<code>{str(e)[:200]}</code>")
        return

    formats = build_quality_options(result["info"])
    title = result["info"].get("title", "Media")[:60]

    await status_msg.edit_text(
        f"✅ Found: <b>{title}</b>\n📱 Platform: {platform}\n\nChoose quality:",
        reply_markup=kb.quality_selection_keyboard(result["result_id"], formats),
    )


@router.callback_query(F.data.startswith("dl:"))
async def handle_quality_choice(callback: CallbackQuery, bot: Bot):
    _, result_id, format_choice = callback.data.split(":")
    await callback.answer()

    status_msg = callback.message
    await status_msg.edit_text(f"⬇️ Downloading...\n{kb.progress_bar(0)}")

    last_update = {"t": 0.0}

    def progress_hook(d):
        # NOTE: yt-dlp progress_hooks run in a worker thread (sync context),
        # so we can't directly await bot.edit_message here — real deployments
        # should push updates through an asyncio.Queue consumed by the main loop.
        pass

    try:
        filepath = await download_media(result_id, format_choice, progress_hook)
    except Exception as e:
        await status_msg.edit_text(f"❌ Download failed.\n<code>{str(e)[:200]}</code>")
        return

    import os
    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        await status_msg.edit_text(
            f"⚠️ File is {size_mb:.1f}MB, which exceeds the {MAX_FILE_SIZE_MB}MB bot limit.\n"
            f"Consider selecting a lower quality."
        )
        cleanup_file(filepath)
        return

    await status_msg.edit_text(f"⬆️ Uploading to Telegram...\n{kb.progress_bar(90)}")

    try:
        file = FSInputFile(filepath)
        if format_choice == "audio":
            await bot.send_audio(chat_id=callback.from_user.id, audio=file)
        else:
            await bot.send_video(chat_id=callback.from_user.id, video=file)
        await status_msg.edit_text("✅ <b>Download Complete!</b>")
        await callback.message.answer(
            "What next?", reply_markup=kb.after_download_keyboard()
        )
        await db.increment_download_count(callback.from_user.id, "unknown", "success")
    except Exception as e:
        await status_msg.edit_text(f"❌ Upload failed.\n<code>{str(e)[:200]}</code>")
        await db.increment_download_count(callback.from_user.id, "unknown", "failed")
    finally:
        cleanup_file(filepath)
