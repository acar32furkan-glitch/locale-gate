# ADR-0002 — Altın set, kuralların davranış sözleşmesidir

- **Durum:** Kabul edildi
- **Tarih:** 2026-10-06

## Bağlam

Kural temelli bir kalite kapısının en büyük riski **sessiz davranış değişikliğidir**: bir kuralı
gevşetmek (ya da bir düzenli ifadeyi düzeltmek) başka bir senaryoda yanlış alarm üretmeye başlar ve
bunu fark eden olmaz. Klasik birim testleri tek tek fonksiyonları korur ama "gerçek bir katalogda
toplam davranış" bozulabilir.

## Karar

`examples/golden/` altında, her biri kendi katalog + sözlük + yapılandırmasını getiren vakalar
tutulur ve **beklenen bulgu kodları segment bazında** yazılır:

```json
{"name": "tr-en temel kurallar", "catalog": "tr_en_temel/catalog.json",
 "expected": {"G-102-title": ["TERM_EKSIK", "TERM_YASAK"]}, "expect_passed": false}
```

- `locale-gate eval examples/golden` vakaları çalıştırır ve farkı raporlar; fark varsa çıkış kodu 1.
- Karşılaştırma **iki yönlüdür**: beklenen kod eksikse *ve* beklenmeyen kod çıkarsa vaka düşer. Yani
  yeni bir yanlış alarm da testi kırar.
- Vakalar `pytest` içinde `@pytest.mark.golden` ile de ayrıca koşar; CI her ikisini çalıştırır.

## Sonuçlar

- **Kazanç:** kural davranışı, örnek dosyalarla birlikte sürümlenir; inceleme (review) sırasında
  "bu değişiklik hangi vakayı etkiler?" sorusu tek komutla yanıtlanır.
- **Bedel:** yeni bir kural eklerken altın seti de güncellemek gerekir (bilinçli sürtünme).
- **Kural:** bir vaka beklenmedik şekilde düşerse, önce **kural mı yoksa beklenti mi** yanlış
  sorusu sorulur; beklenti düzeltilecekse neden düzeltildiği commit mesajında yazılır.
