import 'package:flutter/material.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Profil')),
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
              child: const Column(
                children: [
                  CircleAvatar(
                    radius: 44,
                    backgroundColor: Colors.white24,
                    child: Icon(Icons.person, size: 48, color: Colors.white),
                  ),
                  SizedBox(height: 14),
                  Text(
                    'Misafir Kullanıcı',
                    style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                  ),
                  SizedBox(height: 6),
                  Text(
                    'Üye olarak analiz geçmişini kaydedebilirsin',
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            _statCard('Toplam Analiz', '0', Icons.analytics_outlined),
            _statCard('Güvenli Ürün', '0', Icons.verified_outlined),
            _statCard('Riskli Ürün', '0', Icons.warning_amber_outlined),
            const SizedBox(height: 16),
            _menuCard(
              icon: Icons.history,
              title: 'Analiz Geçmişi',
              subtitle: 'Daha önce sorguladığın ürünleri görüntüle',
              onTap: () => Navigator.pushNamed(context, '/history'),
            ),

            _menuCard(
              icon: Icons.login,
              title: 'Giriş Yap / Üye Ol',
              subtitle: 'Profilini aktif hale getir',
              onTap: () => Navigator.pushNamed(context, '/login'),
            ),
          ],
        ),
      ),
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
