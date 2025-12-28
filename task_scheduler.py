from __future__ import annotations

from datetime import datetime, timedelta, timezone
import config
import db


# =====================
# 공통 유틸
# =====================
def utcnow() -> datetime:
    """UTC 현재 시각"""
    return datetime.now(timezone.utc)


def _fmt_timedelta(td: timedelta) -> str:
    if td.total_seconds() < 0:
        td = timedelta(0)
    total = int(td.total_seconds())
    h = total // 3600
    m = (total % 3600) // 60
    return f"{h}시간 {m}분"


# =====================
# 스케줄러
# =====================
class Scheduler:
    """
    - 30초마다 poll() 호출
    - DB 상태를 기준으로 강철 / 양잠 알림을 계산
    - 동일 알림 중복 발송 방지(self.sent)
    """

    def __init__(self, bot):
        self.bot = bot
        self.sent: set[tuple] = set()

    async def _send(self, channel_id: int, message: str):
        """채널에 메시지 전송 (캐시 미스 안전 처리)"""
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except Exception:
                return
        try:
            await channel.send(message)
        except Exception:
            pass

    # =====================
    # 메인 폴링
    # =====================
    async def poll(self):
        now = utcnow()

        # 봇이 속한 모든 서버 / 텍스트 채널 순회
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                await self._poll_steel(guild.id, channel.id, now)
                await self._poll_silk(guild.id, channel.id, now)

    # =====================
    # 강철 작업
    # =====================
    async def _poll_steel(self, guild_id: int, channel_id: int, now: datetime):
        st = db.get_steel(guild_id, channel_id)
        if not st.active or not st.start_ts or not st.last_refuel_ts:
            return

        start = datetime.fromtimestamp(st.start_ts, timezone.utc)
        end = start + config.STEEL_TOTAL_DURATION
        last_refuel = datetime.fromtimestamp(st.last_refuel_ts, timezone.utc)

        # 작업 종료
        if now >= end:
            db.set_steel(guild_id, channel_id, db.SteelState(False, None, None))
            return

        # 마지막 연료로 종료까지 버틸 수 있으면 알림 없음
        if end - last_refuel <= config.STEEL_FUEL_INTERVAL:
            return

        deadline = last_refuel + config.STEEL_FUEL_INTERVAL

        targets = db.get_targets(guild_id, channel_id, "steel")
        if not targets:
            return

        mentions = " ".join(f"<@{u}>" for u in targets)

        # 3h / 2h / 1h / 30m 알림
        for offset in config.STEEL_WARN_OFFSETS:
            fire_time = deadline - offset
            key = ("steel", guild_id, channel_id, int(fire_time.timestamp()))

            # ±20초 오차 허용
            if abs((now - fire_time).total_seconds()) <= 20:
                if key in self.sent:
                    continue
                self.sent.add(key)
                await self._send(
                    channel_id,
                    f"{mentions} 강철연료 보충이 필요합니다!"
                )

    # =====================
    # 양잠 작업
    # =====================
    async def _poll_silk(self, guild_id: int, channel_id: int, now: datetime):
        st = db.get_silk(guild_id, channel_id)
        if st.stage == "none" or not st.start_ts:
            return

        start = datetime.fromtimestamp(st.start_ts, timezone.utc)

        larva_t = start + config.SILK_EGG_TO_LARVA
        pupa_t = larva_t + config.SILK_LARVA_TO_PUPA
        adult_t = pupa_t + config.SILK_PUPA_TO_ADULT
        end_t = adult_t + config.SILK_ADULT_TO_EGG

        # 사이클 종료 → 완전 종료
        if now >= end_t:
            db.set_silk(guild_id, channel_id, db.SilkState("none", None, None))
            return

        targets = db.get_targets(guild_id, channel_id, "silk")
        if not targets:
            return

        mentions = " ".join(f"<@{u}>" for u in targets)

        def repeat(stage: str, begin: datetime, interval: timedelta, msg: str):
            if st.ack_stage == stage:
                return

            elapsed = now - begin
            if elapsed.total_seconds() < 0:
                return

            n = int(elapsed.total_seconds() // interval.total_seconds())
            fire_time = begin + interval * n

            key = ("silk", stage, guild_id, channel_id, n)
            if abs((now - fire_time).total_seconds()) <= 20:
                if key in self.sent:
                    return
                self.sent.add(key)
                return msg

        # 애벌레 단계
        if larva_t <= now < pupa_t:
            st.stage = "larva"
            msg = repeat(
                "larva",
                larva_t,
                config.SILK_REPEAT_LARVA,
                f"{mentions} 누에 알이 부화하였습니다."
            )
            if msg:
                await self._send(channel_id, msg)

        # 번데기 단계
        elif pupa_t <= now < adult_t:
            st.stage = "pupa"
            msg = repeat(
                "pupa",
                pupa_t,
                config.SILK_REPEAT_PUPA,
                f"{mentions} 누에가 번데기가 되었습니다"
            )
            if msg:
                await self._send(channel_id, msg)

        # 성충 단계
        elif adult_t <= now < end_t:
            st.stage = "adult"
            msg = repeat(
                "adult",
                adult_t,
                config.SILK_REPEAT_ADULT,
                f"{mentions} 누에가 성충이 되었습니다."
            )
            if msg:
                await self._send(channel_id, msg)

        db.set_silk(guild_id, channel_id, st)
