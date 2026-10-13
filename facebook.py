"""Publication d'un produit sur une page Facebook (Graph API)."""
import requests

GRAPH = "https://graph.facebook.com/v21.0"


def build_caption(p, currency):
    price = f"{p['price']:,.0f}".replace(",", " ")
    lines = [
        p["name"],
        f"💰 Prix : {price} {currency}",
        f"📦 Quantité disponible : {p['quantity']}",
        f"🔖 Réf : {p['code']}",
    ]
    if p.get("description"):
        lines.append("")
        lines.append(p["description"])
    lines.append("")
    lines.append("📩 Contactez-nous pour commander !")
    return "\n".join(lines)


def post_product(p, cfg):
    page_id, token = cfg.get("fb_page_id", "").strip(), cfg.get("fb_token", "").strip()
    if not page_id or not token:
        raise RuntimeError("Configurez l'ID de la page et le jeton d'accès Facebook dans Paramètres.")
    with open(p["image_path"], "rb") as f:
        r = requests.post(
            f"{GRAPH}/{page_id}/photos",
            data={"caption": build_caption(p, cfg.get("currency", "")), "access_token": token},
            files={"source": f},
            timeout=120,
        )
    try:
        data = r.json()
    except Exception:
        raise RuntimeError(f"Réponse invalide de Facebook ({r.status_code}).")
    if "error" in data:
        raise RuntimeError(data["error"].get("message", "Erreur Facebook"))
    return data.get("post_id") or data.get("id")
