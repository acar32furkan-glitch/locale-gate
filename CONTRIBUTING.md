# Katkı Rehberi

Teşekkürler! Bu proje **deterministik kalmayı** bir tasarım ilkesi olarak benimser; katkıların
tamamı bu çizgide olmalıdır.

## Hızlı kurulum

```bash
git clone https://github.com/acar32furkan-glitch/locale-gate
cd locale-gate
uv sync --all-extras --dev
uv run locale-gate check examples/data/catalog.json --glossary examples/data/glossary.yaml
uv run pytest
```

## Kurallar

1. **Ağ çağrısı yok, saat okuma yok, rastgelelik yok.** Kurallar saf fonksiyondur; zaman dışarıdan
   verilir. Bir kural ağa çıkıyorsa tasarım tartışması gerekir (bkz. `docs/adr/0001-deterministic-gate.md`).
2. **Kapsamı doğru bildir.** Bir kural yalnızca baktığı segmentleri `checked` olarak saymalı; aksi
   hâlde skor yanıltıcı olur.
3. **Yanlış alarm, kaçırmaktan pahalıdır.** Bir kural emin olmadığında uyarmaz (örnek: diakritik
   kuralı yalnızca kaynakta doğru yazım varsa uyarır).
4. **Altın seti güncelle.** Yeni bir kural veya davranış değişikliği `examples/golden` vakalarına
   yansımalı; beklenti değiştiyse commit mesajında gerekçesi yazılmalı.
5. **Türkçe metin, İngilizce alan adı.** Bulgu mesajları ve dokümanlar Türkçe; kod/alan/kod adları
   İngilizce.

## Kalite kapıları

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy                              # strict
uv run pytest --cov=locale_gate
uv run locale-gate eval examples/golden   # altın set
```

## Commit ve PR

- Conventional Commits: `feat(rules): ...`, `fix(tokens): ...`, `docs: ...`, `test: ...`.
- PR açıklamasında: ne değişti, neden, hangi altın set vakası etkilendi.
- Yeni kural eklerken `docs/rules.md` ve `docs/architecture.md` içindeki listeleri güncelleyin.

## Hata bildirimi

Bir yanlış alarm veya kaçırılan hata bulduğunuzda lütfen **segment metnini** paylaşın (mümkünse
kısaltarak): kural, metne bakan bir fonksiyondur ve örnek olmadan düzeltilemez.
