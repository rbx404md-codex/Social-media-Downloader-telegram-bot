import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from states import AdminStates
from config import ADMIN_IDS

router = Router()


def admin_only(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ---------- ENTRY ----------
@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not admin_only(message.from_user.id):
        await message.answer("⛔ You don't have access to this command.")
        return
    await message.answer(
        "🛠️ <b>Admin Control Panel</b>\n\nSelect an option below:",
        reply_markup=kb.admin_main_panel(),
    )


@router.callback_query(F.data == "adm_home")
async def admin_home(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🛠️ <b>Admin Control Panel</b>\n\nSelect an option below:",
        reply_markup=kb.admin_main_panel(),
    )
    await callback.answer()


# ---------- STATISTICS ----------
@router.callback_query(F.data == "adm_stats")
async def admin_stats(callback: CallbackQuery):
    if not admin_only(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return
    stats = await db.get_stats()
    text = (
        "📊 <b>Bot Statistics</b>\n\n"
        f"👥 Total Users: {stats['total_users']}\n"
        f"🆕 New Today: {stats['today_users']}\n"
        f"📥 Total Downloads: {stats['total_downloads']}\n"
        f"💎 Premium Users: {stats['premium_users']}\n"
        f"🚫 Banned Users: {stats['banned_users']}"
    )
    await callback.message.edit_text(text, reply_markup=kb.admin_back_button())
    await callback.answer()


# ---------- SETTINGS MENU ----------
@router.callback_query(F.data == "adm_settings")
async def admin_settings(callback: CallbackQuery):
    if not admin_only(callback.from_user.id):
        return
    await callback.message.edit_text(
        "⚙️ <b>Bot Settings</b>\n\nWhat would you like to edit?",
        reply_markup=kb.admin_settings_menu(),
    )
    await callback.answer()


@router.callback_query(F.data == "adm_edit_welcome_text")
async def edit_welcome_text_start(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback.from_user.id):
        return
    current = await db.get_setting("welcome_text")
    await callback.message.edit_text(
        f"✏️ <b>Current welcome text:</b>\n\n{current}\n\n"
        f"Send me the new welcome message text now.\n"
        f"(You can use <code>{{first_name}}</code> as a placeholder)",
        reply_markup=kb.admin_back_button("adm_settings"),
    )
    await state.set_state(AdminStates.waiting_welcome_text)
    await callback.answer()


@router.message(AdminStates.waiting_welcome_text)
async def edit_welcome_text_save(message: Message, state: FSMContext):
    if not admin_only(message.from_user.id):
        return
    await db.set_setting("welcome_text", message.html_text)
    await state.clear()
    await message.answer("✅ Welcome text updated!", reply_markup=kb.admin_back_button())


@router.callback_query(F.data == "adm_edit_welcome_img")
async def edit_welcome_img_start(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback.from_user.id):
        return
    await callback.message.edit_text(
        "🖼️ Send me the new welcome image (just send the photo).\n"
        "Send /clear to remove the current image instead.",
        reply_markup=kb.admin_back_button("adm_settings"),
    )
    await state.set_state(AdminStates.waiting_welcome_image)
    await callback.answer()


@router.message(AdminStates.waiting_welcome_image, F.photo)
async def edit_welcome_img_save(message: Message, state: FSMContext):
    if not admin_only(message.from_user.id):
        return
    file_id = message.photo[-1].file_id
    await db.set_setting("welcome_image", file_id)
    await state.clear()
    await message.answer("✅ Welcome image updated!", reply_markup=kb.admin_back_button())


@router.message(AdminStates.waiting_welcome_image, Command("clear"))
async def clear_welcome_img(message: Message, state: FSMContext):
    if not admin_only(message.from_user.id):
        return
    await db.set_setting("welcome_image", "")
    await state.clear()
    await message.answer("✅ Welcome image removed.", reply_markup=kb.admin_back_button())


@router.callback_query(F.data == "adm_edit_limit")
async def edit_limit_start(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback.from_user.id):
        return
    await callback.message.edit_text(
        "🎚️ Send the new daily free-download limit (number only).\n"
        "Note: this updates in-memory config only in this template — "
        "wire it to the settings table for persistence in production.",
        reply_markup=kb.admin_back_button("adm_settings"),
    )
    await state.set_state(AdminStates.waiting_daily_limit)
    await callback.answer()


@router.message(AdminStates.waiting_daily_limit)
async def edit_limit_save(message: Message, state: FSMContext):
    if not admin_only(message.from_user.id):
        return
    if not message.text.isdigit():
        await message.answer("❌ Please send a valid number.")
        return
    await db.set_setting("free_daily_limit", message.text)
    await state.clear()
    await message.answer(
        f"✅ Daily limit updated to {message.text}.", reply_markup=kb.admin_back_button()
    )


# ---------- USER MANAGEMENT ----------
@router.callback_query(F.data == "adm_users")
async def admin_users(callback: CallbackQuery):
    if not admin_only(callback.from_user.id):
        return
    await callback.message.edit_text(
        "👥 <b>User Management</b>", reply_markup=kb.admin_users_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "adm_ban_user")
async def ban_user_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🚫 Send the user ID to ban.", reply_markup=kb.admin_back_button("adm_users")
    )
    await state.update_data(action="ban")
    await state.set_state(AdminStates.waiting_user_id_for_ban)
    await callback.answer()


@router.callback_query(F.data == "adm_unban_user")
async def unban_user_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "✅ Send the user ID to unban.", reply_markup=kb.admin_back_button("adm_users")
    )
    await state.update_data(action="unban")
    await state.set_state(AdminStates.waiting_user_id_for_ban)
    await callback.answer()


@router.message(AdminStates.waiting_user_id_for_ban)
async def ban_user_save(message: Message, state: FSMContext):
    if not admin_only(message.from_user.id):
        return
    if not message.text.isdigit():
        await message.answer("❌ Send a valid numeric user ID.")
        return
    data = await state.get_data()
    target_id = int(message.text)
    should_ban = data.get("action") == "ban"
    await db.set_ban(target_id, should_ban)
    await state.clear()
    verb = "banned 🚫" if should_ban else "unbanned ✅"
    await message.answer(f"User {target_id} has been {verb}.", reply_markup=kb.admin_back_button())


@router.callback_query(F.data == "adm_grant_premium")
async def grant_premium_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "💎 Send the user ID to grant Premium.",
        reply_markup=kb.admin_back_button("adm_users"),
    )
    await state.update_data(action="grant")
    await state.set_state(AdminStates.waiting_user_id_for_premium)
    await callback.answer()


@router.callback_query(F.data == "adm_remove_premium")
async def remove_premium_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "❌ Send the user ID to remove Premium from.",
        reply_markup=kb.admin_back_button("adm_users"),
    )
    await state.update_data(action="remove")
    await state.set_state(AdminStates.waiting_user_id_for_premium)
    await callback.answer()


@router.message(AdminStates.waiting_user_id_for_premium)
async def premium_save(message: Message, state: FSMContext):
    if not admin_only(message.from_user.id):
        return
    if not message.text.isdigit():
        await message.answer("❌ Send a valid numeric user ID.")
        return
    data = await state.get_data()
    target_id = int(message.text)
    grant = data.get("action") == "grant"
    await db.set_premium(target_id, grant)
    await state.clear()
    verb = "granted 💎" if grant else "removed ❌"
    await message.answer(
        f"Premium {verb} for user {target_id}.", reply_markup=kb.admin_back_button()
    )


# ---------- FORCE JOIN CHANNELS ----------
@router.callback_query(F.data == "adm_forcejoin")
async def admin_forcejoin(callback: CallbackQuery):
    if not admin_only(callback.from_user.id):
        return
    channels = await db.get_force_channels()
    await callback.message.edit_text(
        "📢 <b>Force Join Channels</b>\n\n"
        "Bot must be admin in these channels to verify membership.",
        reply_markup=kb.admin_forcejoin_menu(channels),
    )
    await callback.answer()


@router.callback_query(F.data == "adm_add_ch")
async def add_channel_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "➕ Send channel info in this format:\n\n"
        "<code>chat_id|Title|https://t.me/invitelink</code>\n\n"
        "Example:\n<code>-1001234567890|My Channel|https://t.me/mychannel</code>",
        reply_markup=kb.admin_back_button("adm_forcejoin"),
    )
    await state.set_state(AdminStates.waiting_channel_id)
    await callback.answer()


@router.message(AdminStates.waiting_channel_id)
async def add_channel_save(message: Message, state: FSMContext):
    if not admin_only(message.from_user.id):
        return
    try:
        chat_id, title, link = message.text.split("|")
        await db.add_force_channel(chat_id.strip(), title.strip(), link.strip())
        await state.clear()
        await message.answer("✅ Channel added!", reply_markup=kb.admin_back_button())
    except ValueError:
        await message.answer("❌ Invalid format. Use: chat_id|Title|invite_link")


@router.callback_query(F.data.startswith("adm_rm_ch:"))
async def remove_channel(callback: CallbackQuery):
    if not admin_only(callback.from_user.id):
        return
    chat_id = callback.data.split(":", 1)[1]
    await db.remove_force_channel(chat_id)
    channels = await db.get_force_channels()
    await callback.message.edit_text(
        "📢 <b>Force Join Channels</b>\n\nChannel removed.",
        reply_markup=kb.admin_forcejoin_menu(channels),
    )
    await callback.answer("✅ Removed")


# ---------- BROADCAST ----------
@router.callback_query(F.data == "adm_broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback.from_user.id):
        return
    await callback.message.edit_text(
        "📩 Send the message you want to broadcast to all users.\n"
        "(Text, photo, or video with caption — all supported)",
        reply_markup=kb.admin_back_button(),
    )
    await state.set_state(AdminStates.waiting_broadcast_message)
    await callback.answer()


@router.message(AdminStates.waiting_broadcast_message)
async def broadcast_preview(message: Message, state: FSMContext):
    if not admin_only(message.from_user.id):
        return
    await state.update_data(broadcast_msg_id=message.message_id, broadcast_chat_id=message.chat.id)
    await message.answer(
        "👆 This is a preview of your broadcast. Send it to all users?",
        reply_markup=kb.confirm_broadcast_keyboard(),
    )


@router.callback_query(F.data == "adm_broadcast_confirm")
async def broadcast_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not admin_only(callback.from_user.id):
        return
    data = await state.get_data()
    msg_id = data.get("broadcast_msg_id")
    chat_id = data.get("broadcast_chat_id")
    await state.clear()

    if not msg_id:
        await callback.answer("⚠️ Nothing to broadcast.", show_alert=True)
        return

    user_ids = await db.get_all_user_ids()
    await callback.message.edit_text(f"📤 Broadcasting to {len(user_ids)} users...")

    sent, failed = 0, 0
    for uid in user_ids:
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=chat_id, message_id=msg_id)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)  # basic flood-control spacing

    await callback.message.edit_text(
        f"✅ Broadcast complete!\n📤 Sent: {sent}\n❌ Failed: {failed}",
        reply_markup=kb.admin_back_button(),
    )


# ---------- MAINTENANCE MODE ----------
@router.callback_query(F.data == "adm_maintenance")
async def maintenance_menu(callback: CallbackQuery):
    if not admin_only(callback.from_user.id):
        return
    current = await db.get_setting("maintenance_mode") == "1"
    status = "🟢 ON" if current else "🔴 OFF"
    await callback.message.edit_text(
        f"🚦 <b>Maintenance Mode</b>\n\nCurrent status: {status}",
        reply_markup=kb.maintenance_toggle_keyboard(current),
    )
    await callback.answer()


@router.callback_query(F.data == "adm_toggle_maintenance")
async def toggle_maintenance(callback: CallbackQuery):
    if not admin_only(callback.from_user.id):
        return
    current = await db.get_setting("maintenance_mode") == "1"
    new_value = "0" if current else "1"
    await db.set_setting("maintenance_mode", new_value)
    status = "🟢 ON" if new_value == "1" else "🔴 OFF"
    await callback.message.edit_text(
        f"🚦 <b>Maintenance Mode</b>\n\nCurrent status: {status}",
        reply_markup=kb.maintenance_toggle_keyboard(new_value == "1"),
    )
    await callback.answer("✅ Updated")
