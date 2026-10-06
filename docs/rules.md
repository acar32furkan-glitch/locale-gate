# Kural Sözlüğü

Kapı dört kuralı çalıştırır. Her kural **kendi kapsamını** bildirir (`checked`), skor kapsam
üzerinden hesaplanır ve bir kural kapsamı sıfırsa (denetlenecek veri yoksa) skora girmez.

## 1. Sözlük uyumu (`terminology`)

| Kod | Koşul | Önem |
|-----|-------|------|
| `TERM_EKSIK` | Kaynak metinde sözlük terimi geçiyor ama hedef metinde zorunlu karşılığı yok | KRİTİK |
| `TERM_YASAK` | Kaynak metinde sözlük terimi geçiyor ve hedef metin yasaklı bir varyantı kullanıyor | UYARI |

- Kapsam: yalnızca sözlükteki bir terimi **içeren** segmentler (segmentin konusu olmayan terim için
  yanlış alarm üretilmez).
- Kelime sınırı Türkçe harfleri tanır: `beden` eşleşir, `bedenler` eşleşmez; `%100 pamuk` gibi
  sembolle başlayan terimler de doğru eşleşir (`re.compile` `\b` yerine açık lookaround kullanır).

## 2. Korunan ifadeler (`tokens`)

| Kod | Koşul | Önem |
|-----|-------|------|
| `TOKEN_KAYIP` | Yer tutucu (`{order_id}`, `%s`, `{{ name }}`, `${amount}`) veya HTML etiketi hedefte yok | KRİTİK |
| `TOKEN_KAYIP` | Bağlantı veya e-posta adresi hedefte yok | UYARI |
| `SAYI_KAYIP` | Kaynaktaki ölçü/model bilgisinin **rakam dizisi** hedefte geçmiyor (`45 x 30 x 12 cm`, `256 GB`, `B-2000`) | UYARI |
| `NUM_AYIRICI` | Türkçe hedefte ondalık ayırıcı nokta (`2.5 kg`) veya binlik ayırıcı virgül (`1,234.56 TL`) | BİLGİ |
| `YUZDE_KONUM` | Türkçe hedefte yüzde işareti sayıdan sonra (`20% indirim`) | BİLGİ |

- Sayı karşılaştırması **rakam dizisi** üzerinden yapılır: `2,5 kg → 2.5 kg` geçerlidir (ayırıcı
  yerelleşir), `780 gram → 0.78 kg` kayıptır (rakam dizisi değişmiş).
- Kapsam: yer tutucu/ölçü içeren segmentler; Türkçe hedefli kataloglarda sayı biçimi denetimi her
  segmentte çalıştığı için kapsam tüm segmentlerdir.

## 3. Türkçe yazım (`turkish`)

| Kod | Koşul | Önem |
|-----|-------|------|
| `TR_DIAKRITIK` | Kaynakta doğru yazım var (`ürün`), hedefte ASCII karşılığı kullanılmış (`urun`) | UYARI |
| `TR_BUYUK_I` | Türkçe hedefte `I` ile yazılmış kelimenin `İ` olması gerekiyor (`ISTANBUL` → `İSTANBUL`) | UYARI |
| `CEVRILMEMIS` | Kaynak ve hedef birebir aynı ve metin Türkçe karakter içeriyor (segment çevrilmemiş) | KRİTİK |
| `TR_KARAKTER` | İngilizce hedefte Türkçe karakter var (çevrilmemiş kelime kalıntısı) | UYARI |

Tahmin yürütmeyen iki karar:

- **Diakritik kuralı** yalnızca kaynak metinde doğru yazım geçiyorsa uyarır; "doğru olan kelimeyi"
  hatalı sayma riski yoktur. ASCII karşılığı 5 harften uzunsa ek alabilir (`olculer` → `Olculeri`
  yakalanır, çünkü Türkçe eklemeli bir dildir); kısa ve tehlikeli karşılıklarda tam kelime aranır
  (`ısı` → `isi` kuralı `isim` kelimesini yakalamaz).
- **`i/İ` kuralı** kaynak kelime küçük harfle geçiyorsa (`istanbul`) kesin kuraldır; kaynak büyük
  harfle geçiyorsa (`Istanbul`) `i` mi `ı` mı olduğu anlaşılamaz ve yalnızca Türkçede kesin `i` ile
  yazılan özel adlar için uyarılır (`İstanbul` ✓, `Isparta` sessiz kalır).

## 4. Uzunluk bütçesi (`length`)

| Kod | Koşul | Önem |
|-----|-------|------|
| `LENGTH_SINIR` | Hedef metin alan sınırını aşıyor (`title` 70, `bullet` 140, `description` 2000) | UYARI |
| `LENGTH_UZAMA` | Hedef/kaynak uzunluk oranı `max_expansion` (varsayılan 1.60) üzerinde | UYARI |

- Segment kendi `limit` alanını getirirse o kullanılır, yoksa yapılandırmadaki alan sınırı geçerlidir.
- Uzama oranı yalnızca **25 karakterden uzun** kaynaklarda ölçülür: `Deri Cüzdan → Genuine Leather
  Wallet` gibi kısa segmentlerde oran gürültüdür ve yanlış alarm üretir.

## Skor ve karar

| Kavram | Formül |
|--------|--------|
| Kural başarısı | `1 - (etkilenen segment / kapsam)`; kapsam 0 ise 1.0 (skora girmez) |
| Genel skor | Ağırlıklı ortalama: `terminology 0.35 · tokens 0.35 · turkish 0.15 · length 0.15` |
| Karar | `skor ≥ gate` **ve** `kritik bulgu = 0` (ikincisi `fail_on_critical=false` ile kapatılabilir) |

Başarı oranı **etkilenen segment** üzerinden hesaplanır, bulgu sayısı üzerinden değil: tek bir
segmentteki üç bulgu kuralı üç kez cezalandırmaz ve skor negatife düşmez (`tests/test_gate.py`).

## Neden bu eşikler?

- **`title` 70 karakter:** Trendyol/Hepsiburada başlık alanlarının tipik kırpma noktası.
- **x1.60 uzama:** TR→EN çevirisinde beklenen uzama ~%20-30'dur; %60 üzeri genelde metne bilgi
  eklendiğini gösterir.
- **%70 indirim benzeri anomali yok:** bu kapı fiyat doğrulamaz, yalnızca metni denetler.
- **Kritik = mağazayı bozan hata:** yer tutucu kaybı (çalışma zamanı hatası), zorunlu sözlük
  karşılığının yokluğu (marka tutarsızlığı) ve çevrilmemiş segment (müşteri Türkçe metin görür).
