import 'package:flutter/material.dart';

import '../services/api_service.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  final ApiService _apiService = ApiService();
  late Future<List<Map<String, dynamic>>> _historyFuture;

  @override
  void initState() {
    super.initState();
    _historyFuture = _apiService.fetchAnalysisHistory();
  }

  void _reload() {
    setState(() {
      _historyFuture = _apiService.fetchAnalysisHistory();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Analiz Gecmisi'),
        actions: [
          IconButton(
            onPressed: _reload,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: FutureBuilder<List<Map<String, dynamic>>>(
        future: _historyFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return _errorState(context);
          }

          final items = snapshot.data ?? [];
          if (items.isEmpty) {
            return _emptyHistory(context);
          }

          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemBuilder: (context, index) => _HistoryCard(item: items[index]),
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemCount: items.length,
          );
        },
      ),
    );
  }

  Widget _errorState(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.cloud_off, size: 72, color: Color(0xFFF97316)),
            const SizedBox(height: 18),
            const Text(
              'Gecmis yuklenemedi',
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            const Text(
              'Backend calisiyor mu kontrol edip tekrar dene.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white70),
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: _reload,
              icon: const Icon(Icons.refresh),
              label: const Text('Tekrar dene'),
            ),
          ],
        ),
      ),
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
              'Henuz analiz gecmisin yok',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            const Text(
              'Bir urun linki veya urun adi gonderdiginde analizlerin burada gorunecek.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white70),
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: () => Navigator.pop(context),
              icon: const Icon(Icons.add),
              label: const Text('Yeni analiz baslat'),
            ),
          ],
        ),
      ),
    );
  }
}

class _HistoryCard extends StatelessWidget {
  final Map<String, dynamic> item;

  const _HistoryCard({required this.item});

  @override
  Widget build(BuildContext context) {
    final score = item['overall_trust_score'] ?? '-';
    final productName = item['product_name'] ?? 'Urun';
    final recommendation = item['final_recommendation'] ?? '-';
    final reviewCount = item['review_count'] ?? 0;
    final complaintCount = item['complaint_count'] ?? 0;
    final priceSources = _joinList(item['price_sources']);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF151B2E),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF29314A)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              CircleAvatar(
                backgroundColor: const Color(0xFF7C3AED),
                child: Text('$score'),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '$productName',
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '$recommendation',
                      style: const TextStyle(color: Colors.white70),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _MetricChip(label: 'Yorum', value: '$reviewCount'),
              _MetricChip(label: 'Sikayet', value: '$complaintCount'),
              if (priceSources.isNotEmpty)
                _MetricChip(label: 'Fiyat', value: priceSources),
            ],
          ),
        ],
      ),
    );
  }

  String _joinList(dynamic value) {
    if (value is! List) return '';
    return value.where((item) => item != null).map((item) => '$item').join(', ');
  }
}

class _MetricChip extends StatelessWidget {
  final String label;
  final String value;

  const _MetricChip({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Chip(
      label: Text('$label: $value'),
      backgroundColor: const Color(0xFF0B1020),
      side: const BorderSide(color: Color(0xFF29314A)),
    );
  }
}
