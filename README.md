# Tier List Maker

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

## Yeni sürüm yayınlama

Bir etiket (tag) oluşturup GitHub'a gönderince `.exe` otomatik derlenir ve Releases'e eklenir:

```
git tag v1.0.2
git push origin v1.0.2
```
