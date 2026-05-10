import 'package:flutter/material.dart';

class HistoryScreen extends StatelessWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final bool hasHistory = false;

    return Scaffold(
      appBar: AppBar(title: const Text('Analiz Geçmişi')),
      body: hasHistory ? _historyList() : _emptyHistory(context),
    );
  }

  Widget _emptyHistory(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.history_toggle_off,
              size: 80,
              color: Color(0xFFA78BFA),
            ),
            const SizedBox(height: 20),
            const Text(
              'Henüz analiz geçmişin yok',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            const Text(
              'Bir ürün linki veya ürün adı gönderdiğinde analizlerin burada görünecek.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white70),
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: () {
                Navigator.pop(context);
              },
              icon: const Icon(Icons.add),
              label: const Text('Yeni analiz başlat'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _historyList() {
    return const Center(child: Text('Geçmiş analizler burada listelenecek.'));
  }
}
