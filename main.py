"""
Telegram Userbot - Auto Group Messenger
Uses Telethon with session string authentication.

Requirements:
    pip install telethon

Generate session string using: python generate_session.py
"""

import asyncio
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import Channel, Chat

# ─── CONFIG ────────────────────────────────────────────────────────────────────

SESSION_STRING = ""   # paste your session string
API_ID         = 21752358                             # from https://my.telegram.org
API_HASH       = "fb46a136fed4a4de27ab057c7027fec3"               # from https://my.telegram.org

# ─── STATE ─────────────────────────────────────────────────────────────────────

state = {
    "text"     : "Hello from my userbot! 👋",
    "interval" : 60,          # seconds between broadcasts
    "running"  : False,
    "blacklist": set(),        # group IDs to skip
    "whitelist": set(),        # if non-empty, only these groups receive messages
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ─── CLIENT ────────────────────────────────────────────────────────────────────

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ─── BROADCAST LOOP ────────────────────────────────────────────────────────────

async def broadcast_loop():
    while state["running"]:
        await do_broadcast()
        await asyncio.sleep(state["interval"])

broadcast_task = None   # holds the running asyncio Task

async def do_broadcast():
    sent, skipped = 0, 0
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        if not isinstance(entity, (Channel, Chat)):
            continue
        gid = entity.id
        if gid in state["blacklist"]:
            skipped += 1
            continue
        if state["whitelist"] and gid not in state["whitelist"]:
            skipped += 1
            continue
        try:
            await client.send_message(entity, state["text"])
            sent += 1
            await asyncio.sleep(2)          # small delay to avoid flood-wait
        except Exception as e:
            log.warning(f"Failed to send to {dialog.name}: {e}")
            skipped += 1
    log.info(f"Broadcast done — sent: {sent}, skipped: {skipped}")

# ─── COMMANDS ──────────────────────────────────────────────────────────────────

def is_me(event):
    return event.out  # only react to your own messages

@client.on(events.NewMessage(pattern=r"^\.text (.+)", outgoing=True))
async def cmd_set_text(event):
    state["text"] = event.pattern_match.group(1)
    await event.edit(f"✅ Broadcast text updated:\n`{state['text']}`")

@client.on(events.NewMessage(pattern=r"^\.time (\d+)([smh]?)", outgoing=True))
async def cmd_set_time(event):
    value = int(event.pattern_match.group(1))
    unit  = event.pattern_match.group(2) or "s"
    multiplier = {"s": 1, "m": 60, "h": 3600}
    state["interval"] = value * multiplier.get(unit, 1)
    await event.edit(f"✅ Interval set to **{state['interval']}s** ({value}{unit})")

@client.on(events.NewMessage(pattern=r"^\.start$", outgoing=True))
async def cmd_start(event):
    global broadcast_task
    if state["running"]:
        await event.edit("⚠️ Broadcast is already running.")
        return
    if not state["text"]:
        await event.edit("⚠️ No text set. Use `.text <message>` first.")
        return
    state["running"] = True
    broadcast_task = asyncio.ensure_future(broadcast_loop())
    await event.edit(
        f"🚀 Broadcast **started**!\n"
        f"📝 Text: `{state['text']}`\n"
        f"⏱ Interval: `{state['interval']}s`"
    )

@client.on(events.NewMessage(pattern=r"^\.stop$", outgoing=True))
async def cmd_stop(event):
    global broadcast_task
    if not state["running"]:
        await event.edit("⚠️ Broadcast is not running.")
        return
    state["running"] = False
    if broadcast_task:
        broadcast_task.cancel()
        broadcast_task = None
    await event.edit("🛑 Broadcast **stopped**.")

@client.on(events.NewMessage(pattern=r"^\.status$", outgoing=True))
async def cmd_status(event):
    lines = [
        f"**📊 Userbot Status**",
        f"• Running  : {'✅ Yes' if state['running'] else '❌ No'}",
        f"• Text     : `{state['text']}`",
        f"• Interval : `{state['interval']}s`",
        f"• Blacklist: `{len(state['blacklist'])} groups`",
        f"• Whitelist: `{len(state['whitelist'])} groups`",
    ]
    await event.edit("\n".join(lines))

@client.on(events.NewMessage(pattern=r"^\.send$", outgoing=True))
async def cmd_send_now(event):
    await event.edit("📤 Sending broadcast now...")
    await do_broadcast()
    await event.edit("✅ Manual broadcast complete.")

@client.on(events.NewMessage(pattern=r"^\.blacklist$", outgoing=True))
async def cmd_blacklist(event):
    """Blacklist the current group."""
    chat = await event.get_chat()
    state["blacklist"].add(chat.id)
    state["whitelist"].discard(chat.id)
    await event.edit(f"🚫 **{chat.title}** added to blacklist.")

@client.on(events.NewMessage(pattern=r"^\.whitelist$", outgoing=True))
async def cmd_whitelist(event):
    """Whitelist the current group (only whitelisted groups receive msgs)."""
    chat = await event.get_chat()
    state["whitelist"].add(chat.id)
    state["blacklist"].discard(chat.id)
    await event.edit(f"✅ **{chat.title}** added to whitelist.")

@client.on(events.NewMessage(pattern=r"^\.unlist$", outgoing=True))
async def cmd_unlist(event):
    """Remove current group from both lists."""
    chat = await event.get_chat()
    state["blacklist"].discard(chat.id)
    state["whitelist"].discard(chat.id)
    await event.edit(f"↩️ **{chat.title}** removed from all lists.")

@client.on(events.NewMessage(pattern=r"^\.groups$", outgoing=True))
async def cmd_list_groups(event):
    """List all joined groups."""
    lines = ["**📋 Joined Groups:**"]
    async for dialog in client.iter_dialogs():
        if isinstance(dialog.entity, (Channel, Chat)):
            gid  = dialog.entity.id
            flag = ""
            if gid in state["blacklist"]:  flag = " 🚫"
            elif gid in state["whitelist"]: flag = " ✅"
            lines.append(f"• `{gid}` — {dialog.name}{flag}")
    await event.edit("\n".join(lines[:50]))   # cap at 50 to avoid message size limit

@client.on(events.NewMessage(pattern=r"^\.help$", outgoing=True))
async def cmd_help(event):
    help_text = """
**🤖 Userbot Commands**

`.text <msg>`  — set broadcast message
`.time <n>[s/m/h]` — set interval (e.g. `.time 30m`)
`.start`       — start auto broadcast
`.stop`        — stop auto broadcast
`.send`        — send broadcast once immediately
`.status`      — show current config
`.groups`      — list all joined groups
`.blacklist`   — skip this group in broadcasts
`.whitelist`   — only send to whitelisted groups
`.unlist`      — remove this group from lists
`.help`        — show this message
""".strip()
    await event.edit(help_text)

# ─── MAIN ──────────────────────────────────────────────────────────────────────

async def main():
    await client.start()
    me = await client.get_me()
    log.info(f"Logged in as {me.first_name} (@{me.username})")
    log.info("Type .help in any chat to see commands.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    client.loop.run_until_complete(main())
