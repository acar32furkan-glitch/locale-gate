# Yol Haritası

Her sürüm tek bir soruya cevap verir. Deterministik çekirdek (ADR-0001) her sürümde korunur.

## v0.1.0 — Çalışan kapı (bu sürüm)
- Dört kural: sözlük uyumu, korunan ifadeler, Türkçe yazım, uzunluk bütçesi.
- `tr→en` ve `en→tr` yönleri; JSON ve CSV katalog; TOML/JSON yapılandırma.
- `check` / `eval` / `rules` komutları, JSON sözleşmesi, GitHub Actions iş özeti.
- Altın set (3 vaka) ve 119 test; determinizm sözleşmesi testlerle sabitlendi.

## v0.2.0 — Ekip iş akışı
- `locale-gate diff` — iki katalog sürümü arasındaki **yeni** bulguları gösterir ("bu PR hangi
  hatayı getirdi?" sorusunun cevabı, CI'da yorum olarak).
- `--baseline report.json` — önceki raporu taban alıp yalnızca regresyonu bildirir (mevcut bulgu
  borcu PR'ı kırmaz).
- Sözlük dosyası için şema doğrulama komutu (`glossary lint`) ve yinelenen terim uyarısı.

## v0.3.0 — Kapsam genişletme
- `de→en` gibi üçüncü dil çifti için kural iskeleti (`rules/locale_profile.py`: dil başına sayı
  biçimi, büyük harf ve diakritik politikası veri olarak).
- Marka/koruma listesi (özel adlar, ürün kodları) ve "çevrilmeyecek kelimeler" sözlüğü.
- HTML/PDF rapor çıktısı (içerik ekibinin okuyacağı biçim).

## v0.4.0 — Opsiyonel LLM hakem (deterministik çekirdeğin üstünde)
- `--judge` bayrağı: akıcılık/anlam için modelden **ikincil** sinyal; skor formülüne yalnızca
  yapılandırılmış bir ağırlıkla girer ve kapı kararını tek başına veremez.
- Çıktıda "deterministik skor" ve "hakem skoru" ayrı ayrı gösterilir; hakem hata verirse kapı
  deterministik sonuca düşer.

## Kapsam dışı (bilinçli)
- Çeviri **yapmak** (bu araç denetler, üretmez).
- Pazaryeri paneline bağlanmak veya metni otomatik düzeltmek.
- Anlam denetimini tek başına üstlenmek: mekanik hatalar kapının işi, yaratıcı kalite insan işi.
