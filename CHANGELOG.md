# Değişiklik Günlüğü

Bu dosya [Keep a Changelog](https://keepachangelog.com/tr/1.1.0/) biçimini izler ve proje
[Semantic Versioning](https://semver.org/lang/tr/) kullanır.

## [0.1.0] - 2026-10-06

### Eklendi
- **Kural motoru:** dört bağımsız, saf fonksiyon kuralı — `terminology`, `tokens`, `turkish`, `length`.
  Her kural kendi kapsamını (`checked`) bildirir; skor etkilenen segment üzerinden hesaplanır.
- **Sözlük kuralı:** zorunlu karşılıklar (`TERM_EKSIK`, kritik) ve yasaklı varyantlar (`TERM_YASAK`);
  Türkçe harf duyarlı kelime sınırı (`beden` eşleşir, `bedenler` eşleşmez).
- **Korunan ifadeler:** yer tutucu (`{order_id}`, `%s`, `{{ name }}`, `${amount}`) ve HTML etiketi
  kaybı kritik; bağlantı/e-posta kaybı uyarı; ölçü ve model numarası kaybı `SAYI_KAYIP`
  (karşılaştırma rakam dizisi üzerinden — `2,5 kg → 2.5 kg` geçerli, `780 gram → 0.78 kg` hata).
- **Türkçe yazım:** `TR_DIAKRITIK` (ASCII'ye düşmüş kelimeler), `TR_BUYUK_I` (`i → İ` büyük harf
  kuralı), `CEVRILMEMIS` (kaynakla birebir aynı segment), `TR_KARAKTER` (İngilizce hedefte Türkçe
  karakter sızıntısı).
- **Türkçe sayı biçimi:** `NUM_AYIRICI` (ondalık/binlik ayırıcı) ve `YUZDE_KONUM` (`%` işareti
  sayının önüne gelir) yalnızca `tr` hedefli kataloglarda.
- **Uzunluk bütçesi:** alan sınırı aşımı (`LENGTH_SINIR`) ve kaynağa göre aşırı uzama
  (`LENGTH_UZAMA`); uzama oranı 25 karakterden uzun kaynaklarda ölçülür.
- **Kapı kararı:** ağırlıklı skor + kritik bulgu kapısı; `--fail-under` ile geçici eşik.
- **Girdi katmanı:** JSON ve CSV katalog, YAML/JSON sözlük, TOML/JSON yapılandırma; bilinmeyen
  alanlar reddedilir (yazım hatası koruması). Çıkış kodları: 0 geçti, 1 kapı düştü, 2 girdi hatası.
- **Altın set:** `examples/golden` altında üç vaka (tr-en, en-tr, temiz katalog); iki yönlü
  karşılaştırma ile hem eksik hem beklenmeyen bulguyu yakalar.
- **Çıktılar:** Türkçe konsol raporu, `--json` sözleşmesi, `--report` dosyası, `--github-summary`
  (Actions iş özeti) ve Markdown özeti.
- **Kalite:** 119 test (kural sınırları, altın set, CLI sözleşmesi, mutasyon testleri),
  `ruff` + `mypy --strict` + karmaşık `kapsam` (%91), GitHub Actions CI ve Dependabot.
- **Dokümantasyon:** kural sözlüğü, mimari, iki ADR, yol haritası ve gerçek çıktıdan üretilen SVG demo.
