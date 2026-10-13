"""StockQR - Stock + codes QR + vente Facebook."""
import os
import shutil
import tempfile
import threading
import uuid
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

import db
import facebook

COLS = 4
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


def fmt_price(v, cur):
    return f"{v:,.0f}".replace(",", " ") + f" {cur}"


def ctk_img(pil, size):
    pil = pil.copy()
    pil.thumbnail(size)
    return ctk.CTkImage(light_image=pil, size=pil.size)


# ---------------------------------------------------------------- Caméra
class CameraWindow(ctk.CTkToplevel):
    def __init__(self, master, on_capture):
        super().__init__(master)
        import cv2
        self.cv2 = cv2
        self.title("Prendre une photo")
        self.geometry("700x600")
        self.on_capture = on_capture
        self.frame = None
        self.after_id = None
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.label = ctk.CTkLabel(self, text="Ouverture de la caméra...")
        self.label.pack(padx=10, pady=10, expand=True)
        ctk.CTkButton(self, text="📸 Capturer", height=40, command=self.capture).pack(pady=10)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(100, self.lift)
        self.update_frame()

    def update_frame(self):
        if not self.cap or not self.cap.isOpened():
            self.label.configure(text="Caméra introuvable.\nUtilisez « Importer une image ».")
            return
        ok, frame = self.cap.read()
        if ok:
            self.frame = frame
            rgb = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB)
            self.photo = ctk_img(Image.fromarray(rgb), (660, 480))
            self.label.configure(image=self.photo, text="")
        self.after_id = self.after(30, self.update_frame)

    def capture(self):
        if self.frame is None:
            return
        path = os.path.join(tempfile.gettempdir(), f"cap_{uuid.uuid4().hex[:8]}.jpg")
        self.cv2.imwrite(path, self.frame)
        self.close()
        self.on_capture(path)

    def close(self):
        if self.after_id:
            self.after_cancel(self.after_id)
        if self.cap:
            self.cap.release()
        self.destroy()


# ---------------------------------------------------------------- Fiche produit
class ProductDialog(ctk.CTkToplevel):
    """Création (image_path fourni) ou modification (product fourni)."""

    def __init__(self, master, on_saved, image_path=None, product=None):
        super().__init__(master)
        self.on_saved, self.image_path, self.product = on_saved, image_path, product
        self.title("Modifier le produit" if product else "Nouveau produit en stock")
        self.geometry("760x520")
        self.resizable(False, False)
        self.code = product["code"] if product else db.new_code()

        left = ctk.CTkFrame(self)
        left.pack(side="left", padx=15, pady=15, fill="y")
        src = Image.open(product["image_path"] if product else image_path)
        self.img_ref = ctk_img(src, (300, 300))
        ctk.CTkLabel(left, image=self.img_ref, text="").pack(padx=10, pady=10)
        self.qr_ref = ctk_img(db.qr_image(self.code), (140, 140))
        ctk.CTkLabel(left, image=self.qr_ref, text="").pack()
        ctk.CTkLabel(left, text=f"Code : {self.code}", font=("Arial", 12, "bold")).pack(pady=4)

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True, padx=10, pady=15)
        cur = master.cfg.get("currency", "")
        self.e_name = self._field(right, "Nom du produit", product["name"] if product else "")
        self.e_price = self._field(right, f"Prix ({cur})", str(int(product["price"]) if product and product["price"] == int(product["price"]) else (product["price"] if product else "")))
        self.e_qty = self._field(right, "Quantité en stock", str(product["quantity"]) if product else "1")
        ctk.CTkLabel(right, text="Description (optionnelle)", anchor="w").pack(fill="x")
        self.t_desc = ctk.CTkTextbox(right, height=90)
        self.t_desc.pack(fill="x", pady=(0, 12))
        if product:
            self.t_desc.insert("1.0", product.get("description") or "")
        ctk.CTkButton(right, text="💾 Enregistrer en stock", height=40, command=self.save).pack(fill="x", pady=4)
        ctk.CTkButton(right, text="Annuler", fg_color="gray", height=32, command=self.destroy).pack(fill="x")
        self.after(150, self.lift)
        self.e_name.focus()

    def _field(self, parent, label, value):
        ctk.CTkLabel(parent, text=label, anchor="w").pack(fill="x")
        e = ctk.CTkEntry(parent, height=34)
        e.insert(0, value)
        e.pack(fill="x", pady=(0, 12))
        return e

    def save(self):
        name = self.e_name.get().strip()
        try:
            price = float(self.e_price.get().replace(" ", "").replace(",", "."))
            qty = int(self.e_qty.get().strip())
            if price < 0 or qty < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erreur", "Prix et quantité doivent être des nombres positifs.", parent=self)
            return
        if not name:
            messagebox.showerror("Erreur", "Le nom est obligatoire.", parent=self)
            return
        desc = self.t_desc.get("1.0", "end").strip()
        if self.product:
            db.update_product(self.product["id"], name, price, qty, desc)
        else:
            db.add_product(self.code, name, price, qty, desc, self.image_path)
        self.on_saved()
        self.destroy()


# ---------------------------------------------------------------- Fenêtre QR
class QRWindow(ctk.CTkToplevel):
    def __init__(self, master, product):
        super().__init__(master)
        self.title(f"QR - {product['name']}")
        self.product = product
        self.img = ctk_img(Image.open(product["qr_path"]), (320, 320))
        ctk.CTkLabel(self, image=self.img, text="").pack(padx=20, pady=15)
        ctk.CTkLabel(self, text=product["code"], font=("Arial", 14, "bold")).pack()
        ctk.CTkButton(self, text="Enregistrer l'étiquette QR", command=self.export).pack(pady=15)
        self.after(150, self.lift)

    def export(self):
        dest = filedialog.asksaveasfilename(
            defaultextension=".png", initialfile=f"{self.product['code']}.png",
            filetypes=[("PNG", "*.png")], parent=self)
        if dest:
            shutil.copy(self.product["qr_path"], dest)


# ---------------------------------------------------------------- Paramètres
class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.app = master
        self.title("Paramètres")
        self.geometry("520x420")
        cfg = master.cfg
        self.e_cur = self._f("Devise (ex : FCFA, €, $)", cfg["currency"])
        self.e_page = self._f("Facebook - ID de la Page", cfg["fb_page_id"])
        self.e_tok = self._f("Facebook - Jeton d'accès de la Page", cfg["fb_token"], show="•")
        ctk.CTkLabel(self, text="Voir README pour obtenir l'ID et le jeton.",
                     text_color="gray").pack(pady=4)
        ctk.CTkButton(self, text="Enregistrer", command=self.save).pack(pady=15)
        self.after(150, self.lift)

    def _f(self, label, value, show=None):
        ctk.CTkLabel(self, text=label, anchor="w").pack(fill="x", padx=20, pady=(14, 0))
        e = ctk.CTkEntry(self, show=show)
        e.insert(0, value)
        e.pack(fill="x", padx=20)
        return e

    def save(self):
        self.app.cfg.update(currency=self.e_cur.get().strip() or "FCFA",
                            fb_page_id=self.e_page.get().strip(),
                            fb_token=self.e_tok.get().strip())
        db.save_config(self.app.cfg)
        self.app.refresh()
        self.destroy()


# ---------------------------------------------------------------- Application
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        db.init_db()
        self.cfg = db.load_config()
        self.title("StockQR - Stock & Vente")
        self.geometry("1200x780")

        bar = ctk.CTkFrame(self)
        bar.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(bar, text="📷 Prendre une photo", height=40, command=self.open_camera).pack(side="left", padx=5)
        ctk.CTkButton(bar, text="📁 Importer une image", height=40, command=self.import_image).pack(side="left", padx=5)
        ctk.CTkButton(bar, text="⚙ Paramètres", height=40, fg_color="gray", command=lambda: SettingsWindow(self)).pack(side="right", padx=5)
        self.search = ctk.CTkEntry(bar, placeholder_text="🔍 Rechercher (nom ou code)", width=260, height=40)
        self.search.pack(side="right", padx=5)
        self.search.bind("<KeyRelease>", lambda e: self.refresh())

        self.info = ctk.CTkLabel(self, text="", anchor="w")
        self.info.pack(fill="x", padx=16)
        self.grid_frame = ctk.CTkScrollableFrame(self)
        self.grid_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.refresh()

    # --- ajout
    def open_camera(self):
        CameraWindow(self, self.new_product)

    def import_image(self):
        path = filedialog.askopenfilename(
            title="Choisir une image",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.bmp")])
        if path:
            self.new_product(path)

    def new_product(self, image_path):
        ProductDialog(self, self.refresh, image_path=image_path)

    # --- affichage
    def refresh(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()
        q = self.search.get().strip().lower()
        items = [p for p in db.list_products() if q in p["name"].lower() or q in p["code"].lower()]
        total_qty = sum(p["quantity"] for p in items)
        self.info.configure(text=f"{len(items)} produit(s) • {total_qty} unité(s) en stock")
        if not items:
            ctk.CTkLabel(self.grid_frame, text="Aucun produit.\nPrenez une photo ou importez une image pour commencer.",
                         font=("Arial", 16), text_color="gray").grid(row=0, column=0, padx=40, pady=80)
        for i, p in enumerate(items):
            self.card(p).grid(row=i // COLS, column=i % COLS, padx=8, pady=8, sticky="n")

    def card(self, p):
        cur = self.cfg["currency"]
        f = ctk.CTkFrame(self.grid_frame, width=250, corner_radius=12)
        try:
            im = ctk_img(Image.open(p["image_path"]), (230, 190))
            lbl = ctk.CTkLabel(f, image=im, text="")
            lbl.image = im
            lbl.pack(padx=8, pady=(8, 4))
        except Exception:
            ctk.CTkLabel(f, text="(image manquante)").pack(pady=40)
        ctk.CTkLabel(f, text=p["name"], font=("Arial", 15, "bold"), wraplength=220).pack()
        ctk.CTkLabel(f, text=fmt_price(p["price"], cur), font=("Arial", 14), text_color="#1a7f37").pack()
        if p["quantity"] > 0:
            ctk.CTkLabel(f, text=f"Stock : {p['quantity']}").pack()
        else:
            ctk.CTkLabel(f, text="ÉPUISÉ", text_color="red", font=("Arial", 13, "bold")).pack()
        ctk.CTkLabel(f, text=p["code"] + ("  • ✔ publié" if p["fb_post_id"] else ""),
                     text_color="gray", font=("Arial", 11)).pack()
        r1 = ctk.CTkFrame(f, fg_color="transparent")
        r1.pack(pady=(6, 2))
        ctk.CTkButton(r1, text="QR", width=50, command=lambda: QRWindow(self, p)).pack(side="left", padx=2)
        ctk.CTkButton(r1, text="✏", width=40, command=lambda: ProductDialog(self, self.refresh, product=p)).pack(side="left", padx=2)
        ctk.CTkButton(r1, text="Vendu -1", width=70, fg_color="#e08a00", command=lambda: self.sell(p)).pack(side="left", padx=2)
        ctk.CTkButton(r1, text="🗑", width=40, fg_color="#c0392b", command=lambda: self.delete(p)).pack(side="left", padx=2)
        ctk.CTkButton(f, text="📘 Publier sur Facebook", fg_color="#1877f2",
                      command=lambda: self.publish(p)).pack(padx=8, pady=(2, 10), fill="x")
        return f

    # --- actions
    def sell(self, p):
        db.sell_one(p["id"])
        self.refresh()

    def delete(self, p):
        if messagebox.askyesno("Supprimer", f"Supprimer « {p['name']} » du stock ?"):
            db.delete_product(p["id"])
            self.refresh()

    def publish(self, p):
        if p["fb_post_id"] and not messagebox.askyesno("Déjà publié", "Ce produit est déjà publié. Publier à nouveau ?"):
            return
        self.info.configure(text="Publication sur Facebook en cours...")

        def work():
            try:
                post_id = facebook.post_product(p, self.cfg)
                db.set_fb_post(p["id"], post_id)
                self.after(0, lambda: (self.refresh(), messagebox.showinfo("Facebook", "Produit publié sur votre page !")))
            except Exception as e:
                self.after(0, lambda: (self.refresh(), messagebox.showerror("Facebook", str(e))))

        threading.Thread(target=work, daemon=True).start()


if __name__ == "__main__":
    App().mainloop()
