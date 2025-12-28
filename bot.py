import os
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

import db
import config
from task_scheduler import Scheduler, utcnow

# =====================
# 환경 설정
# =====================
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
scheduler: Scheduler | None = None


# =====================
# 공통 유틸
# =====================
def fmt_td(td: timedelta) -> str:
    """timedelta를 'X시간 Y분' 형식으로 변환"""
    if td.total_seconds() < 0:
        td = timedelta(0)
    total = int(td.total_seconds())
    h = total // 3600
    m = (total % 3600) // 60
    return f"{h}시간 {m}분"


def fmt_kst(dt_utc: datetime) -> str:
    kst = dt_utc + timedelta(hours=config.KST_OFFSET)
    return f"{kst.hour}시 {kst.minute:02d}분"


def mentioned_user_ids(ctx: commands.Context) -> list[int]:
    return [m.id for m in ctx.message.mentions]


# =====================
# 봇 시작 이벤트
# =====================
@bot.event
async def on_ready():
    global scheduler
    db.init_db()
    scheduler = Scheduler(bot)
    poll_loop.start()
    print("Bot ready (Python 3.11)")


# =====================
# 주기 루프 (알림 전용)
# =====================
@tasks.loop(seconds=30)
async def poll_loop():
    if scheduler:
        await scheduler.poll()


# =====================
# 강철: 대상자 관리
# =====================
@bot.command()
async def 강철인원(ctx):
    db.add_targets(ctx.guild.id, ctx.channel.id, "steel", mentioned_user_ids(ctx))
    await ctx.send("강철 호출 대상자를 추가하였습니다.")


@bot.command()
async def 강철제외(ctx):
    db.remove_targets(ctx.guild.id, ctx.channel.id, "steel", mentioned_user_ids(ctx))
    await ctx.send("강철 호출 대상자에서 제외하였습니다.")


# =====================
# 강철: 타이머 제어
# =====================
@bot.command()
async def 강철시작(ctx):
    st = db.get_steel(ctx.guild.id, ctx.channel.id)
    if st.active:
        await ctx.send("기존 작업의 완료가 필요합니다.")
        return

    now = utcnow()
    db.set_steel(
        ctx.guild.id,
        ctx.channel.id,
        db.SteelState(
            active=True,
            start_ts=int(now.timestamp()),
            last_refuel_ts=int(now.timestamp())
        )
    )
    await ctx.send("강철 작업을 시작하였습니다. (총 34시간, 연료 최대)")


@bot.command()
async def 강철보충(ctx):
    st = db.get_steel(ctx.guild.id, ctx.channel.id)
    if not st.active:
        await ctx.send("현재 강철 작업이 없습니다.")
        return

    now = utcnow()
    st.last_refuel_ts = int(now.timestamp())
    db.set_steel(ctx.guild.id, ctx.channel.id, st)
    await ctx.send(f"강철 연료를 보충하였습니다. (KST {fmt_kst(now)})")


@bot.command()
async def 강철완료(ctx):
    db.set_steel(ctx.guild.id, ctx.channel.id, db.SteelState(False, None, None))
    await ctx.send("강철 타이머를 리셋하였습니다.")


@bot.command()
async def 강철(ctx):
    st = db.get_steel(ctx.guild.id, ctx.channel.id)
    if not st.active or not st.start_ts or not st.last_refuel_ts:
        await ctx.send("현재 강철 작업이 없습니다.")
        return

    now = utcnow()
    start = datetime.fromtimestamp(st.start_ts, timezone.utc)
    end = start + config.STEEL_TOTAL_DURATION
    last_refuel = datetime.fromtimestamp(st.last_refuel_ts, timezone.utc)

    remain_total = end - now

    # 연료가 종료까지 충분한 경우
    if end - last_refuel <= config.STEEL_FUEL_INTERVAL:
        await ctx.send(
            f"현재 강철 작업은 완료까지 {fmt_td(remain_total)} 남아 있으며,\n"
            f"마지막 연료 보충 시간은 KST {fmt_kst(last_refuel)}입니다.\n"
            f"작업 종료 전 추가 연료 보충은 필요하지 않습니다."
        )
        return

    # 다음 연료 시한
    next_deadline = last_refuel + config.STEEL_FUEL_INTERVAL
    remain_fuel = next_deadline - now

    await ctx.send(
        f"현재 강철 작업은 완료까지 {fmt_td(remain_total)} 남아 있으며,\n"
        f"마지막 연료 보충 시간은 KST {fmt_kst(last_refuel)}입니다.\n"
        f"연료 보충까지 {fmt_td(remain_fuel)} 남았습니다."
    )


# =====================
# 양잠: 대상자 관리
# =====================
@bot.command()
async def 양잠인원(ctx):
    db.add_targets(ctx.guild.id, ctx.channel.id, "silk", mentioned_user_ids(ctx))
    await ctx.send("양잠 호출 대상자를 추가하였습니다.")


@bot.command()
async def 양잠제외(ctx):
    db.remove_targets(ctx.guild.id, ctx.channel.id, "silk", mentioned_user_ids(ctx))
    await ctx.send("양잠 호출 대상자에서 제외하였습니다.")


# =====================
# 양잠: 타이머 제어
# =====================
@bot.command()
async def 양잠시작(ctx):
    st = db.get_silk(ctx.guild.id, ctx.channel.id)
    if st.stage != "none":
        await ctx.send("기존 작업의 완료가 필요합니다.")
        return

    now = utcnow()
    db.set_silk(
        ctx.guild.id,
        ctx.channel.id,
        db.SilkState(
            stage="egg",
            start_ts=int(now.timestamp()),
            ack_stage=None
        )
    )
    await ctx.send("양잠을 시작하였습니다. (현재 단계: 알)")


@bot.command()
async def 양잠완료(ctx):
    db.set_silk(ctx.guild.id, ctx.channel.id, db.SilkState("none", None, None))
    await ctx.send("양잠 타이머를 리셋하였습니다.")


@bot.command()
async def 양잠확인(ctx):
    st = db.get_silk(ctx.guild.id, ctx.channel.id)
    if st.stage == "none":
        await ctx.send("현재 진행 중인 양잠이 없습니다.")
        return

    st.ack_stage = st.stage
    db.set_silk(ctx.guild.id, ctx.channel.id, st)
    await ctx.send("현재 단계의 반복 호출을 중단하였습니다.")


@bot.command()
async def 양잠(ctx):
    st = db.get_silk(ctx.guild.id, ctx.channel.id)
    if st.stage == "none" or not st.start_ts:
        await ctx.send("현재 진행 중인 양잠이 없습니다.")
        return

    now = utcnow()
    start = datetime.fromtimestamp(st.start_ts, timezone.utc)

    larva = start + config.SILK_EGG_TO_LARVA
    pupa = larva + config.SILK_LARVA_TO_PUPA
    adult = pupa + config.SILK_PUPA_TO_ADULT
    egg = adult + config.SILK_ADULT_TO_EGG

    if now < larva:
        stage = "알"
        next_stage = "애벌레"
        next_t = larva
    elif now < pupa:
        stage = "애벌레"
        next_stage = "번데기"
        next_t = pupa
    elif now < adult:
        stage = "번데기"
        next_stage = "성충"
        next_t = adult
    elif now < egg:
        stage = "성충"
        next_stage = "알"
        next_t = egg
    else:
        await ctx.send("현재 진행 중인 양잠이 없습니다.")
        return

    remain = next_t - now

    await ctx.send(
        f"현재 누에는 '{stage}' 단계이며,\n"
        f"다음 단계('{next_stage}')까지 {fmt_td(remain)} 남아 있습니다.\n"
        f"KST {fmt_kst(next_t)}에 '{next_stage}' 단계로 전환됩니다."
    )


# =====================
# 실행
# =====================
def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN 환경 변수가 설정되지 않았습니다.")
    bot.run(token)


if __name__ == "__main__":
    main()
