import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
import datetime

TOKEN = ""
DATA_FILE = "points.json"
HISTORY_FILE = "history.json"
BLACKLISTED_ROLES = ["🚫Чорний список", "😈 4/5", "😈 5/5", "😈 3/5"]
ALLOWED_ROLES = ["Власник сервера", "Менеджер Персоналу", "😈 1,534,847/5"]

ROLE_PERMISSIONS = {
    "адмінзвіт": ["Адміністрація", "Діскорд менеджер", "Власник сервера","Адмін+", "😈 1,534,847/5"],
    "модерзвіт": ["Модерація", "Діскорд менеджер", "Власник сервера","😈 1,534,847/5"],
    "дівентерзвіт": ["Діскорд івентер", "Діскорд менеджер", "Власник сервера","😈 1,534,847/5"],
    "івентбал": ["Івентери", "Діскорд менеджер", "Власник сервера","Адмін+", "😈 1,534,847/5"]
}

LOG_CHANNEL_ID = 1395098916491628575    

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ----------------- DATA -----------------
def load_data():
    if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}   

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ----------------- HISTORY -----------------
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def add_history(user_id: int, тип: str, бали: int, **extra):
    """Додає запис в історію з можливістю вказати додаткові поля"""
    history = load_history()
    entry = {
        "user_id": str(user_id),
        "тип": тип,
        "бали": бали,
        "дата": datetime.date.today().isoformat()
    }
    entry.update(extra)  # додаємо всі додаткові дані (посилання, jump_url, порушник тощо)
    history.append(entry)
    save_history(history)



# ----------------- LOG -----------------
async def log_to_channel(bot, embed):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(embed=embed)

# ----------------- ON READY -----------------
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Бот запущено як {bot.user}")

# ----------------- /бали -----------------
# --- helpers для дат ---
def parse_date_input(s: str):
    """Повертає datetime.date з рядка. Основний формат: дд/мм/рррр.
       Додатково пробує рррр-мм-дд та рррр/мм/дд (щоб не падати, якщо хтось звик до старого формату)."""
    import datetime as _dt
    if not s:
        return None
    s = s.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return _dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None  # дамо дружнє повідомлення про помилку нижче

def format_ddmmyyyy(d: "datetime.date|None"):
    import datetime as _dt
    if not d:
        return "сьогодні"
    return d.strftime("%d/%m/%Y")

@tree.command(name="бали", description="Показує бали користувача")
@app_commands.describe(
    користувач="Користувач (необов'язково)",
    з="З якої дати (дд/мм/рррр)",
    по="По яку дату (дд/мм/рррр)"
)
async def бали(
    interaction: discord.Interaction,
    користувач: discord.Member = None,
    з: str = None,
    по: str = None
):
    import datetime

    target = користувач or interaction.user
    uid = str(target.id)

    data = load_data()
    total_points = data.get(uid, 0)

    history = load_history()
    user_history = [h for h in history if h.get("user_id") == uid]

    z_date = parse_date_input(з) if з else None
    po_date = parse_date_input(по) if по else None

    if з and not z_date:
        await interaction.response.send_message(
            "❗ Невірний формат дати в полі **з**. Використовуй `дд/мм/рррр` (наприклад, `01/01/2025`).",
            ephemeral=True
        )
        return
    if по and not po_date:
        await interaction.response.send_message(
            "❗ Невірний формат дати в полі **по**. Використовуй `дд/мм/рррр` (наприклад, `31/01/2025`).",
            ephemeral=True
        )
        return

    if z_date and po_date and z_date > po_date:
        z_date, po_date = po_date, z_date

    def in_range(entry_date_iso: str) -> bool:
        d = datetime.date.fromisoformat(entry_date_iso)  # в історії дата зберігається як YYYY-MM-DD
        if z_date and d < z_date:
            return False
        if po_date and d > po_date:
            return False
        return True

    user_history = [h for h in user_history if in_range(h.get("дата", datetime.date.min.isoformat()))]

    counts = {}
    def inc(key): counts[key] = counts.get(key, 0) + 1

    for h in user_history:
        typ = (h.get("тип") or "").lower()
        punishment = (h.get("покарання") or "").lower()

        if typ.startswith("івент"):  # "івент (хост/допомога, легкий/...)"
            t = "Інші івенти"
            if "легкий" in typ:
                t = "Легкі івенти"
            elif "середній" in typ:
                t = "Середні івенти"
            elif "складний" in typ:
                t = "Складні івенти"
            elif "мега" in typ:
                t = "Мега івенти"
            inc(t)

        elif typ == "модерзвіт":
            if punishment == "бан":
                inc("Діскорд-банів")
            elif punishment == "тайм-аут":
                inc("Діскорд-тайм-аутів")
            elif punishment == "попередження":
                inc("Діскорд-попереджень")
            else:
                inc("Діскорд-звітів")

        elif typ == "адмінзвіт":
            if punishment == "бан":
                inc("Банів")
            elif punishment == "мут":
                inc("Адмін-мутів")
            elif punishment == "кік":
                inc("Адмін-кіків")
            elif punishment == "попередження":
                inc("Адмін-попереджень")
            else:
                inc("Адмін-звітів")

        elif typ == "дівентерзвіт":
            inc("Діскорд-івентів")

        else:
            inc(typ.capitalize() if typ else "Інші")

    total_reports = sum(counts.values())

    period_str = ""
    if z_date or po_date:
        period_str = f"\n\n**Період:** {format_ddmmyyyy(z_date) if z_date else 'початок'} → {format_ddmmyyyy(po_date) if po_date else 'сьогодні'}"

    order = [
        "Легкі івенти", "Середні івенти", "Складні івенти", "Мега івенти",
        "Діскорд-івентів",
        "Діскорд-банів", "Діскорд-тайм-аутів", "Діскорд-попереджень",
        "Банів", "Адмін-мутів", "Адмін-кіків", "Адмін-попереджень",
    ]
    lines = []
    for key in order:
        if key in counts:
            lines.append(f"- **{key}**: {counts[key]}")
    for key in sorted(k for k in counts.keys() if k not in order):
        lines.append(f"- **{key}**: {counts[key]}")

    reports_block = "\n".join(lines) if lines else "Немає записів."

    embed = discord.Embed(
        title=f"📊 Статистика для {target.display_name}",
        description=f"**Усього балів:** {total_points}{period_str}",
        color=discord.Color.blue()
    )
    embed.add_field(name="📌 Кількість звітів (за типами)", value=reports_block, inline=False)
    embed.set_footer(text=f"Усього звітів: {total_reports}")

    await interaction.response.send_message(embed=embed, ephemeral=True)



# ----------------- PERMISSIONS -----------------
def has_permission(interaction: discord.Interaction, command_name: str) -> bool:
    user_roles = [role.name for role in interaction.user.roles]
    allowed_roles = ROLE_PERMISSIONS.get(command_name, [])
    return any(role in allowed_roles for role in user_roles)

# ----------------- Команда /лідерборд -----------------
@tree.command(name="лідерборд", description="Показати топ 10 користувачів за балами")
async def лідерборд(interaction: discord.Interaction):
    data = load_data()

    if not data:
        await interaction.response.send_message("❗ Наразі немає даних про бали.", ephemeral=True)
        return

    sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)

    embed = discord.Embed(
        title="🏆 Топ користувачів за балами",
        description="Ось найактивніші учасники сервера!",
        color=discord.Color.gold()
    )

    for index, (user_id, points) in enumerate(sorted_data[:10], start=1):
        mention = f"<@{user_id}>"
        embed.add_field(name=f"#{index}", value=f"{mention} — **{points} балів**", inline=False)

    await interaction.response.send_message(embed=embed)


# ----------------- Команда /видатибали -----------------
@tree.command(name="видатибали", description="Видати комусь бали вручну")
@app_commands.describe(
    користувач="Кому видати бали",
    кількість="Скільки балів",
    причина="Причина видачі балів"
)
async def видатибали(
    interaction: discord.Interaction,
    користувач: discord.Member,
    кількість: int,
    причина: str
):
    roles = [role.name for role in interaction.user.roles]
    if not any(role in ALLOWED_ROLES for role in roles):
        await interaction.response.send_message("⛔ У вас немає дозволу використовувати цю команду.", ephemeral=True)
        return

    data = load_data()
    uid = str(користувач.id)
    data[uid] = data.get(uid, 0) + кількість
    save_data(data)

    add_history(
        користувач.id,
        "ручна видача",
        кількість,
        причина=причина,
        видано_ким=interaction.user.display_name
    )

    await interaction.response.send_message(
        f"✅ Видано **{кількість}** бал(ів) для {користувач.mention}.\n"
        f"📌 Причина: **{причина}**",
        ephemeral=True
    )

    embed = discord.Embed(
        title="Видача балів вручну",
        description=(
            f"{interaction.user.mention} видав {кількість} бал(ів) для {користувач.mention}\n"
            f"📌 **Причина:** {причина}"
        ),
        color=discord.Color.orange()
    )
    await log_to_channel(bot, embed)

    подяки = [
        "Твоя активність дуже цінується ❤️",
        "Дякуємо за працю!",
        "Чудова робота!",
        "Ми пишаємось вами!",
        "Молодець! Завдяки тобі сервер живий!"
    ]

    dm_embed = discord.Embed(
        title=f"FLAME PROJECT ЦСБ - ТОБІ ПРИЙШЛО {кількість} БАЛ(А/ІВ)!",
        description=(
            f"**Кількість балів:** {кількість}\n"
            f"**Причина:** {причина}"
        ),
        color=discord.Color.green()
    )
    dm_embed.set_footer(
        text=f"Видав: {interaction.user.display_name}",
        icon_url=interaction.user.avatar.url if interaction.user.avatar else None
    )

    try:
        await користувач.send(embed=dm_embed)
    except discord.Forbidden:
        await interaction.followup.send(
            f"⚠️ {користувач.mention} не отримав DM (закриті повідомлення).",
            ephemeral=True
        )




# ----------------- Команда /знятибали -----------------
@tree.command(name="знятибали", description="Зняти певну кількість балів")
@app_commands.describe(
    користувач="З кого зняти бали",
    кількість="Скільки балів зняти",
    причина="Причина зняття балів"
)
async def знятибали(
    interaction: discord.Interaction,
    користувач: discord.Member,
    кількість: int,
    причина: str
):
    roles = [role.name for role in interaction.user.roles]
    if not any(role in ALLOWED_ROLES for role in roles):
        await interaction.response.send_message("⛔ У вас немає дозволу використовувати цю команду.", ephemeral=True)
        return

    data = load_data()
    uid = str(користувач.id)
    old_points = data.get(uid, 0)
    new_points = max(0, old_points - кількість)
    data[uid] = new_points
    save_data(data)

    add_history(
        користувач.id,
        "ручне зняття",
        -кількість,  # від’ємне значення для зняття
        причина=причина,
        зняв=interaction.user.display_name
    )

    await interaction.response.send_message(
        f"⚠️ Знято **{кількість}** бал(ів) з {користувач.mention}.\n"
        f"📌 Причина: **{причина}**",
        ephemeral=True
    )

    embed = discord.Embed(
        title="Зняття балів вручну",
        description=(
            f"{interaction.user.mention} зняв {кількість} бал(ів) з {користувач.mention}\n"
            f"📌 **Причина:** {причина}"
        ),
        color=discord.Color.red()
    )
    await log_to_channel(bot, embed)

    подяки = [
        "Не засмучуйся, головне — рухатись вперед 💪",
        "Це досвід, далі буде краще!",
        "Ніхто не ідеальний, працюй над собою 😉",
        "Помилки — це теж шлях до прогресу!",
        "Ми віримо в тебе ✨"
    ]

    dm_embed = discord.Embed(
        title=f"FLAME PROJECT ЦСБ - У ТЕБЕ ЗНЯТО {кількість} БАЛ(ІВ)!",
        description=(
            f"**Знято балів:** {кількість}\n"
            f"**Причина:** {причина}"
        ),
        color=discord.Color.red()
    )
    dm_embed.set_footer(
        text=f"Зняв: {interaction.user.display_name}",
        icon_url=interaction.user.avatar.url if interaction.user.avatar else None
    )

    try:
        await користувач.send(embed=dm_embed)
    except discord.Forbidden:
        await interaction.followup.send(
            f"⚠️ {користувач.mention} не отримав DM (закриті повідомлення).",
            ephemeral=True
        )



# ----------------- Рольова перевірка для команд -----------------
def has_permission(interaction: discord.Interaction, command_name: str) -> bool:
    user_roles = [role.name for role in interaction.user.roles]
    allowed_roles = ROLE_PERMISSIONS.get(command_name, [])
    return any(role in allowed_roles for role in user_roles)


@tree.command(name="івентбал", description="Видати бали за івент")
@app_commands.describe(
    хост_чи_допомога="Роль у івенті: хост або допомога",
    тип_івенту="Назва івенту (легкий, середній, складний, мега)",
    посилання="Посилання на лог або івент"
)
@app_commands.choices(
    хост_чи_допомога=[
        app_commands.Choice(name="Хост", value="хост"),
        app_commands.Choice(name="Допомога", value="допомога"),
    ],
    тип_івенту=[
        app_commands.Choice(name="Легкий", value="легкий"),
        app_commands.Choice(name="Середній", value="середній"),
        app_commands.Choice(name="Складний", value="складний"),
        app_commands.Choice(name="Мега", value="мега"),
    ]
)
async def івентбал(
    interaction: discord.Interaction,
    хост_чи_допомога: app_commands.Choice[str],
    тип_івенту: app_commands.Choice[str],
    посилання: str
):
    подяки = [
        "Твоя активність дуже цінується ❤️",
        "Дякуємо за працю!",
        "Чудова робота!",
        "Ми пишаємось вами!",
        "Молодець! Завдяки тобі сервер живий!"
    ]

    if not has_permission(interaction, "івентбал"):
        await interaction.response.send_message("⛔ У вас немає дозволу використовувати цю команду.", ephemeral=True)
        return

    хост = хост_чи_допомога.value
    тип = тип_івенту.value
    user = interaction.user

    if хост == "допомога":
        бали = 3 if тип == "мега" else 1
    elif хост == "хост":
        бали = {
            "легкий": 1,
            "середній": 2,
            "складний": 3,
            "мега": 5
        }.get(тип, 0)
        if бали == 0:
            await interaction.response.send_message("❗ Невірний тип івенту.", ephemeral=True)
            return

    uid = str(user.id)
    data = load_data()
    data[uid] = data.get(uid, 0) + бали
    save_data(data)

    add_history(user.id, f"івент ({хост}, {тип})", бали)

    embed = discord.Embed(
        title=f"FLAME PROJECT ЦСБ - ТОБІ ПРИЙШЛО {бали} БАЛ(А/ІВ) ЗА ІВЕНТ!",
        description=(
            f"**Тип івенту:** {тип.title()}\n"
            f"**Роль в івенті:** {хост.capitalize()}\n"
            f"**Кількість балів:** {бали}\n"
            f"📎 [Посилання на івент]({посилання})\n\n"
            f"> {random.choice(подяки)}"
        ),
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Видав: {user.display_name}", icon_url=user.avatar.url if user.avatar else None)

    try:
        await user.send(embed=embed)
    except discord.Forbidden:
        await interaction.followup.send(
            f"⚠️ {user.mention} не отримав DM (закриті повідомлення).",
            ephemeral=True
        )

    await interaction.response.send_message(
        f"✅ Видано {бали} бал(ів) для {user.mention} як **{хост}**!", ephemeral=True
    )

    msg = await interaction.channel.send(
        f"**Івентер звіт**\n\n"
        f"**Івентер:** {user.mention}\n"
        f"**Хост/Допомога:** {хост.capitalize()}\n"
        f"**Тип івенту:** {тип.title()}\n"
        f"**Кількість балів:** {бали}\n"
        f"**Посилання на івент:** {посилання}"
    )

    log_embed = discord.Embed(
        title="📥 Бал за івент (у грі)",
        description=(
            f"{user.mention} отримав **{бали}** бал(ів) за {хост} ({тип})\n"
            f"[📄 Переглянути публічний звіт]({msg.jump_url})"
        ),
        color=discord.Color.orange()
    )
    await log_to_channel(bot, log_embed)
    


@tree.command(name="модерзвіт", description="Звіт модератора")
@app_commands.describe(
    порушник="Ім'я або тег порушника",
    правило="Порушене правило (наприклад 3.1)",
    покарання="Тип покарання: попередження, тайм-аут, бан",
    час_покарання="Тривалість покарання (необов'язково)",
    посилання="Посилання на повідомлення з видачею покарання"
)
@app_commands.choices(
    покарання=[
        app_commands.Choice(name="Попередження", value="попередження"),
        app_commands.Choice(name="Тайм-аут", value="тайм-аут"),
        app_commands.Choice(name="Бан", value="бан"),
    ],
    правило=[
        app_commands.Choice(name=f"Правило {i}", value=str(i)) for i in range(1, 15)
    ] + [
        app_commands.Choice(name="Правило 3.1", value="3.1")
    ]
)
async def модерзвіт(
    interaction: discord.Interaction,
    порушник: str,
    правило: app_commands.Choice[str],
    покарання: app_commands.Choice[str],
    посилання: str,
    час_покарання: str = None
):
    подяки = [
        "Твоя активність дуже цінується ❤️",
        "Дякуємо за працю!",
        "Чудова робота!",
        "Ми пишаємось вами!",
        "Молодець! Завдяки тобі сервер живий!"
    ]

    if not has_permission(interaction, "модерзвіт"):
        await interaction.response.send_message("⛔ У вас немає дозволу використовувати цю команду.", ephemeral=True)
        return

    покарання = покарання.value
    правило = правило.value
    час = час_покарання if час_покарання else "-"

    правильні = {"попередження": 1, "тайм-аут": 2, "бан": 2}
    бали = правильні.get(покарання)
    if бали is None:
        await interaction.response.send_message("❗ Невірне покарання.", ephemeral=True)
        return

    uid = str(interaction.user.id)
    data = load_data()
    data[uid] = data.get(uid, 0) + бали
    save_data(data)

    await interaction.response.send_message(
        f"✅ Модератор {interaction.user.mention} отримав {бали} бал(и) за `{покарання}`.", ephemeral=True
    )

    msg = await interaction.channel.send(
        f"**Модерзвіт**\n\n"
        f"**Модератор:** {interaction.user.mention}\n"
        f"**Порушник:** {порушник}\n"
        f"**Порушене правило:** {правило}\n"
        f"**Покарання:** {покарання.title()}\n"
        f"**Час покарання:** {час}\n"
        f"**Бали:** {бали}\n"
        f"📎 **Посилання:** {посилання}"
    )

    add_history(
        interaction.user.id,
        "модерзвіт",
        бали,
        порушник=порушник,
        правило=правило,
        покарання=покарання,
        час=час,
        посилання=посилання,
        звіт_url=msg.jump_url
    )

    log_embed = discord.Embed(
        title="📥 Бал за модер звіт",
        description=(
            f"{interaction.user.mention} отримав **{бали}** бал(ів) за `{покарання}` (порушення {правило})\n"
            f"[📄 Переглянути публічний звіт]({msg.jump_url})"
        ),
        color=discord.Color.orange()
    )
    await log_to_channel(bot, log_embed)

    embed = discord.Embed(
        title=f"FLAME PROJECT ЦСБ - ТОБІ ПРИЙШЛО {бали} БАЛ(А/ІВ) ЗА ЗВІТ!",
        description=(
            f"**Порушник:** {порушник}\n"
            f"**Порушене правило:** {правило}\n"
            f"**Покарання:** {покарання.title()}\n"
            f"**Час покарання:** {час}\n"
            f"📎 [Посилання на покарання]({посилання})\n"
            f"**Кількість балів:** {бали}\n\n"
            f"> {random.choice(подяки)}"
        ),
        color=discord.Color.green()
    )
    embed.set_footer(
        text=f"Звіт подав: {interaction.user.display_name}",
        icon_url=interaction.user.avatar.url if interaction.user.avatar else None
    )

    try:
        await interaction.user.send(embed=embed)
    except discord.Forbidden:
        await interaction.followup.send(
            f"⚠️ {interaction.user.mention} не отримав DM (закриті повідомлення).",
            ephemeral=True
        )






@tree.command(name="адмінзвіт", description="Звіт адміністратора")
@app_commands.describe(
    покарання="Тип покарання: попередження, овервотч, мут, кік, бан",
    час_покарання="Тривалість покарання (необов'язково)",
    нікнейм="Нікнейм порушника",
    правило="Порушене правило (від 1 до 11)",
    стімайді="Steam ID порушника"
)
@app_commands.choices(
    покарання=[
        app_commands.Choice(name="Попередження", value="попередження"),
        app_commands.Choice(name="Мут", value="мут"),
        app_commands.Choice(name="Кік", value="кік"),
        app_commands.Choice(name="Бан", value="бан"),
    ],
    правило=[
        app_commands.Choice(name=f"Правило {i}", value=str(i)) for i in range(1, 12)
    ]
)
async def адмінзвіт(
    interaction: discord.Interaction,
    покарання: app_commands.Choice[str],
    нікнейм: str,
    правило: app_commands.Choice[str],
    стімайді: str,
    час_покарання: str = None
):
    покарання = покарання.value
    правило = правило.value
    подяки = [
        "Твоя активність дуже цінується ❤️",
        "Дякуємо за працю!",
        "Чудова робота!",
        "Ми пишаємось вами!",
        "Молодець! Завдяки тобі сервер живий!"
    ]

    if not has_permission(interaction, "адмінзвіт"):
        await interaction.response.send_message("⛔ У вас немає дозволу використовувати цю команду.", ephemeral=True)
        return

    типи_балів = {
        "попередження": 1,
        "мут": 2,
        "кік": 2,
        "бан": 2
    }

    бали = типи_балів.get(покарання)
    if бали is None:
        await interaction.response.send_message("❗ Невідомий тип покарання.", ephemeral=True)
        return

    user = interaction.user
    uid = str(user.id)
    data = load_data()
    data[uid] = data.get(uid, 0) + бали
    save_data(data)

    час_text = час_покарання if час_покарання else "-"

    embed_dm = discord.Embed(
        title=f"FLAME PROJECT ЦСБ - ТОБІ ПРИЙШЛО {бали} БАЛ(А/ІВ) ЗА ЗВІТ!",
        description=(
            f"**Покарання:** {покарання.title()}\n"
            f"**Порушник:** {нікнейм}\n"
            f"**Порушене правило:** {правило}\n"
            f"**Steam ID:** {стімайді}\n"
            f"**Тривалість:** {час_text}\n"
            f"**Кількість балів:** {бали}\n\n"
            f"> {random.choice(подяки)}"
        ),
        color=discord.Color.green()
    )
    embed_dm.set_footer(text=f"Звіт подав: {user.display_name}", icon_url=user.avatar.url if user.avatar else None)

    try:
        await user.send(embed=embed_dm)
    except discord.Forbidden:
        await interaction.followup.send(f"⚠️ {user.mention} не отримав DM (закриті повідомлення).", ephemeral=True)

    msg = await interaction.channel.send(
        f"**Адмін звіт**\n\n"
        f"**Адмін:** {user.mention}\n"
        f"**Порушник:** {нікнейм}\n"
        f"**Правило:** {правило}\n"
        f"**Steam ID:** {стімайді}\n"
        f"**Покарання:** {покарання.title()}\n"
        f"**Тривалість:** {час_text}\n"
        f"**Бали:** {бали}"
    )

    add_history(
        user.id,
        "адмінзвіт",
        бали,
        порушник=нікнейм,
        правило=правило,
        покарання=покарання,
        стімайді=стімайді,
        час=час_text,
        звіт_url=msg.jump_url
    )

    log_embed = discord.Embed(
        title="📥 Бал за адмін звіт",
        description=(
            f"{user.mention} отримав **{бали}** бал(ів) за `{покарання}` (порушення {правило})\n"
            f"[📄 Переглянути публічний звіт]({msg.jump_url})"
        ),
        color=discord.Color.orange()
    )
    await log_to_channel(bot, log_embed)

    await interaction.response.send_message(
        f"✅ {user.mention} отримав **{бали}** бал(ів) за покарання **{покарання}**.\n"
        f"**Нікнейм порушника:** {нікнейм}\n"
        f"**Порушене правило:** {правило}\n"
        f"**Steam ID:** {стімайді}\n"
        f"**Тривалість покарання:** {час_text}",
        ephemeral=True
    )






@tree.command(name="дівентерзвіт", description="Звіт дискорд-івентера")
@app_commands.describe(
    приз="Чи був приз (з призом / без приза)",
    посилання="Посилання на лог завершеного івенту"
)
@app_commands.choices(
    приз=[
        app_commands.Choice(name="З призом", value="з призом"),
        app_commands.Choice(name="Без приза", value="без приза"),
    ]
)
async def дівентерзвіт(
    interaction: discord.Interaction,
    приз: app_commands.Choice[str],
    посилання: str
):
    подяки = [
        "Твоя активність дуже цінується ❤️",
        "Дякуємо за працю!",
        "Чудова робота!",
        "Ми пишаємось вами!",
        "Молодець! Завдяки тобі сервер живий!"
    ]

    if not has_permission(interaction, "дівентерзвіт"):
        await interaction.response.send_message("⛔ У вас немає дозволу використовувати цю команду.", ephemeral=True)
        return

    приз_value = приз.value
    бали = 5 if приз_value == "з призом" else 2

    uid = str(interaction.user.id)
    data = load_data()
    data[uid] = data.get(uid, 0) + бали
    save_data(data)

    await interaction.response.send_message(
        f"✅ Тобі нараховано **{бали} бал(ів)** за івент **({приз_value})**.", ephemeral=True
    )

    msg = await interaction.channel.send(
        f"**Діскорд-Івентер звіт**\n\n"
        f"**Івентер:** {interaction.user.mention}\n"
        f"**Приз:** {приз_value}\n"
        f"**Бали:** {бали}\n"
        f"**Посилання на лог:** {посилання}"
    )

    add_history(
        interaction.user.id,
        "дівентерзвіт",
        бали,
        приз=приз_value,
        посилання=посилання,
        звіт_url=msg.jump_url
    )

    log_embed = discord.Embed(
        title="📥 Бал за діскорд івент-звіт",
        description=(
            f"{interaction.user.mention} отримав **{бали}** бал(ів) за Discord-івент ({приз_value})\n"
            f"[📄 Переглянути публічний звіт]({msg.jump_url})"
        ),
        color=discord.Color.orange()
    )
    await log_to_channel(bot, log_embed)

    embed = discord.Embed(
        title=f"FLAME PROJECT ЦСБ - ТОБІ ПРИЙШЛО {бали} БАЛ(А/ІВ) ЗА ІВЕНТ!",
        description=(
            f"**Призовий статус:** {приз_value.capitalize()}\n"
            f"📎 [Посилання на лог івенту]({посилання})\n\n"
            f"> {random.choice(подяки)}"
        ),
        color=discord.Color.green()
    )
    embed.set_footer(
        text=f"Звіт подав: {interaction.user.display_name}",
        icon_url=interaction.user.avatar.url if interaction.user.avatar else None
    )

    try:
        await interaction.user.send(embed=embed)
    except discord.Forbidden:
        await interaction.followup.send(
            f"⚠️ {interaction.user.mention} не отримав DM (закриті повідомлення).",
            ephemeral=True
        )




bot.run(TOKEN)