class ApiService {
  Future<String> analyzeProduct(String message) async {
    await Future.delayed(const Duration(seconds: 2));

    return '''
Ürünü analiz ettim.

Genel Güven Skoru: 78/100

Yorum Güvenilirliği:
Yorumların çoğu doğal görünüyor. Ancak bazı kısa ve tekrar eden yorumlar tespit edildi.

Satıcı Güvenilirliği:
Satıcı genel olarak güvenilir görünüyor. Fakat kargo gecikmesiyle ilgili bazı şikayetler var.

İndirim Gerçeklik Analizi:
İndirim büyük oranda gerçek görünüyor. Fiyat geçmişinde aşırı manipülasyon belirtisi yok.

Temel Risk Faktörleri:
• Bazı yorumlar çok kısa
• Kargo gecikmesi şikayetleri var
• Son yorumlar ayrıca kontrol edilmeli

Nihai Tavsiye:
Dikkatli şekilde satın alınabilir.
''';
  }
}
