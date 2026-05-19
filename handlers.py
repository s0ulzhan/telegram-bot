from datetime import datetime, timedelta
from telebot import types
from utils import get_color

user_data = {}

def register_handlers(bot, db, storage):

    # START
    @bot.message_handler(commands=['start'])
    def start(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ Add Task", "📌 Tasks")
        markup.add("📊 Today", "📅 Calendar")
        markup.add("🗑 Delete Task", "📄 Export CSV")

        bot.send_message(message.chat.id, "👋 CtrlDeadline Bot Ready", reply_markup=markup)

    # ADD TASK
    @bot.message_handler(func=lambda m: m.text == "➕ Add Task")
    def add(message):
        user_data[message.from_user.id] = {}
        bot.send_message(message.chat.id, "✏️ Enter title:")

    # TASKS
    @bot.message_handler(func=lambda m: m.text == "📌 Tasks")
    def tasks(message):
        try:
            data = db.get_tasks(message.from_user.id)

            if not data:
                bot.send_message(message.chat.id, "📭 No tasks")
                return

            now = datetime.now()

            for i, t in enumerate(data, 1):
                print("DB ROW:", t)  
                print("PHOTO_ID:", t[10])
                photo_id = t[10]

                diff = t[3] - now
                left = "❌ expired" if diff.total_seconds() < 0 else f"{diff.days}d {diff.seconds // 3600}h"

                text = f"{i}. {get_color(t[3])} {t[2]}\n⏳ {left}"


                try:
                    if photo_id and photo_id != "None":
                        bot.send_photo(message.chat.id, photo_id, caption=text[:1000])
                    else:
                        bot.send_message(message.chat.id, text)
                except Exception as e:
                    print("SEND ERROR:", e)
                    bot.send_message(message.chat.id, text)

        except Exception as e:
            print("TASK ERROR:", e)
            bot.send_message(message.chat.id, "Error loading tasks")

    # TODAY


    @bot.message_handler(func=lambda m: m.text == "📊 Today")
    def today(message):
        try:
            tasks = db.get_tasks(message.from_user.id)

            today_date = datetime.now().date()

            text = "📊 Today:\n\n"
            count = 0

            for t in tasks:
                task_datetime = t[3]  

                if task_datetime.date() == today_date:
                    text += f"{get_color(t[3])} {t[2]} — {t[3]}\n"
                    count += 1

                if count == 3:
                    break

            if count == 0:
                text += "Нет задач на сегодня"

            bot.send_message(message.chat.id, text)

        except Exception as e:
            print(e)  

    # CALENDAR
    @bot.message_handler(func=lambda m: m.text == "📅 Calendar")
    def calendar(message):
        try:
            tasks = db.get_tasks(message.from_user.id)

            now = datetime.now()
            week = now + timedelta(days=7)

            grouped = {}
            weekdays = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

            for t in tasks:
                if now.date() <= t[3].date() <= week.date():

                    day = t[3].date()
                    wd = weekdays[t[3].weekday()]

                    if day not in grouped:
                        grouped[day] = {"wd": wd, "tasks": []}

                    grouped[day]["tasks"].append(t[2])

            text = "📅 Calendar (7 days)\n\n"

            for d in sorted(grouped):
                text += f"📆 {grouped[d]['wd']} — {d}\n"
                for i, t in enumerate(grouped[d]["tasks"], 1):
                    text += f"   {i}. {t}\n"

            bot.send_message(message.chat.id, text)

        except Exception as e:
            bot.send_message(message.chat.id, "Calendar error")

    # DELETE START
    @bot.message_handler(func=lambda m: m.text == "🗑 Delete Task")
    def delete(message):
        tasks = db.get_tasks(message.from_user.id)

        if not tasks:
            bot.send_message(message.chat.id, "No tasks")
            return

        user_data[message.from_user.id] = {"delete": tasks}

        text = "🗑 Choose task:\n\n"
        for i, t in enumerate(tasks, 1):
            text += f"{i}. {t[2]}\n"

        bot.send_message(message.chat.id, text)

    # EXPORT CSV
    @bot.message_handler(func=lambda m: m.text == "📄 Export CSV")
    def export(message):
        tasks = db.get_all()

        if storage.export(tasks):
            bot.send_message(message.chat.id, "CSV exported!")
        else:
            bot.send_message(message.chat.id, "Error")

    # FLOW HANDLER
    @bot.message_handler(content_types=['text', 'photo'])
    def handle(message):

        user_id = message.from_user.id
        text = message.text or ""

        if text.startswith("/"):
            return

        # DELETE STEP
        if user_id in user_data and "delete" in user_data[user_id]:
            try:
                idx = int(text) - 1
                task_id = user_data[user_id]["delete"][idx][0]

                db.delete_task(task_id)
                bot.send_message(message.chat.id, "Deleted!")

            except Exception as e:
                print("DELETE ERROR:", e)
                bot.send_message(message.chat.id, "Wrong input")

            del user_data[user_id]
            return

        # ADD FLOW
        if user_id in user_data:

            try:
                # 1. TITLE
                if "title" not in user_data[user_id]:
                    if not text:
                        bot.send_message(message.chat.id, "❗ Send TEXT for title")
                        return

                    user_data[user_id]["title"] = text

                   
                    markup = types.InlineKeyboardMarkup()
                    markup.add(
                        types.InlineKeyboardButton("📸 Send Photo", callback_data="send_photo"),
                        types.InlineKeyboardButton("⏭ Skip", callback_data="skip_photo")
                    )

                    bot.send_message(message.chat.id, "Choose option:", reply_markup=markup)
                    return

                # 2. PHOTO
                if "photo" not in user_data[user_id]:

                    if message.photo:
                        user_data[user_id]["photo"] = message.photo[-1].file_id
                        bot.send_message(message.chat.id, "📅 Enter Year:")
                        return

                  
                    markup = types.InlineKeyboardMarkup()
                    markup.add(
                        types.InlineKeyboardButton("📸 Send Photo", callback_data="send_photo"),
                        types.InlineKeyboardButton("⏭ Skip", callback_data="skip_photo")
                    )

                    bot.send_message(message.chat.id, "Choose option:", reply_markup=markup)
                    return



                # 3. YEAR
                if "year" not in user_data[user_id]:
                    try:
                        user_data[user_id]["year"] = int(text)
                        bot.send_message(message.chat.id, "📅 Enter month (1-12):")
                    except:
                        bot.send_message(message.chat.id, "❗ Invalid year")
                    return

                # 4. MONTH
                if "month" not in user_data[user_id]:
                    try:
                        user_data[user_id]["month"] = int(text)
                        bot.send_message(message.chat.id, "📅 Enter day (1-31):")
                    except:
                        bot.send_message(message.chat.id, "❗ Invalid month")
                    return

                # 5. DAY
                if "day" not in user_data[user_id]:
                    try:
                        user_data[user_id]["day"] = int(text)
                        bot.send_message(message.chat.id, "⏰ Enter time HH:MM:")
                    except:
                        bot.send_message(message.chat.id, "❗ Invalid day")
                    return

                # 6. TIME 
                if "time" not in user_data[user_id]:
                    try:
                        datetime.strptime(text, "%H:%M")
                        user_data[user_id]["time"] = text

                        dt = datetime(
                            user_data[user_id]["year"],
                            user_data[user_id]["month"],
                            user_data[user_id]["day"],
                            int(text.split(":")[0]),
                            int(text.split(":")[1])
                        )

                        db.add_task(
                            user_id,
                            user_data[user_id]["title"],
                            dt,
                            user_data[user_id].get("photo")
                        )

                        bot.send_message(message.chat.id, "✅ Task saved!")
                        del user_data[user_id]

                    except:
                        bot.send_message(message.chat.id, "❗ Wrong time format")
                    return

            except Exception as e:
                print("FLOW ERROR:", e)
                bot.send_message(message.chat.id, "❌ Error while saving task")
                user_data.pop(user_id, None)

    @bot.callback_query_handler(func=lambda call: True)
    def callback(call):

        user_id = call.from_user.id

        if call.data == "skip_photo":
            user_data[user_id]["photo"] = None
            bot.send_message(call.message.chat.id, "📅 Enter Year:")
            return

        if call.data == "send_photo":
            bot.send_message(call.message.chat.id, "📸 Now send photo")
