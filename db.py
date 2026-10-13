"""Base de données, fichiers images / QR et configuration."""
import os
import json
import shutil
import sqlite3
import uuid
from datetime import datetime

import qrcode
from PIL import Image

APP_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "StockQR")
IMG_DIR = os.path.join(APP_DIR, "images")
QR_DIR = os.path.join(APP_DIR, "qr")
DB_PATH = os.path.join(APP_DIR, "stock.db")
CONFIG_PATH = os.path.join(APP_DIR, "config.json")

for _d in (APP_DIR, IMG_DIR, QR_DIR):
    os.makedirs(_d, exist_ok=True)


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                price REAL NOT NULL DEFAULT 0,
                quantity INTEGER NOT NULL DEFAULT 0,
                image_path TEXT,
                qr_path TEXT,
                fb_post_id TEXT,
                created_at TEXT
            )"""
        )


# ---------- Config ----------
def load_config():
    cfg = {"currency": "FCFA", "fb_page_id": "", "fb_token": ""}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ---------- QR ----------
def new_code():
    return "STK-" + uuid.uuid4().hex[:8].upper()


def qr_image(code):
    """Retourne une image PIL du QR code."""
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(code)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


# ---------- Produits ----------
def add_product(code, name, price, quantity, description, source_image):
    img = Image.open(source_image).convert("RGB")
    img.thumbnail((1280, 1280))
    image_path = os.path.join(IMG_DIR, f"{code}.jpg")
    img.save(image_path, "JPEG", quality=88)

    qr_path = os.path.join(QR_DIR, f"{code}.png")
    qr_image(code).save(qr_path)

    with _conn() as c:
        c.execute(
            """INSERT INTO products
               (code,name,description,price,quantity,image_path,qr_path,created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (code, name, description, price, quantity, image_path, qr_path,
             datetime.now().isoformat(timespec="seconds")),
        )


def list_products():
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM products ORDER BY id DESC")]


def update_product(pid, name, price, quantity, description):
    with _conn() as c:
        c.execute(
            "UPDATE products SET name=?, price=?, quantity=?, description=? WHERE id=?",
            (name, price, quantity, description, pid),
        )


def sell_one(pid):
    with _conn() as c:
        c.execute(
            "UPDATE products SET quantity = quantity - 1 WHERE id=? AND quantity > 0", (pid,)
        )


def set_fb_post(pid, post_id):
    with _conn() as c:
        c.execute("UPDATE products SET fb_post_id=? WHERE id=?", (post_id, pid))


def delete_product(pid):
    with _conn() as c:
        row = c.execute("SELECT image_path, qr_path FROM products WHERE id=?", (pid,)).fetchone()
        c.execute("DELETE FROM products WHERE id=?", (pid,))
    if row:
        for p in (row["image_path"], row["qr_path"]):
            try:
                os.remove(p)
            except Exception:
                pass
