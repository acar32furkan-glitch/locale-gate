## Ne değişti?

<!-- Kısa özet. Örnek: "tokens kuralı artık litre/mililitre ölçülerini de koruyor" -->

## Neden?

<!-- Hangi hata sınıfı yakalanıyor: Closes #12 -->

## Altın set etkisi

- [ ] `examples/golden` vakaları güncellendi (beklenti değiştiyse gerekçesi aşağıda)
- [ ] `uv run locale-gate eval examples/golden` yerelde geçiyor

## Kontrol listesi

- [ ] Kural saf fonksiyon (ağ/saat/rastgelelik yok)
- [ ] `checked` kapsamı doğru bildiriliyor
- [ ] Yanlış alarm riski test edildi (emin olunmayan durumda kural susuyor)
- [ ] `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest` geçiyor
- [ ] Dokümantasyon güncellendi (`docs/rules.md` kod tablosu, gerekirse `docs/architecture.md`)
