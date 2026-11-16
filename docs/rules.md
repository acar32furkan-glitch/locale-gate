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

### Sözlük yapılandırma bulguları (`glossary lint`)

Yukarıdaki iki kod kataloğu denetler; `glossary lint` ise **sözlüğün kendisini** denetler. Ayrı bir
komut olmasının nedeni: bozuk kayıt katalogda bulgu gibi görünür, oysa hata sözlüktedir — düzeltme
yerini göstermeden yapılan her ayar katalog metnini gereksiz yere değiştirir.

| Kod | Koşul | Kural motorundaki gerçek sonucu |
|-----|-------|----------------------------------|
| `SOZLUK_HEDEF_BOS` | `target: ""` (boş metin) | Desen yalnızca boş metne uyar; terimi içeren her segment `TERM_EKSIK` alır |
| `SOZLUK_KAYNAK_BOS` | `source` boş ya da yalnızca boşluk | Desen hiçbir segmentle eşleşmez — kayıt ölü ağırlıktır |
| `SOZLUK_YINELENEN` | İki kayıt aynı kaynak desenini tanımlıyor | Aynı segment iki kez denetlenir, bulgu sayısı çiftlenir |
| `SOZLUK_CELISKILI_HEDEF` | Aynı kaynak, iki farklı `target` | Her iki doğru çeviri de en az bir `TERM_EKSIK` alır (ölçüldü: iki yön de düşer) |
| `SOZLUK_YASAK_HEDEFLE_CAKISIYOR` | Yasaklı varyant zorunlu karşılığın içinde geçiyor | Sözlüğe uyan çeviri `TERM_YASAK` alır — kural kendisiyle çelişir |
| `SOZLUK_YASAK_BOS` | `forbidden` listesinde boş metin | Aranan desen anlamsız; sonuç öngörülemez |
| `SOZLUK_YASAK_TEKRAR` | Aynı varyant listede iki kez (büyük/küçük harf farkı dahil) | Tek segment için iki `TERM_YASAK` bulgusu |

- **Yinelenen kayıt, kural motorunun kendi eşlemesiyle bulunur**, elle `lower()` ile değil:
  “Kargo Ücreti” ile “kargo ücreti” aynı kayıttır (kapı zaten harfe duyarsız eşler), ama biri
  `case_sensitive: true` ise ayrı metinleri yakaladıkları için yinelenen sayılmaz.
- `target: null` (alanın yokluğu) bulgu değildir: kısa biçim yalnızca yasaklı varyant denetimi bırakır.
- Çıkış kodları: `0` temiz · `1` yapılandırma bulgusu var · `2` dosya okunamadı/geçersiz.
- Kasıtlı hatalı örnek: `examples/data/glossary-hatali.yaml` (3 bulgu üretir, testle sabitlenmiştir).

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

Bu değerler bir başlangıçtır; gerçek katalogda bulgu borcuna göre kalibre edilmeleri gerekir —
adım adım yöntem ve ölçülmüş örnek: [kalibrasyon.md](kalibrasyon.md).
