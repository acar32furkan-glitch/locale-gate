# Taban Çizgisi: Mevcut Borcu Dondurup Yalnızca Regresyonu Bildirmek

Gerçek bir katalog ilk günden `gate = 0.95` eşiğinin altındadır. Borç kapanana kadar her PR'ı
kırmızı göstermek kapıyı "herkesin görmezden geldiği" bir tören hâline getirir: kırmızı çıktı bilgi
taşımaz olur. `--baseline report.json` bu sorunu **yalnızca yeni bulguları kapıya sokarak** çözer —
borç kaybolmaz, ama borç yüzünden kimse de engellenmez.

Buradaki her sayı depodaki `examples/data/catalog.json` (12 segment, bilinçli kirli örnek) üzerinde
gerçekten koşulmuş komutlardan geliyor.

## 1. Önce taban: bir kez dondur

```bash
uv run locale-gate check examples/data/catalog.json --glossary examples/data/glossary.yaml \
  --report taban.json
```

Çıkış kodu **1** (borç var, kapı düştü) ama rapor yazılır — taban bilinçli olarak kırmızı bir koşudan
üretilir. Yazılan dosya `--json` ile aynı sözleşmedir: `findings[]`, `stats[]`, `score`, `gate`.
Bu dosyayı depoya koyun (ör. `content/taban.json`) ve PR'larda ona referans verin.

## 2. Sonraki koşular: yalnızca yeniyi gör

```console
$ uv run locale-gate check examples/data/catalog.json --glossary examples/data/glossary.yaml \
    --baseline taban.json
ÇEVİRİ KALİTE KAPISI
  yön: tr → en  ·  segment: 12  ·  katalog: examples\data\catalog.json
  skor: 1.000 / eşik 0.950  ·  KRİTİK 0  ·  UYARI 0  ·  BİLGİ 0
  taban taban.json: 12 bilinen bulgu devralındı (kapıya girmiyor) · 0 yeni · 0 kapanmış · ham skor 0.529
  (skor yalnızca YENİ bulgulardan hesaplandı; taban dosyası güncellenmedi)

KURAL BAŞARI ORANLARI
  Sözlük uyumu      100.0%   (0 bulgu / 7 segment)
  Korunan ifadeler  100.0%   (0 bulgu / 3 segment)
  Türkçe yazım      100.0%   (0 bulgu / 12 segment)
  Uzunluk bütçesi   100.0%   (0 bulgu / 12 segment)

Yeni bulgu yok; 12 bilinen bulgu tabanda devralındı.

KARAR: GEÇTİ ✔
```

Ham skor (`raw_score = 0.529`) raporda kalır: borcun büyüklüğü gizlenmez, yalnızca **karara girmez**.
`--json` çıktısında ek blok:

```json
"baseline": {
  "path": "taban.json",
  "entries": 12,
  "suppressed": 12,
  "new": 0,
  "stale": 0,
  "raw_score": 0.5292
}
```

`entries` tabandaki satır sayısı, `suppressed` bu koşuda gerçekten eşleşip düşülen bulgu sayısı,
`new` kapıya giren bulgu, `stale` ise tabanda durup artık üretilmeyen (yani düzeltilmiş) bulgu.

## 3. Regresyon yakalanıyor mu? Ölçüldü

Taban dondurulmuşken kataloğa tek bir bozuk segment eklendi (`{order_id}` yer tutucusu hedef metinde
yok):

```console
$ uv run locale-gate check katalog-yeni.json --glossary examples/data/glossary.yaml --baseline taban.json
  skor: 0.912 / eşik 0.950  ·  KRİTİK 1  ·  UYARI 0  ·  BİLGİ 0
  taban taban.json: 12 bilinen bulgu devralındı (kapıya girmiyor) · 1 yeni · 0 kapanmış · ham skor 0.503

YENİ BULGULAR
  1. [KRİTİK] [TOKEN_KAYIP] Yer tutucu korunmamış: {order_id}
      alan   : description  ·  segment: YENI-1-description

KARAR: KALDI ✘
  neden: skor 0.912 < eşik 0.950 (1 kritik, 1 bulgu)
  neden: 1 kritik bulgu var (fail_on_critical=true)
```

Skor **yeniden hesaplanıyor**, sabit bir değere çekilmiyor: 13 segmentte `tokens` kapsamı 4, tek
etkilenen segment → `0.35 × (1 − 1/4)` ağırlığı düşürür, kalan üç kural 1.0 → `0.9125`. Kritik sayacı
da yalnızca yeni bulguyu sayar.

Borç dondurulmazsa aynı katalog `0.503` ile düşerdi; fark, kapının **ne söylediği**: "12 eski bulgu
duruyor" değil, "sen bir tane ekledin".

## 4. Kısmi taban: borcu kurallara bölebilirsiniz

Tabana yalnızca `TERM_EKSIK` bulguları konursa (3 bulgu) kalan 9 bulgu hâlâ kapıya girer:

```text
suppressed: 3 · new: 9 · stale: 0 · ham skor: 0.5292 → skor: 0.5792 · kritik: 5 → 2
```

Bu, kalibrasyonun (§[kalibrasyon.md](kalibrasyon.md)) kademeli yükseltmesiyle aynı mantık: hangi borç
önce kapanacaksa, taban o kadar daraltılır ve eşik zamanla yükseltilir.

## 5. Eşleşme kimliği: kod + segment + alan

Bir bulgu `(code, segment_id, field)` üçlüsüyle tanınır. Sonuçları:

- **Mesaj metni değişse de aynı bulgu sayılır.** Çeviriyi düzeltmek borcu yeniden doğurmaz.
- **Segment kimliği değişirse bulgu yenidir.** `G-102-title` → `G-102-title-v2` yapmak tabanı
  geçersiz kılar; katalog kimliklerini sabit tutun.
- **Alan değişirse bulgu yenidir.** Aynı kod aynı segmentte `title` yerine `bullet` alanında
  görünüyorsa bu gerçekten başka bir ihlaldir.

## 6. Reddedilen durumlar (hepsi çıkış kodu 2)

| Durum | Neden reddedilir |
|-------|------------------|
| `--baseline` + `--report` birlikte | Taban raporu **tam** bulgu listesi taşımalı; tabanla yazılan rapor borcu sessizce küçültürdü. |
| Taban başka dil çiftinden (`en→tr` raporu, `tr→en` koşusu) | Kodlar aynı olduğu için borç "tanınmış" görünür ve kapı hiçbir şeyi denetlemez. |
| Geçersiz JSON | Satır/sütunla Türkçe hata; yutulan taban borcu kapıya geri döndürür. |
| `findings` listesi yok, satır nesne değil, `code`/`segment_id`/`field` eksik | Aynı gerekçe: yarım okunan taban yanlış karar üretir. |

## 7. Sınırlar

- **Taban kendiliğinden güncellenmez.** Borç kapandıkça tabanı elle daraltın; aksi hâlde taban
  zamanla "tüm bulgular"a dönüşür ve kapı yalnızca yeni hataları görür — istenen davranış bu, ama
  tabanın da bakılması gerekir.
- **Segment sayısı değişebilir.** Taban segment sayısına bağlı değil; kimlik eşleşmesi kullanılır.
  Bu yüzden büyüyen katalogda eski borç yerinde sayar, kapsam (`checked`) ise büyür — skor ham
  koşudan farklı çıkabilir.
- **Taban bir "onay" değildir.** Devralınan bulgular kaybolmaz: `suppressed` sayısı ve ham skor her
  koşuda yazılır, PR yorumunda da görünür (`--github-summary`).

## 8. Yeniden üretme

```bash
uv run locale-gate check examples/data/catalog.json --glossary examples/data/glossary.yaml --report taban.json
uv run locale-gate check examples/data/catalog.json --glossary examples/data/glossary.yaml --baseline taban.json
uv run pytest tests/test_baseline.py -q     # 17 test: kimlik, yön, bozuk taban, skor, CLI sözleşmesi
```
