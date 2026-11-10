from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    waiting_welcome_text = State()
    waiting_welcome_image = State()
    waiting_broadcast_message = State()
    waiting_channel_id = State()
    waiting_channel_remove = State()
    waiting_user_id_for_ban = State()
    waiting_user_id_for_premium = State()
    waiting_daily_limit = State()
