import 'package:flutter/material.dart';

class AppDrawer extends StatelessWidget {
  const AppDrawer({super.key});

  @override
  Widget build(BuildContext context) {
    return Drawer(
      backgroundColor: const Color(0xFF0B1020),
      child: SafeArea(
        child: Column(
          children: [
            const ListTile(
              leading: CircleAvatar(
                backgroundColor: Color(0xFF7C3AED),
                child: Icon(Icons.smart_toy, color: Colors.white),
              ),
              title: Text(
                'AI Güven Asistanı',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              subtitle: Text('Alışveriş güven analizleri'),
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
              title: const Text('Analiz Geçmişi'),
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

            ListTile(
              leading: const Icon(Icons.login),
              title: const Text('Giriş / Üyelik'),
              onTap: () {
                Navigator.pop(context);
                Navigator.pushNamed(context, '/login');
              },
            ),
          ],
        ),
      ),
    );
  }
}
