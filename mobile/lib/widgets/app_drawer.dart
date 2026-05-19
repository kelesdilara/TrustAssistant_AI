import 'package:flutter/material.dart';

import '../services/api_service.dart';

class AppDrawer extends StatelessWidget {
  const AppDrawer({super.key});

  @override
  Widget build(BuildContext context) {
    final apiService = ApiService();

    return Drawer(
      backgroundColor: const Color(0xFF0B1020),
      child: SafeArea(
        child: FutureBuilder<String?>(
          future: apiService.currentUserEmail(),
          builder: (context, snapshot) {
            final email = snapshot.data;
            final isSignedIn = email != null;

            return Column(
              children: [
                ListTile(
                  leading: const CircleAvatar(
                    backgroundColor: Color(0xFF7C3AED),
                    child: Icon(Icons.smart_toy, color: Colors.white),
                  ),
                  title: const Text(
                    'AI Guven Asistani',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  subtitle: Text(
                    isSignedIn ? email : 'Misafir oturumu',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const Divider(),

                ListTile(
                  leading: const Icon(Icons.add_comment_outlined),
                  title: const Text('Yeni Analiz'),
                  onTap: () {
                    Navigator.popUntil(context, (route) => route.isFirst);
                  },
                ),

                ListTile(
                  leading: const Icon(Icons.history),
                  title: const Text('Analiz Gecmisi'),
                  onTap: () {
                    Navigator.pop(context);
                    Navigator.pushNamed(context, '/history');
                  },
                ),

                const Spacer(),
                const Divider(),

                ListTile(
                  leading: const Icon(Icons.person_outline),
                  title: const Text('Profil'),
                  onTap: () {
                    Navigator.pop(context);
                    Navigator.pushNamed(context, '/profile');
                  },
                ),

                if (isSignedIn)
                  ListTile(
                    leading: const Icon(Icons.logout),
                    title: const Text('Cikis Yap'),
                    onTap: () async {
                      await apiService.logout();
                      if (!context.mounted) return;
                      Navigator.pushNamedAndRemoveUntil(
                        context,
                        '/',
                        (route) => false,
                      );
                    },
                  )
                else
                  ListTile(
                    leading: const Icon(Icons.login),
                    title: const Text('Giris / Uyelik'),
                    onTap: () {
                      Navigator.pop(context);
                      Navigator.pushNamed(context, '/login');
                    },
                  ),
              ],
            );
          },
        ),
      ),
    );
  }
}
