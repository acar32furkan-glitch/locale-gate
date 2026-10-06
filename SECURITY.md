# Güvenlik Politikası

## Desteklenen sürümler

| Sürüm | Destek |
|-------|--------|
| 0.1.x | ✅ |
| < 0.1 | ❌ (geliştirme sürümleri) |

## Bir açığı nasıl bildirirsiniz?

Güvenlikle ilgili konuları herkese açık issue olarak **açmayın**. GitHub üzerinden özel güvenlik
bildirimi gönderin: depoda **Security → Report a vulnerability**. Bildirimde şunları paylaşın:

- etkilenen sürüm ve işletim sistemi,
- en küçük yeniden üretim adımları (girdi dosyası: katalog/sözlük/yapılandırma),
- beklenen ve gözlenen davranış,
- varsa istismar senaryosu.

İlk yanıt hedefi: 7 iş günü. Düzeltme yayınlandığında bildirimi yapan kişi (isterseniz) sürüm
notlarında anılır.

## Tehdit modeli

`locale-gate` **çevrimdışı bir CLI/kütüphanedir**: ağa çıkmaz, hesap açmaz, kimlik bilgisi istemez,
gizli veri saklamaz.

Bu proje açısından anlamlı riskler:

| Risk | Değerlendirme |
|------|---------------|
| Doğruluk riski | Kurallar "geçti/kaldı" kararı verir; hatalı bir kural **yanlış alarm** ya da **kaçırmadır**. Kaçırılan hata güvenlik sorunu değildir; yanlış alarm ise CI'yı kırar. Her ikisi de issue olarak bildirilmeye değer. |
| Girdi dosyaları | Katalog/sözlük/yapılandırma kullanıcı girdisidir. YAML yüklerken `yaml.safe_load` kullanılır; `python -c` benzeri bir yürütme yolu yoktur. |
| Kötü niyetli regex | Sözlük terimleri `re.escape` ile kaçırılır ve kullanıcı girdisi desen olarak çalıştırılmaz. |
| Kaynak tüketimi | Uzun segmentler ve büyük kataloglar için işlem doğrusaldır; bilinen üstel desen yoktur. |

## Kapsam dışı

- Kullanıcının yüklediği katalogların içeriğinin doğruluğu (bu bir içerik sorunudur, güvenlik değil).
- Üçüncü taraf pazaryeri servisleri.
