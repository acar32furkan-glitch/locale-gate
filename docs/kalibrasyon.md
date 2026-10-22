# Eşik Kalibrasyonu

Varsayılan `gate = 0.95` bir başlangıç değeridir, evrensel bir doğru değil. Gerçek bir katalog ilk
günden bu eşiğin altında olur; o zaman iki kötü seçenek var: kapıyı kapatmak (hiçbir PR geçmez) ya da
eşiği işe yaramaz hâle getirecek kadar düşürmek. Kalibrasyon üçüncü yol: **bugünkü bulgu borcunu ölç,
borcun hemen altında bir eşikle dondur, borç kapandıkça kademeli yükselt.**

Buradaki her sayı depodaki `examples/data/catalog.json` (12 segment, bilinçli olarak kirli örnek) ve
ondan türetilen aşamalar üzerinde gerçekten koşulmuş komutlardan geliyor. Yeniden üretme adımları §8'de.

## 1. Skorun yapısı: her düzeltme aynı ağırlıkta değil

Kapı skoru ağırlıklı ortalamadır ve ceza **etkilenen segment** üzerinden kesilir:

```text
skor = Σ (ağırlık_i × (1 − etkilenen_segment_i / kapsam_i)) / Σ ağırlık_i
       (yalnızca kapsamı > 0 olan kurallar toplama girer)
```

Bir segmentin skora maliyeti, o kuralın ağırlığının kapsamına bölümüdür. Örnek katalogda ölçülen
kapsamlar (`--json` → `stats[].checked`) ve tek segment cezaları:

| Kural | Ağırlık | Kapsam (bu katalog) | Tek segment cezası |
|-------|---------|---------------------|--------------------|
| `terminology` | 0.35 | 7 | **0.0500** |
| `tokens` | 0.35 | 3 | **0.1167** |
| `turkish` | 0.15 | 12 | **0.0125** |
| `length` | 0.15 | 12 | **0.0125** |

Kendi kataloğunuzda bu tabloyu `stats[].checked` ile yeniden hesaplayın: `ağırlık / kapsam`. Sonuç
kalibrasyonun en önemli sayısıdır — bir `tokens` düzeltmesi, bir diakritik düzeltmesinden **dokuz kat**
fazla skor taşır. Eşik adımı bu yüzden sabit olamaz.

Skor tekrarlanabilir: aynı girdi iki koşuda `generated_at` dışında birebir aynı raporu verir (ADR-0001).
Ölçüldü:

```console
$ diff <(grep -v generated_at r1.json) <(grep -v generated_at r2.json)   # iki ayrı koşu, 1 sn arayla
DETERMINISTIK: generated_at disinda fark yok
```

## 2. Adım 1 — Borç envanterini çıkar

```bash
uv run locale-gate check examples/data/catalog.json --glossary examples/data/glossary.yaml \
  --report kalibrasyon/baseline.json
```

Gerçek çıktı (kısaltıldı):

```text
  yön: tr → en  ·  segment: 12  ·  katalog: examples\data\catalog.json
  skor: 0.529 / eşik 0.950  ·  KRİTİK 5  ·  UYARI 7  ·  BİLGİ 0

KURAL BAŞARI ORANLARI
  Sözlük uyumu       42.9%   (6 bulgu, 4 segment etkilendi / 7 segment)
  Korunan ifadeler   33.3%   (2 bulgu / 3 segment)
  Türkçe yazım       83.3%   (3 bulgu, 2 segment etkilendi / 12 segment)
  Uzunluk bütçesi    91.7%   (1 bulgu / 12 segment)
```

JSON raporu bulguları koda göre sayar; kalibrasyon kararı bu tablodan verilir, bulgu listesinden değil:

| Kod | Adet | Önem | Anlamı |
|-----|------|------|--------|
| `TERM_EKSIK` | 3 | KRİTİK | Sözlük karşılığı hedefte yok |
| `TOKEN_KAYIP` | 1 | KRİTİK | `{order_id}` çeviride düşmüş |
| `CEVRILMEMIS` | 1 | KRİTİK | Segment hiç çevrilmemiş |
| `TERM_YASAK` | 3 | UYARI | Yasaklı varyant (`puffer coat`, `cargo fee`, `body`) |
| `SAYI_KAYIP` | 1 | UYARI | `780 gram` → `0.78 kg` |
| `LENGTH_SINIR` | 1 | UYARI | Başlık 78/70 karakter |
| `TR_DIAKRITIK` | 2 | UYARI | `Urun Ozellikleri` |

12 bulgu, 7 kod, 5 kritik. Kritik sayısı bulgu sayısından bağımsız okunur: iki kritik kod aynı
segmentte birleşebilir (`P-1006` hem `TERM_EKSIK` hem `TERM_YASAK`).

## 3. Adım 2 — Kritikleri eşikle satın alamazsınız

Eşiği sıfıra indirip "skor sorununu" kapatalım:

```console
$ uv run locale-gate check examples/data/catalog.json --glossary examples/data/glossary.yaml --fail-under 0.0
  skor: 0.529 / eşik 0.000  ·  KRİTİK 5  ·  UYARI 7  ·  BİLGİ 0
KARAR: KALDI ✘
  neden: 5 kritik bulgu var (fail_on_critical=true)
```

`fail_on_critical` açıkken skor eşiği tamamen devre dışı kalır. Yani kalibrasyonun sırası pazarlık
konusu değil: **önce kritik = 0, sonra eşik.** Eşiği kritikler dururken tartışmak boşa emektir.

## 4. Adım 3 — Kritikleri kapat, borcu dondur

Dört kritik segment düzeltildiğinde beş kritik bulgu kapanır (12 bulgu → 5); `P-1002` ve `P-1006`'daki
yasaklı varyantlar da aynı düzeltmeyle gider. Ölçülen durum:

```console
$ uv run locale-gate check <kopya>/asama-a.json --glossary examples/data/glossary.yaml
  skor: 0.808 / eşik 0.950  ·  KRİTİK 0  ·  UYARI 5  ·  BİLGİ 0
```

Artık borç yalnızca uyarı: 5 bulgu, 5 segment. Kapı bu hâliyle 0.95'te duramaz. Doğru eşik aralığı:

```text
skor − (en küçük tek segment cezası)  <  gate  ≤  skor
0.8083 − 0.0125 = 0.7958             <  gate  ≤  0.8083
```

Ölçülen sınırlar:

| Eşik | Karar | Neden |
|------|-------|-------|
| `--fail-under 0.80` | GEÇTİ ✔ | 0.8083 ≥ 0.800, marj 0.0083 (bir diakritik cezasından küçük) |
| `--fail-under 0.81` | KALDI ✘ | 0.8083 < 0.810 |
| `--fail-under 0.8083` | GEÇTİ ✔ | eşitlik geçer; ama görüntüde "0.808" yazar |
| `--fail-under 0.809` | KALDI ✘ | ekranda 0.808 görünse de gerçek skor 0.80833 |

Son iki satır rehberin en sık yapılan hatası: **konsoldaki üç haneli sayıyı eşik olarak yazmayın.**
Eşiği JSON'daki dört haneli `score` alanından veya §1'deki formülden alın.

Marjın üst sınırı da önemli: marj en küçük tek segment cezasından (burada 0.0125) küçük olmalı, yoksa
tek segmentlik gerçek bir gerileme eşiğin altında kalır ve kapı yeşil yanar.

Kalıcı eşik yapılandırmada durur, komut satırında değil:

```toml
# locale-gate.toml
gate = 0.80
fail_on_critical = true
```

`--fail-under` yalnızca deneme içindir; CI ile yerel koşu aynı sayıyı kullansın diye eşik dosyada
tutulur. (Konsol başlığı artık kararı veren eşiği gösterir; `--fail-under 0.80` verildiğinde satır
`eşik 0.800` yazar, yapılandırmadaki 0.950'yi değil.)

## 5. Adım 4 — Kademeli yükseltme: hangi düzeltme hangi sıçramayı yapar

Aynı katalogda dört aşama gerçekten koşuldu:

| Aşama | Yapılan | Skor | Kritik | Uyarı | Kazanç |
|-------|---------|------|--------|-------|--------|
| baseline | — | 0.5292 | 5 | 7 | — |
| A | 4 kritik segment | 0.8083 | 0 | 5 | +0.2791 |
| B | + `P-1010`: `body` → `size` | 0.8583 | 0 | 4 | +0.0500 |
| C | + `P-1003`: `0.78 kg` → `780 grams` | 0.9750 | 0 | 3 | +0.1167 |
| D | + `P-1008` başlık kısalt, `P-1009` çevir | 1.0000 | 0 | 0 | +0.0250 |

Sıçramalar §1'deki cezalarla birebir örtüşüyor: B tek `terminology` cezası (0.0500), C tek `tokens`
cezası (0.1167), D iki küçük ceza (0.0125 × 2). Formül ölçümle doğrulandığı için yükseltme takvimini
tahminle değil aritmetikle kurabilirsiniz.

Sıra kuralı: **önce kapsamı dar olan kural.** `tokens` 3 segmentte denetleniyor, bu yüzden aynı emekle
0.1167 taşıyor; diakritik temizliği 12 segmentte 0.0125 getiriyor. "Önce kolay olan" yanlış sezgidir.

## 6. Adım 5 — Nerede durulur

C aşaması varsayılan eşiği geçiyor: `skor 0.975 / eşik 0.950 → GEÇTİ ✔` — ama hâlâ 3 uyarı ve 2 kirli
segment var. Yani **yeşil kapı "temiz" demek değil**, "kabul edilebilir" demek. İki ayrı politika gerekir:

1. **Kapı (merge kararı):** kritik = 0 **ve** skor ≥ `gate`.
2. **Borç (haftalık hedef):** uyarı sayısı. Yukarıdaki koşuda 12 → 5 → 4 → 3 → 0.

Durma noktası olarak `gate = 0.95` + kritik 0 + uyarı 0 savunulabilir. Eşiği 1.0'a çekmek kırılgandır:
tek bir diakritik kaybı 0.0125 düşürür ve hiçbir PR geçemez; üstelik 0.95 ile 1.0 arasındaki fark
kural setinin değil, borcun sıfırlanmasının işidir.

## 7. Tuzak — skor bir orandır, sayı değil

Ölçüldü: aynı borç aynı katalogda 0.8083; kataloğa **hiçbir şey düzeltmeden** 24 temiz segment
eklendiğinde (`P-1001`'in kopyaları, benzersiz id'lerle) 36 segmentte skor **0.8637** oluyor. Buna
karşılık kataloğu borcuyla birlikte üç kez kopyalarsanız 36 segmentte skor **0.808** kalıyor — oran
ölçek-bağımsız, ama yalnızca karışım aynı kaldıkça.

Buradan çıkan üç kural:

- Temiz içerik eklemek kapıyı kendiliğinden gevşetir. Katalog büyüdükçe eşiği **yeniden ölçün**.
- "Kapı yeşil" borcun bittiğini göstermez; uyarı sayısını ayrıca kaydedin (§6, politika 2).
- Testlerde skoru sabit sayıyla assert etmeyin; segment sayısı değişince oran da değişir. Altın set
  (`uv run locale-gate eval examples/golden`) bu yüzden kod beklentisi üzerinden çalışır, skor üzerinden değil.

## 8. Ölçümü yeniden üretmek

`examples/data/catalog.json`'u bir kopyaya alın ve aşağıdaki `target` değişikliklerini sırayla uygulayın;
her satırdan sonra `uv run locale-gate check <kopya> --glossary examples/data/glossary.yaml` koşun.

| Aşama | Segment | Yeni `target` |
|-------|---------|---------------|
| A | `P-1002-title` | `Womens Puffer Jacket, Water Repellent Fabric, Hooded` |
| A | `P-1005-description` | `Your order {order_id} will be shipped within 2 business days.` |
| A | `P-1006-description` | `No shipping fee is charged on orders over 500 TL; the return period is 14 days.` |
| A | `P-1007-title` | `Womens Winter Puffer Jacket` |
| B | `P-1010-bullet` | `Separate pattern for each size; please check the size chart` |
| C | `P-1003-bullet` | `Measures 45 x 30 x 12 cm and weighs only 780 grams` |
| D | `P-1008-title` | `Genuine Leather Wallet with RFID Protection` |
| D | `P-1009-title` | `Product Features and Measurements` |

D aşaması `examples/data/catalog-fixed.json` ile aynı skoru verir (1.000). Temiz segment deneyi için
`P-1001-title`'ın 24 kopyasını benzersiz id'lerle ekleyip yeniden koşun: `skor: 0.864`, uyarı sayısı
değişmeden 5 kalır.

## 9. Kontrol listesi

- [ ] Baseline `--report` ile saklandı; kod dağılımı (§2 tablosu) kayıtlı.
- [ ] Kritik = 0. Eşik tartışması bundan sonra başlar.
- [ ] `gate`, ölçülen skorun **en küçük tek segment cezasından az** altında (veya eşit).
- [ ] Eşik `locale-gate.toml` içinde; `--fail-under` yalnızca denemelerde.
- [ ] Her yükseltme tek bir kural/segment grubuna bağlı; commit mesajı hangi segmentin düzeldiğini yazıyor.
- [ ] Yükseltmeden sonra katalog büyümesi yeniden ölçüldü (§7).
- [ ] Uyarı borcu ayrı sayılıyor; hedef 0, kapı yeşili bunun yerine geçmiyor.

CI'da kalıcı eşik:

```yaml
- name: Çeviri kalite kapısı
  run: uv run locale-gate check content/catalog.json --glossary content/glossary.yaml \
       --config locale-gate.toml --github-summary
```

Kural kodları ve gerekçeleri: [rules.md](rules.md) · skorun neden deterministik olduğu:
[ADR-0001](adr/0001-deterministic-gate.md) · altın set:
[ADR-0002](adr/0002-golden-set.md)
