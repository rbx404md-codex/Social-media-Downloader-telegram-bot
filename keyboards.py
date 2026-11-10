from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


# ---------- USER SIDE ----------
def main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Persistent bottom menu — always visible."""
    kb = ReplyKeyboardBuilder()
    kb.button(text="🏠 Home")
    kb.button(text="📜 My History")
    kb.button(text="💎 Premium")
    kb.button(text="🌐 Language")
    kb.button(text="❓ Help")
    kb.adjust(3, 2)
    return kb.as_markup(resize_keyboard=True)


def start_inline_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📥 How to Download", callback_data="how_to")
    kb.button(text="📊 My Stats", callback_data="my_stats")
    kb.button(text="💎 Go Premium", callback_data="premium_info")
    kb.button(text="⚙️ Settings", callback_data="user_settings")
    kb.button(text="📢 Updates Channel", url="https://t.me/your_channel")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def force_join_keyboard(channels) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for ch in channels:
        kb.button(text=f"📢 Join {ch['title']}", url=ch["invite_link"])
    kb.button(text="✅ I've Joined", callback_data="verify_join")
    kb.adjust(1)
    return kb.as_markup()


def quality_selection_keyboard(result_id: str, formats: list) -> InlineKeyboardMarkup:
    """
    formats: list of dicts like {"label": "720p", "format_id": "22"}
    result_id: short id referencing cached link info (avoids huge callback_data)
    """
    kb = InlineKeyboardBuilder()
    for f in formats:
        kb.button(text=f"🎬 {f['label']}", callback_data=f"dl:{result_id}:{f['format_id']}")
    kb.button(text="🎵 Audio Only (MP3)", callback_data=f"dl:{result_id}:audio")
    kb.adjust(2)
    return kb.as_markup()


def after_download_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Try Another Link", callback_data="try_again")
    kb.button(text="❤️ Save to Favorites", callback_data="save_fav")
    kb.button(text="📤 Share Bot", switch_inline_query="Check out this bot!")
    kb.adjust(2, 1)
    return kb.as_markup()


def progress_bar(percent: int) -> str:
    filled = int(percent / 10)
    bar = "█" * filled + "░" * (10 - filled)
    return f"[{bar}] {percent}%"


# ---------- ADMIN SIDE ----------
def admin_main_panel() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Statistics", callback_data="adm_stats")
    kb.button(text="👥 User Management", callback_data="adm_users")
    kb.button(text="⚙️ Bot Settings", callback_data="adm_settings")
    kb.button(text="📢 Force Join Channels", callback_data="adm_forcejoin")
    kb.button(text="📩 Broadcast", callback_data="adm_broadcast")
    kb.button(text="🚦 Maintenance Mode", callback_data="adm_maintenance")
    kb.adjust(2, 2, 2)
    return kb.as_markup()


def admin_back_button(target: str = "adm_home") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Back", callback_data=target)
    return kb.as_markup()


def admin_settings_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Edit Welcome Text", callback_data="adm_edit_welcome_text")
    kb.button(text="🖼️ Edit Welcome Image", callback_data="adm_edit_welcome_img")
    kb.button(text="🎚️ Set Daily Free Limit", callback_data="adm_edit_limit")
    kb.button(text="⬅️ Back", callback_data="adm_home")
    kb.adjust(1, 1, 1, 1)
    return kb.as_markup()


def admin_users_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🚫 Ban User", callback_data="adm_ban_user")
    kb.button(text="✅ Unban User", callback_data="adm_unban_user")
    kb.button(text="💎 Grant Premium", callback_data="adm_grant_premium")
    kb.button(text="❌ Remove Premium", callback_data="adm_remove_premium")
    kb.button(text="⬅️ Back", callback_data="adm_home")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def admin_forcejoin_menu(channels) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for ch in channels:
        kb.button(text=f"❌ Remove {ch['title']}", callback_data=f"adm_rm_ch:{ch['chat_id']}")
    kb.button(text="➕ Add Channel", callback_data="adm_add_ch")
    kb.button(text="⬅️ Back", callback_data="adm_home")
    kb.adjust(1)
    return kb.as_markup()


def confirm_broadcast_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Confirm Send", callback_data="adm_broadcast_confirm")
    kb.button(text="❌ Cancel", callback_data="adm_home")
    kb.adjust(2)
    return kb.as_markup()


def maintenance_toggle_keyboard(current_state: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    label = "🔴 Turn OFF Maintenance" if current_state else "🟢 Turn ON Maintenance"
    kb.button(text=label, callback_data="adm_toggle_maintenance")
    kb.button(text="⬅️ Back", callback_data="adm_home")
    kb.adjust(1)
    return kb.as_markup()
