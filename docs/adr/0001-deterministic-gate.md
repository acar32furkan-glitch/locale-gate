# ADR-0001 — Kapı deterministiktir, LLM kullanmaz

- **Durum:** Kabul edildi
- **Tarih:** 2026-10-06

## Bağlam

Çeviri kalitesini ölçmenin popüler yolu bir dil modeline "bu çeviri iyi mi?" diye sormaktır. Bu
yaklaşımın üç sorunu var:

1. **Kararsızlık:** aynı metin için skor her koşuda değişebilir; CI'da "geçti/kaldı" kararı
   güvenilir olmaz.
2. **Maliyet ve gecikme:** her PR'da yüzlerce segment için model çağrısı gerekir.
3. **Gizlilik:** yayınlanmamış ürün metinleri üçüncü taraf bir servise gönderilir.

## Karar

Kural motoru **saf fonksiyonlardan** oluşur ve hiçbir ağ çağrısı yapmaz:

- Her kural `RuleContext` alır (katalog + sözlük + yapılandırma), `RuleOutcome` döndürür.
- Zaman dışarıdan verilir (`now=...`); kural içinde `datetime.now()` çağrılmaz.
- Katalog sırası sonucu etkilemez: bulgular `(önem, segment_id, kod)` ile sıralanır.

## Sonuçlar

- **Kazanç:** aynı girdi aynı skoru üretir (`tests/test_rule_*` + altın set bunu sabitler); kapı
  PR'ı haklı ve tekrar edilebilir biçimde kırar; veri makineden çıkmaz.
- **Bedel:** anlam ve akıcılık denetimi yapılamaz — "çeviri doğru ama tuhaf" durumu yakalanmaz.
  Kural seti, mekanik ve sözlük temelli hatalara odaklanır.
- **Telafi:** ekipler için yol haritasında **opsiyonel LLM hakem** var (`docs/roadmap.md`), fakat
  deterministik çekirdek her zaman CI'da çalışan kapı olarak kalacak; LLM hakem yalnızca ek sinyal
  üretecek, kararı tek başına vermeyecek.
