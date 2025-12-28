import os
from datetime import datetime, timezone
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

import db, config
from task_scheduler import Scheduler, utcnow

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
scheduler: Scheduler | None = None

@bot.event
async def on_ready():
    global scheduler
    db.init_db()
    scheduler = Scheduler(bot)
    poll_loop.start()
    print("Bot ready (Python 3.11)")

@tasks.loop(seconds=30)
async def poll_loop():
    await scheduler.poll()

def mentions(ctx):
    return [m.id for m in ctx.message.mentions]

# =====================
# 강철
# =====================
@bot.command()
async def 강철인원(ctx):
    db.add_targets(ctx.guild.id, ctx.channel.id, "steel", mentions(ctx))
    await ctx.send("강철 호출 대상자 추가 완료.")

@bot.command()
async def 강철제외(ctx):
    db.remove_targets(ctx.guild.id, ctx.channel.id, "steel", mentions(ctx))
    await ctx.send("강철 호출 대상자 제외 완료.")

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
        db.SteelState(True, int(now.timestamp()), int(now.timestamp()))
    )
    await ctx.send("강철 작업 시작 (34시간)")

@bot.command()
async def 강철(ctx):
    st = db.get_steel(ctx.guild.id, ctx.channel.id)
    if not st.active:
        await ctx.send("현재 강철 작업 없음")
        return
    now = utcnow()
    start = datetime.fromtimestamp(st.start_ts, timezone.utc)
    end = start + config.STEEL_TOTAL_DURATION
    await ctx.send(f"현재 강철작업은 완료까지 {int((end-now).total_seconds()//3600)}시간 남았습니다.")

@bot.command()
async def 강철보충(ctx):
    st = db.get_steel(ctx.guild.id, ctx.channel.id)
    if not st.active:
        await ctx.send("현재 강철 작업 없음")
        return
    now = utcnow()
    st.last_refuel_ts = int(now.timestamp())
    db.set_steel(ctx.guild.id, ctx.channel.id, st)
    await ctx.send("강철 연료 보충 완료")

@bot.command()
async def 강철완료(ctx):
    db.set_steel(ctx.guild.id, ctx.channel.id, db.SteelState(False, None, None))
    await ctx.send("강철 타이머 리셋")

# =====================
# 양잠
# =====================
@bot.command()
async def 양잠인원(ctx):
    db.add_targets(ctx.guild.id, ctx.channel.id, "silk", mentions(ctx))
    await ctx.send("양잠 호출 대상자 추가 완료.")

@bot.command()
async def 양잠제외(ctx):
    db.remove_targets(ctx.guild.id, ctx.channel.id, "silk", mentions(ctx))
    await ctx.send("양잠 호출 대상자 제외 완료.")

@bot.command()
async def 양잠시작(ctx):
    st = db.get_silk(ctx.guild.id, ctx.channel.id)
    if st.stage != "none":
        await ctx.send("기존 작업의 완료가 필요합니다.")
        return
    now = utcnow()
    db.set_silk(ctx.guild.id, ctx.channel.id, db.SilkState("egg", int(now.timestamp()), None))
    await ctx.send("양잠 시작: 알 상태")

@bot.command()
async def 양잠(ctx):
    st = db.get_silk(ctx.guild.id, ctx.channel.id)
    if st.stage == "none":
        await ctx.send("현재 진행중인 양잠 없음")
        return
    await ctx.send(f"현재 양잠 단계: {st.stage}")

@bot.command()
async def 양잠확인(ctx):
    st = db.get_silk(ctx.guild.id, ctx.channel.id)
    if st.stage == "none":
        await ctx.send("현재 진행중인 양잠 없음")
        return
    st.ack_stage = st.stage
    db.set_silk(ctx.guild.id, ctx.channel.id, st)
    await ctx.send("현재 단계 호출 중지")

@bot.command()
async def 양잠완료(ctx):
    db.set_silk(ctx.guild.id, ctx.channel.id, db.SilkState("none", None, None))
    await ctx.send("양잠 타이머 리셋")

def main():
    bot.run(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    main()
