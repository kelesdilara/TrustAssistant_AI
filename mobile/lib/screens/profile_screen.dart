import 'package:flutter/material.dart';

import '../services/api_service.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final ApiService _apiService = ApiService();
  late Future<_ProfileData> _profileFuture;

  @override
  void initState() {
    super.initState();
    _profileFuture = _loadProfile();
  }

  void _reload() {
    setState(() {
      _profileFuture = _loadProfile();
    });
  }

  Future<_ProfileData> _loadProfile() async {
    final email = await _apiService.currentUserEmail();
    if (email == null) {
      return const _ProfileData();
    }

    try {
      final history = await _apiService.fetchAnalysisHistory(limit: 100);
      return _ProfileData.fromHistory(email: email, history: history);
    } catch (_) {
      return _ProfileData(email: email, historyUnavailable: true);
    }
  }

  Future<void> _logout() async {
    await _apiService.logout();
    if (!mounted) return;
    Navigator.pushNamedAndRemoveUntil(context, '/', (route) => false);
  }

  Future<void> _openLogin() async {
    await Navigator.pushNamed(context, '/login');
    if (mounted) {
      _reload();
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<_ProfileData>(
      future: _profileFuture,
      builder: (context, snapshot) {
        final profile = snapshot.data ?? const _ProfileData(isLoading: true);
        final isLoading = snapshot.connectionState == ConnectionState.waiting;
        final hasError = snapshot.hasError;
        final isSignedIn = profile.isSignedIn;

        return Scaffold(
          appBar: AppBar(
            title: const Text('Profil'),
            actions: [
              IconButton(onPressed: _reload, icon: const Icon(Icons.refresh)),
            ],
          ),
          body: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(22),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF7C3AED), Color(0xFF2563EB)],
                    ),
                    borderRadius: BorderRadius.circular(24),
                  ),
                  child: Column(
                    children: [
                      const CircleAvatar(
                        radius: 44,
                        backgroundColor: Colors.white24,
                        child: Icon(
                          Icons.person,
                          size: 48,
                          color: Colors.white,
                        ),
                      ),
                      const SizedBox(height: 14),
                      if (isLoading)
                        const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      else
                        Text(
                          profile.displayName,
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      const SizedBox(height: 6),
                      Text(
                        isLoading
                            ? 'Profil yukleniyor...'
                            : isSignedIn
                            ? 'Hesabin aktif. Yeni analizlerin bu profile kaydedilecek.'
                            : hasError
                            ? 'Profil bilgileri yuklenemedi.'
                            : 'Uye olarak analiz gecmisini kaydedebilirsin.',
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                _statCard(
                  'Toplam Analiz',
                  profile.totalAnalysesText,
                  Icons.analytics_outlined,
                ),
                _statCard(
                  'Guvenli Urun',
                  profile.safeProductsText,
                  Icons.verified_outlined,
                ),
                _statCard(
                  'Riskli Urun',
                  profile.riskyProductsText,
                  Icons.warning_amber_outlined,
                ),
                const SizedBox(height: 16),
                _menuCard(
                  icon: Icons.history,
                  title: 'Analiz Gecmisi',
                  subtitle: profile.historyUnavailable
                      ? 'Gecmis su anda yuklenemedi'
                      : isSignedIn
                      ? 'Daha once sorguladigin urunleri goruntule'
                      : 'Gecmisini gormek icin giris yap',
                  onTap: () => Navigator.pushNamed(context, '/history'),
                ),
                if (isSignedIn)
                  _menuCard(
                    icon: Icons.logout,
                    title: 'Cikis Yap',
                    subtitle: 'Bu cihazdaki oturumu kapat',
                    onTap: _logout,
                  )
                else
                  _menuCard(
                    icon: Icons.login,
                    title: 'Giris Yap / Uye Ol',
                    subtitle: 'Profilini aktif hale getir',
                    onTap: _openLogin,
                  ),
              ],
            ),
          ),
        );
      },
    );
  }

  static Widget _statCard(String title, String value, IconData icon) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF151B2E),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFF29314A)),
      ),
      child: Row(
        children: [
          Icon(icon, color: const Color(0xFF8B5CF6)),
          const SizedBox(width: 14),
          Expanded(child: Text(title)),
          Text(
            value,
            style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }

  static Widget _menuCard({
    required IconData icon,
    required String title,
    required String subtitle,
    VoidCallback? onTap,
  }) {
    return Card(
      color: const Color(0xFF151B2E),
      child: ListTile(
        leading: Icon(icon, color: const Color(0xFF8B5CF6)),
        title: Text(title),
        subtitle: Text(subtitle),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}

class _ProfileData {
  final String? email;
  final int totalAnalyses;
  final int safeProducts;
  final int riskyProducts;
  final bool historyUnavailable;
  final bool isLoading;

  const _ProfileData({
    this.email,
    this.totalAnalyses = 0,
    this.safeProducts = 0,
    this.riskyProducts = 0,
    this.historyUnavailable = false,
    this.isLoading = false,
  });

  factory _ProfileData.fromHistory({
    required String email,
    required List<Map<String, dynamic>> history,
  }) {
    var safeProducts = 0;
    var riskyProducts = 0;

    for (final item in history) {
      final score = item['overall_trust_score'];
      if (score is num && score >= 70) {
        safeProducts++;
      } else if (score is num && score < 50) {
        riskyProducts++;
      }
    }

    return _ProfileData(
      email: email,
      totalAnalyses: history.length,
      safeProducts: safeProducts,
      riskyProducts: riskyProducts,
    );
  }

  bool get isSignedIn => email != null;

  String get displayName => email ?? 'Misafir Kullanici';

  String get totalAnalysesText => '$totalAnalyses';

  String get safeProductsText => '$safeProducts';

  String get riskyProductsText => '$riskyProducts';
}
