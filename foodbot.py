# foodiebot.py
# FoodieBot - Database-Driven Conversational Fast Food System
# Recommended Python: 3.10 or 3.11
#
# Run:
#   python -m venv foodie_env
#   # activate venv
#   pip install streamlit pandas plotly
#   streamlit run foodiebot.py

print("🚀 FoodieBot starting up...")

import streamlit as st
import sqlite3
import json
import pandas as pd
import plotly.express as px
import random
import re
from datetime import datetime
from typing import List, Dict
import sys
import traceback

def global_excepthook(exctype, value, tb):
    traceback.print_exception(exctype, value, tb)
    sys.exit(1)

sys.excepthook = global_excepthook
print("🚀 Imports complete")

# =========================================================
# Database Layer (robust & debug-friendly)
# =========================================================
class FoodieBotDatabase:
    def __init__(self, db_path: str = "foodiebot.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id TEXT PRIMARY KEY,
                name TEXT,
                category TEXT,
                description TEXT,
                ingredients TEXT,
                price REAL,
                calories INTEGER,
                prep_time TEXT,
                dietary_tags TEXT,
                mood_tags TEXT,
                allergens TEXT,
                popularity_score INTEGER,
                chef_special INTEGER,
                limited_time INTEGER,
                spice_level INTEGER,
                image_prompt TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                user_message TEXT,
                bot_response TEXT,
                interest_score INTEGER,
                recommended_products TEXT,
                session_id TEXT
            )
        """)
        self.conn.commit()

    def populate_products_safe(self, products: List[Dict], batch_size: int = 50) -> Dict:
        result = {"success": False, "inserted": 0, "error": None}
        try:
            cursor = self.conn.execute("SELECT COUNT(*) as c FROM products")
            count = cursor.fetchone()["c"]
            if count > 0:
                result["success"] = True
                result["inserted"] = 0
                return result

            insert_sql = """
                INSERT OR REPLACE INTO products (
                    product_id, name, category, description, ingredients,
                    price, calories, prep_time, dietary_tags, mood_tags,
                    allergens, popularity_score, chef_special, limited_time,
                    spice_level, image_prompt
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """

            rows = []
            for p in products:
                rows.append((
                    p.get("product_id"),
                    p.get("name"),
                    p.get("category"),
                    p.get("description"),
                    json.dumps(p.get("ingredients", [])),
                    float(p.get("price", 0.0)) if p.get("price") is not None else None,
                    int(p.get("calories", 0)) if p.get("calories") is not None else None,
                    p.get("prep_time"),
                    json.dumps(p.get("dietary_tags", [])),
                    json.dumps(p.get("mood_tags", [])),
                    json.dumps(p.get("allergens", [])),
                    int(p.get("popularity_score", 0)),
                    1 if p.get("chef_special") else 0,
                    1 if p.get("limited_time") else 0,
                    int(p.get("spice_level", 0)),
                    p.get("image_prompt")
                ))

            inserted = 0
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i+batch_size]
                self.conn.executemany(insert_sql, batch)
                self.conn.commit()
                inserted += len(batch)

            result["success"] = True
            result["inserted"] = inserted
            return result
        except Exception as e:
            result["error"] = str(e)
            try:
                self.conn.rollback()
            except Exception:
                pass
            return result

    def recommend_products(self, mood=None, budget=None, category=None, keywords=None):
        query = "SELECT * FROM products WHERE 1=1"
        params = []

        if budget:
            query += " AND price <= ?"
            params.append(budget)
        if category:
            query += " AND category LIKE ?"
            params.append(f"%{category}%")

        df = pd.read_sql_query(query, self.conn, params=params)

        # Scoring-based keyword & mood matching
        if not df.empty:
            df["match_score"] = df["popularity_score"].copy()
            if mood:
                df["match_score"] += df["mood_tags"].apply(lambda tags: 1 if mood in json.loads(tags) else 0)
            if keywords:
                for kw in keywords:
                    kw_lower = kw.lower()
                    df["match_score"] += df["name"].str.lower().str.contains(kw_lower).astype(int)
                    df["match_score"] += df["description"].str.lower().str.contains(kw_lower).astype(int)
                    df["match_score"] += df["ingredients"].apply(lambda lst: any(kw_lower in ing.lower() for ing in json.loads(lst))).astype(int)
            df = df.sort_values("match_score", ascending=False)

        return df.head(10)

    def log_conversation(self, user_message: str, bot_response: str, score: int, recs, session_id: str):
        try:
            self.conn.execute("""
                INSERT INTO conversations (timestamp, user_message, bot_response, interest_score, recommended_products, session_id)
                VALUES (?,?,?,?,?,?)
            """, (datetime.now().isoformat(), user_message, bot_response, int(score),
                  json.dumps(recs if recs is not None else []), session_id))
            self.conn.commit()
        except Exception as e:
            print("log_conversation error:", e)

# =========================================================
# Product generator
# =========================================================
def generate_products() -> List[Dict]:
    categories = {
        "Burgers": ["Spicy Fusion Dragon Burger", "Classic All-American Burger", "Plant-Based Beyond Burger", "BBQ Bacon Cheeseburger"],
        "Pizza": ["Margherita Classica", "Meat Lovers Supreme", "BBQ Chicken Pineapple", "Vegan Mediterranean"],
        "Fried Chicken": ["Nashville Hot Wings", "Honey Garlic Tenders", "Korean Fried Chicken", "Classic Fried Chicken"],
        "Tacos & Wraps": ["Korean Beef Taco", "Crispy Fish Taco", "Buffalo Chicken Wrap", "Veggie Hummus Wrap"],
        "Desserts": ["Chocolate Cake Slice", "Ice Cream Sundae", "Mini Cheesecake", "Brownie"]
    }

    products = []
    pid = 1
    for cat, names in categories.items():
        for name in names:
            product = {
                "product_id": f"FF{pid:03d}",
                "name": name,
                "category": cat,
                "description": f"{name} — a delicious {cat.lower()} option.",
                "ingredients": ["main ingredient", "seasoning", "garnish"],
                "price": round(random.uniform(5.0, 24.99), 2),
                "calories": random.randint(150, 900),
                "prep_time": f"{random.randint(5, 18)} mins",
                "dietary_tags": random.sample(["spicy", "vegan", "gluten-free", "classic", "gourmet"], k=2),
                "mood_tags": random.sample(["comfort", "adventurous", "healthy", "indulgent"], k=2),
                "allergens": random.sample(["gluten", "dairy", "soy", "nuts"], k=1),
                "popularity_score": random.randint(60, 100),
                "chef_special": random.choice([True, False]),
                "limited_time": random.choice([True, False]),
                "spice_level": random.randint(0, 10),
                "image_prompt": f"photo of {name.lower()}"
            }
            products.append(product)
            pid += 1
    return products

# =========================================================
# Interest Score Calculator
# =========================================================
def calculate_interest(user_input: str) -> int:
    score = 0
    if not user_input:
        return 0
    text = user_input.lower()

    if re.search(r"(spicy|vegan|cheese|burger|pizza|taco|wrap|salad)", text):
        score += 15
    if "vegetarian" in text or "vegan" in text:
        score += 10
    if "$" in text or re.search(r"\bunder\b|\bbelow\b", text):
        score += 5
    if re.search(r"(happy|adventurous|tired|sad|hungry|indulgent)", text):
        score += 20
    if "?" in text:
        score += 10
    if re.search(r"(love|perfect|amazing|great|yum|yummy)", text):
        score += 8
    if "how much" in text or "price" in text or re.search(r"\$\d+", text):
        score += 25
    if re.search(r"(order|add to cart|take it|i'll take it|i will take it|buy)", text):
        score += 30

    if re.search(r"\bmaybe\b|\bnot sure\b", text):
        score -= 10
    if "too expensive" in text or "expensive" in text:
        score -= 15
    if re.search(r"\bdon'?t like\b|\bnot for me\b|\bhate\b", text):
        score -= 25

    return max(0, min(100, score))

# =========================================================
# Streamlit App
# =========================================================
st.set_page_config(page_title="🍔 FoodieBot", layout="wide")
st.title("🍔 FoodieBot - Conversational Fast Food Recommender")
st.info("👋 Welcome! Tell me what kind of food you're craving (e.g., 'spicy burger under $10').")

# Session state
if "session_id" not in st.session_state:
    st.session_state.session_id = f"SID{random.randint(1000,9999)}"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Initialize DB
db = None
db_status = {"ok": False, "inserted": 0, "error": None}
try:
    db = FoodieBotDatabase()
    products = generate_products()
    pop_res = db.populate_products_safe(products)
    if pop_res.get("success"):
        db_status["ok"] = True
        db_status["inserted"] = pop_res.get("inserted", 0)
except Exception as e:
    db_status["error"] = str(e)
    db = None

# Fallback DF
FALLBACK_PRODUCTS_DF = pd.DataFrame([p for p in products]) if db is None else None

# -----------------------
# Input box & recommendation
# -----------------------
user_input = st.text_input("What are you craving today?")
if user_input:
    score = calculate_interest(user_input)
    keywords = [kw for kw in re.findall(r"\w+", user_input.lower()) if kw not in {"i","want","some","a","an","the","please","order"}]

    # Mood & Category detection
    mood = None
    category = None
    if "burger" in user_input.lower():
        category = "Burgers"
    elif "pizza" in user_input.lower():
        category = "Pizza"
    elif "chicken" in user_input.lower():
        category = "Fried Chicken"

    if "spicy" in user_input.lower():
        mood = "spicy"

    # Budget detection
    budget_match = re.search(r"under\s*\$?(\d+)", user_input.lower())
    budget = float(budget_match.group(1)) if budget_match else None

    # Recommendation (DB or fallback)
    if db:
        recs = db.recommend_products(mood=mood, budget=budget, category=category, keywords=keywords)
    else:
        df = FALLBACK_PRODUCTS_DF.copy()
        df["match_score"] = df["popularity_score"].copy()
        if mood:
            df["match_score"] += df["mood_tags"].apply(lambda tags: 1 if mood in tags else 0)
        if category:
            df["match_score"] += df["category"].str.lower().str.contains(category.lower()).astype(int)
        for kw in keywords:
            df["match_score"] += df["name"].str.lower().str.contains(kw).astype(int)
            df["match_score"] += df["description"].str.lower().str.contains(kw).astype(int)
            df["match_score"] += df["ingredients"].apply(lambda lst: any(kw in ing.lower() for ing in lst)).astype(int)
        df = df.sort_values("match_score", ascending=False)
        recs = df.head(10)

    bot_msg = f"I found {len(recs)} good matches for you!" if not recs.empty else "Hmm, I couldn’t find a perfect match. Try rephrasing."
    st.session_state.chat_history.append((user_input, bot_msg, score, recs))

    if db:
        db.log_conversation(user_input, bot_msg, score, recs.to_dict(orient="records"), st.session_state.session_id)

# -----------------------
# Chat history display
# -----------------------
st.subheader("Chat History")
if not st.session_state.chat_history:
    st.info("No conversations yet. Type a message in the input box to begin.")
else:
    for u, b, s, r in st.session_state.chat_history[::-1]:
        st.markdown(f"**You:** {u}")
        st.markdown(f"**FoodieBot:** {b}  —  **Interest Score:** {s}%")
        if isinstance(r, pd.DataFrame) and not r.empty:
            for _, row in r.head(5).iterrows():
                st.markdown(f"- **{row['name']}** — ${row['price']}  \n  {row['description']}")
        st.markdown("---")

# -----------------------
# Analytics
# -----------------------
if st.session_state.chat_history:
    st.subheader("📊 Analytics")
    scores = [c[2] for c in st.session_state.chat_history]
    fig = px.line(x=list(range(1, len(scores)+1)), y=scores, title="Interest Score Progression", markers=True)
    fig.update_layout(xaxis_title="Message #", yaxis_title="Interest Score (%)")
    st.plotly_chart(fig, use_container_width=True)

# -----------------------
# Sidebar
# -----------------------
with st.sidebar:
    st.header("FoodieBot Controls")
    st.write(f"Session ID: {st.session_state.session_id}")
    if db and db_status.get("ok"):
        st.success("Database: connected")
        st.write(f"Inserted products: {db_status.get('inserted')}")
        if st.button("Show sample products (DB)"):
            sample = db.recommend_products()
            st.dataframe(sample.head(10))
    else:
        st.warning("Database: unavailable (using fallback)")
        if st.button("Show fallback products"):
            st.dataframe(FALLBACK_PRODUCTS_DF.head(20))

st.caption("⚡ Powered by FoodieBot — local demo")
