from ErisPulse import sdk
from ErisPulse.Core.Bases import BaseModule
from ErisPulse.Core.Event import message, Event
from .config import load_config


class Main(BaseModule):
    def __init__(self):
        self.sdk = sdk
        self.logger = sdk.logger.get_child("CopyCat")
        self.storage = sdk.storage
        self.config = load_config()
        # 会话状态：
        #   key: "group:{group_id}" 或 "private:{user_id}"
        #   value: {
        #       "last_message": str | None,
        #       "last_sender": str | None,
        #       "repeat_count": int,
        #       "repeated_set": set[str]
        #   }
        self._sessions: dict = {}

    @staticmethod
    def get_load_strategy():
        from ErisPulse.loaders import ModuleLoadStrategy
        return ModuleLoadStrategy(
            lazy_load=False,
            priority=0
        )

    async def on_load(self, event):
        @message.on_message()
        async def repeat_handler(ev: Event):
            # —— 1. 基础过滤 ——
            # 忽略机器人自身消息
            if ev.get_user_id() == ev.get_self_user_id():
                return

            text = ev.get_text()
            if not text:
                return

            # —— 2. 确定会话 key ——
            if ev.is_group_message():
                session_key = f"group:{ev.get_group_id()}"
            elif ev.is_private_message():
                session_key = f"private:{ev.get_user_id()}"
            else:
                return

            # —— 3. 获取/初始化会话状态 ——
            if session_key not in self._sessions:
                self._sessions[session_key] = {
                    "last_message": None,
                    "last_sender": None,
                    "repeat_count": 0,
                    "repeated_set": set()
                }
            state = self._sessions[session_key]

            # —— 4. 已复读过的消息不再复读 ——
            if text in state["repeated_set"]:
                return

            # —— 5. 与上一条消息不同 → 重置为新消息 ——
            if text != state["last_message"]:
                state["last_message"] = text
                state["last_sender"] = ev.get_user_id()
                state["repeat_count"] = 1
                return

            # —— 6. 文本相同，但发送者也相同 → 跳过 ——
            if ev.get_user_id() == state["last_sender"]:
                return

            # —— 7. 不同人发送相同文本 → 递增计数 ——
            state["repeat_count"] += 1
            state["last_sender"] = ev.get_user_id()

            # —— 8. 达到触发次数 → 复读 ——
            trigger = self.config.get("trigger_count", 2)
            if state["repeat_count"] >= trigger:
                self.logger.info(
                    f"[{session_key}] 检测到复读 ({state['repeat_count']}x): {text}"
                )
                await ev.reply(text)
                state["repeated_set"].add(text)

        self.logger.info("CopyCat 模块已加载")

    async def on_unload(self, event):
        self._sessions.clear()
        self.logger.info("CopyCat 模块已卸载")
