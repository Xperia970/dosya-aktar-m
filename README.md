# LocalSend Python Dosya Aktarım Uygulaması

Bu proje, Wi-Fi üzerinden basit bir dosya aktarma aracı sağlar. Bir cihazda `serve` modunu çalıştırıp diğer cihazlardan tarayıcı veya CLI aracılığıyla dosya gönderebilirsiniz.

## Gereksinimler

- Python 3.8 veya üzeri

## Kullanım

### Sunucu modu
Bir cihazda aşağıdaki komutu çalıştırın:

```bash
python localsend.py serve
```

Çıktıda sizin yerel IP adresiniz ve port adresiniz gösterilir. Örnek:

```text
Ağdaki tüm cihazlar için erişim adresi: http://192.168.1.10:8080
```

Sonra aynı ağdaki başka bir cihazdan bu adresi tarayıcıda açarak dosya seçip gönderebilirsiniz.

### İstemci modu (CLI)
Birden fazla dosyayı göndermek için terminalde şu şekilde kullanabilirsiniz:

```bash
python localsend.py send 192.168.1.10:8080 dosya1.txt resim.png
```

### Kaydedilen dosyalar
Alınan dosyalar `received/` klasörüne kaydedilir.

## Özellikler

- Wi-Fi ağında aynı alt ağdaki cihazlar arasında çalışır
- Tarayıcıdan dosya yükleme destekler
- CLI üzerinden dosya gönderebilir
- Gelen dosyalar `received/` klasörüne kaydedilir

## Notlar

- Hedef adresi `IP:PORT` formatında olmalıdır.
- Sunucunun çalıştığı portun yerel ağda açık olduğundan emin olun.
- Eğer sunucu IP adresi yanlış görünürse, aynı ağda olduğunuzdan ve Python uygulamasının ağ erişimine izinli olduğundan emin olun.
