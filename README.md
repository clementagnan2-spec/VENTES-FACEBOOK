# StockQR – Stock avec QR code + vente Facebook

**Fonctionnement**
1. **📷 Prendre une photo** (webcam) ou **📁 Importer une image** d'un produit.
2. Le logiciel génère immédiatement une fiche stock avec un **code QR unique** (STK-XXXXXXXX).
3. Vous saisissez **nom, prix, quantité** → *Enregistrer*.
4. Le produit apparaît sur la **page d'accueil** (vitrine). Boutons : QR (enregistrer l'étiquette), ✏ modifier, *Vendu -1*, 🗑 supprimer.
5. **📘 Publier sur Facebook** envoie photo + prix + quantité sur votre Page.

Les données sont dans `%APPDATA%\StockQR` (base SQLite, images, QR).

## Obtenir le .exe via GitHub
1. Créez un dépôt GitHub et envoyez-y tous ces fichiers (y compris le dossier `.github`).
2. Onglet **Actions** → *Build Windows EXE* → le build démarre (ou *Run workflow*).
3. Une fois terminé, téléchargez **StockQR-windows** dans *Artifacts* → `StockQR.exe`.
4. Pour une Release téléchargeable : `git tag v1.0 && git push --tags`.

## Configurer Facebook
1. https://developers.facebook.com → créez une App (type *Business*).
2. Dans l'*Explorateur de l'API Graph*, générez un jeton avec les permissions
   `pages_manage_posts`, `pages_read_engagement`, `pages_show_list`.
3. Obtenez le **jeton de Page** (`GET /me/accounts`) et l'**ID de la Page**.
4. Collez-les dans **⚙ Paramètres** (utilisez un jeton longue durée).

> Pour publier sur une page dont vous êtes administrateur, l'app peut rester en mode développement.

## Lancer en local
```
pip install -r requirements.txt
python main.py
```
