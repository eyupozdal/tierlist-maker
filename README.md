# Tier List Maker (Türkçe)

[English Below] #english

S'den F'ye tier listeleri oluşturan masaüstü uygulaması.

- Her tier satırının adı değiştirilebilir (ör. "S" yerine "En iyisi")
- Görselleri sürükleyip bırakarak tier'lara yerleştir, satır içinde sıra değiştir
- Renkli etiketler (yalnızca uygulamada görünür) ve liste adı / etiket araması
- Listeleri kaydet, düzenle, sil
- Tier tahtasını JPG olarak indir (etiketler JPG'ye eklenmez)

## Windows'a kurulum

1. Bu sayfanın sağındaki **Releases** bölümünden en son sürümü aç.
2. **TierListMaker.exe** dosyasını indir ve çalıştır.

Windows "PC'nizi korudu" (SmartScreen) uyarısı gösterirse **Ek bilgi → Yine de çalıştır** seçeneğini kullan. Uygulama imzalı olmadığı için bu uyarı normaldir.

Listeler `%APPDATA%\TierListMaker` klasöründe saklanır.

## Kaynak koddan çalıştırma

```
pip install -r requirements.txt
python tierlist_maker.py
```


# English

A desktop application that creates tier lists from S to F.

- You can rename each tier row (e.g., “Best” instead of “S”)
- Drag and drop images into tiers; reorder them within a row
- Color-coded labels (visible only in the app) and list name/label search
- Save, edit, and delete lists
- Download the tier board as a JPG (labels are not included in the JPG)

## Installation on Windows

1. Open the latest version from the **Releases** section on the right side of this page.
2. Download and run the **TierListMaker.exe** file.

If Windows displays a “Your PC is protected” (SmartScreen) warning, select **More info → Run anyway**. This warning is normal because the application is not signed.

The lists are stored in the `%APPDATA%\TierListMaker` folder.

## Running from Source Code

```
pip install -r requirements.txt
python tierlist_maker.py
```


