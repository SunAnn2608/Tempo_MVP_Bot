import json
import os

DATA_FILE = "data/data.json"

def load_data():
if not os.path.exists("data"):
os.makedirs("data")

```
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

return {"users": {}}
```

def save_data(data):
with open(DATA_FILE, "w", encoding="utf-8") as f:
json.dump(data, f, ensure_ascii=False, indent=2)

def add_task(user_id, task):
data = load_data()
user_id = str(user_id)

```
if user_id not in data["users"]:
    data["users"][user_id] = {"tasks": []}

data["users"][user_id]["tasks"].append(task)
save_data(data)

return {"message": "✅ Задача добавлена"}
```

def get_tasks_summary(user_id):
data = load_data()
user_id = str(user_id)

```
tasks = data["users"].get(user_id, {}).get("tasks", [])

if not tasks:
    return "📭 Нет задач"

text = "📋 Задачи:\n\n"
for i, t in enumerate(tasks, 1):
    text += f"{i}. {t['title']} ({t.get('duration_hours',1)}ч)\n"

return text
```

def clear_all_tasks(user_id):
data = load_data()
user_id = str(user_id)

```
if user_id in data["users"]:
    data["users"][user_id]["tasks"] = []

save_data(data)
```
