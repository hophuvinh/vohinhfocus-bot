import os
import json
import logging
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "")
DATA_FILE = "tasks.json"

# ===== DATA =====
def load_tasks():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_tasks(tasks):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

def next_id(tasks):
    return max((t["id"] for t in tasks), default=0) + 1

# ===== NLP PARSER =====
TYPE_KEYWORDS = {
    "kv":       ["kv", "key visual", "concept", "branding", "brand", "logo", "nhận diện"],
    "uiux":     ["ui", "ux", "giao diện", "interface", "trang", "web", "layout", "wireframe"],
    "hr":       ["nhân sự", "quy trình", "hr", "team", "tuyển", "onboard", "cải tiến", "improve"],
    "feedback": ["feedback", "review", "approve", "duyệt", "check", "sửa", "chỉnh"],
    "boss":     ["sếp", "boss", "anh", "chị giao", "yêu cầu gấp"],
}

SOURCE_KEYWORDS = {
    "editorial": ["editorial", "biên tập", "ban biên", "trang tin", "news", "bài"],
    "sales":     ["sales", "kinh doanh", "khách chốt", "chốt tiền", "proposal"],
    "boss":      ["sếp", "boss", "giám đốc"],
    "client":    ["khách hàng", "client", "agency", "đối tác", "samsung", "honda"],
    "self":      ["cá nhân", "tự làm", "mình cần"],
}

URGENCY_PATTERNS = [
    (r"hôm nay|today|ngay bây giờ|gấp|urgent", 0),
    (r"ngày mai|tomorrow|mai", 1),
    (r"tuần này|this week", 3),
    (r"(\d+)\s*ngày", None),  # X ngày
]

def parse_task(text: str) -> dict:
    text_lower = text.lower()

    # Detect type
    task_type = "kv"
    for t, keywords in TYPE_KEYWORDS.items():
        if any(k in text_lower for k in keywords):
            task_type = t
            break

    # Detect source
    source = "self"
    for s, keywords in SOURCE_KEYWORDS.items():
        if any(k in text_lower for k in keywords):
            source = s
            break

    # Detect deadline
    deadline = None
    today = datetime.now()
    for pattern, delta in URGENCY_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            if delta is None:
                # Extract number of days
                days = int(match.group(1))
                deadline = (today + timedelta(days=days)).strftime("%Y-%m-%d")
            else:
                deadline = (today + timedelta(days=delta)).strftime("%Y-%m-%d")
            break

    if not deadline:
        deadline = today.strftime("%Y-%m-%d")

    # Determine if deep or reactive
    deep_types = ["kv", "uiux", "hr"]
    today_slot = "focus" if task_type in deep_types else "reactive"

    # Clean task name — remove filler words
    name = text.strip()
    for filler in ["hôm nay cần làm", "cần làm", "hôm nay", "tôi cần", "mình cần", "làm"]:
        if name.lower().startswith(filler):
            name = name[len(filler):].strip()
            break
    name = name[:1].upper() + name[1:] if name else text

    return {
        "type": task_type,
        "source": source,
        "deadline": deadline,
        "today": today_slot,
        "name": name,
    }

TYPE_LABELS = {
    "kv": "KV/Branding",
    "uiux": "UI/UX",
    "hr": "HR/Quy trình",
    "feedback": "Feedback",
    "boss": "Từ sếp"
}

SOURCE_LABELS = {
    "editorial": "Editorial",
    "sales": "Sales",
    "boss": "Sếp",
    "client": "Khách hàng",
    "self": "Cá nhân"
}

TODAY_LABELS = {
    "focus": "🎯 Deep Focus hôm nay",
    "reactive": "⚡ Reactive hôm nay",
    "inbox": "📥 Inbox"
}

# ===== HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Chào Vinh!\n\n"
        "Mình là FocusFlow bot — nhắn tự nhiên để thêm task:\n\n"
        "💬 *Ví dụ:*\n"
        "• _Hôm nay cần làm KV cho dự án Better Choice_\n"
        "• _Feedback 3 banner editorial gấp_\n"
        "• _Sếp giao làm proposal Samsung ngày mai_\n\n"
        "📋 *Lệnh nhanh:*\n"
        "/today — Xem việc hôm nay\n"
        "/inbox — Xem inbox\n"
        "/done — Đánh dấu hoàn thành\n"
        "/week — Tổng quan tuần này",
        parse_mode="Markdown"
    )

async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = load_tasks()
    today_str = datetime.now().strftime("%Y-%m-%d")

    focus = [t for t in tasks if t.get("today") == "focus" and not t.get("done")]
    reactive = [t for t in tasks if t.get("today") == "reactive" and not t.get("done")]
    done = [t for t in tasks if t.get("done")]

    msg = f"📅 *Hôm nay — {datetime.now().strftime('%d/%m/%Y')}*\n\n"

    msg += f"🎯 *Deep Focus ({len(focus)}/3)*\n"
    if focus:
        for t in focus:
            msg += f"  • {t['name']} _[{TYPE_LABELS.get(t['type'], t['type'])}]_\n"
    else:
        msg += "  _Chưa có task — vào /inbox để chọn_\n"

    msg += f"\n⚡ *Reactive ({len(reactive)})*\n"
    if reactive:
        for t in reactive:
            msg += f"  • {t['name']} _[{SOURCE_LABELS.get(t['source'], t['source'])}]_\n"
    else:
        msg += "  _Không có task reactive_\n"

    if done:
        msg += f"\n✅ *Hoàn thành ({len(done)})*\n"
        for t in done[-3:]:
            msg += f"  ~~{t['name']}~~\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

async def inbox_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = load_tasks()
    inbox = [t for t in tasks if t.get("today") == "inbox" and not t.get("done")]

    if not inbox:
        await update.message.reply_text("📥 Inbox trống — ngon lành! 🎉")
        return

    msg = f"📥 *Inbox ({len(inbox)} tasks)*\n\n"
    for t in inbox:
        deadline_str = ""
        if t.get("deadline"):
            d = datetime.strptime(t["deadline"], "%Y-%m-%d")
            deadline_str = f" — {d.strftime('%d/%m')}"
        msg += f"• [{t['id']}] {t['name']} _[{TYPE_LABELS.get(t['type'])}]{deadline_str}_\n"

    msg += "\n_Nhắn `/move [id] focus` hoặc `/move [id] reactive` để assign_"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = load_tasks()
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())

    msg = "📆 *Tuần này*\n\n"
    days_vi = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]

    for i in range(7):
        day = monday + timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        day_tasks = [t for t in tasks if t.get("deadline") == day_str and not t.get("done")]
        is_today = day_str == today.strftime("%Y-%m-%d")

        if day_tasks or is_today:
            marker = " ◀ hôm nay" if is_today else ""
            msg += f"*{days_vi[i]} {day.strftime('%d/%m')}*{marker}\n"
            if day_tasks:
                for t in day_tasks:
                    msg += f"  • {t['name']}\n"
            else:
                msg += "  _Trống_\n"
            msg += "\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = load_tasks()
    active = [t for t in tasks if not t.get("done") and t.get("today") in ["focus", "reactive"]]

    if not active:
        await update.message.reply_text("Không có task nào đang active hôm nay!")
        return

    keyboard = []
    for t in active:
        keyboard.append([InlineKeyboardButton(
            f"✓ {t['name'][:45]}",
            callback_data=f"done_{t['id']}"
        )])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Chọn task đã xong:", reply_markup=reply_markup)

async def move_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Cú pháp: `/move [id] focus` hoặc `/move [id] reactive`", parse_mode="Markdown")
        return

    try:
        task_id = int(args[0])
        slot = args[1].lower()
        if slot not in ["focus", "reactive", "inbox"]:
            raise ValueError()
    except:
        await update.message.reply_text("❌ Sai cú pháp. Ví dụ: `/move 3 focus`", parse_mode="Markdown")
        return

    tasks = load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)

    if not task:
        await update.message.reply_text(f"❌ Không tìm thấy task #{task_id}")
        return

    if slot == "focus":
        focus_count = sum(1 for t in tasks if t.get("today") == "focus" and not t.get("done"))
        if focus_count >= 3:
            await update.message.reply_text("⚠️ Tối đa 3 task Deep Focus mỗi ngày — chọn lọc hơn nhé!")
            return

    task["today"] = slot
    save_tasks(tasks)
    await update.message.reply_text(
        f"✅ *{task['name']}*\n→ {TODAY_LABELS[slot]}",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        return

    parsed = parse_task(text)
    tasks = load_tasks()

    # Check focus limit
    if parsed["today"] == "focus":
        focus_count = sum(1 for t in tasks if t.get("today") == "focus" and not t.get("done"))
        if focus_count >= 3:
            parsed["today"] = "inbox"

    task = {
        "id": next_id(tasks),
        "name": parsed["name"],
        "type": parsed["type"],
        "source": parsed["source"],
        "deadline": parsed["deadline"],
        "today": parsed["today"],
        "done": False,
        "created_at": datetime.now().isoformat()
    }

    tasks.insert(0, task)
    save_tasks(tasks)

    slot_label = TODAY_LABELS[task["today"]]
    deadline_dt = datetime.strptime(task["deadline"], "%Y-%m-%d")
    deadline_label = deadline_dt.strftime("%d/%m/%Y")

    keyboard = [
        [
            InlineKeyboardButton("🎯 → Focus", callback_data=f"move_{task['id']}_focus"),
            InlineKeyboardButton("⚡ → Reactive", callback_data=f"move_{task['id']}_reactive"),
            InlineKeyboardButton("📥 → Inbox", callback_data=f"move_{task['id']}_inbox"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg = (
        f"✅ *Đã thêm task #{task['id']}*\n\n"
        f"📌 {task['name']}\n\n"
        f"• Loại: {TYPE_LABELS[task['type']]}\n"
        f"• Nguồn: {SOURCE_LABELS[task['source']]}\n"
        f"• Deadline: {deadline_label}\n"
        f"• Xếp vào: {slot_label}\n\n"
        f"_Điều chỉnh nếu cần:_"
    )

    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    tasks = load_tasks()

    if data.startswith("done_"):
        task_id = int(data.split("_")[1])
        task = next((t for t in tasks if t["id"] == task_id), None)
        if task:
            task["done"] = True
            save_tasks(tasks)
            await query.edit_message_text(f"✅ Xong! *{task['name']}* 🎉", parse_mode="Markdown")

    elif data.startswith("move_"):
        parts = data.split("_")
        task_id = int(parts[1])
        slot = parts[2]
        task = next((t for t in tasks if t["id"] == task_id), None)
        if task:
            if slot == "focus":
                focus_count = sum(1 for t in tasks if t.get("today") == "focus" and not t.get("done") and t["id"] != task_id)
                if focus_count >= 3:
                    await query.answer("⚠️ Tối đa 3 task Focus mỗi ngày!", show_alert=True)
                    return
            task["today"] = slot
            save_tasks(tasks)
            await query.edit_message_text(
                f"✅ *{task['name']}*\n→ {TODAY_LABELS[slot]} đã cập nhật!",
                parse_mode="Markdown"
            )

# ===== MAIN =====
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today_command))
    app.add_handler(CommandHandler("inbox", inbox_command))
    app.add_handler(CommandHandler("week", week_command))
    app.add_handler(CommandHandler("done", done_command))
    app.add_handler(CommandHandler("move", move_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("FocusFlow bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
