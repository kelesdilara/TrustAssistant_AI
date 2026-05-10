class ChatMessage {
  final String text;
  final bool isUser;
  final DateTime createdAt;

  ChatMessage({required this.text, required this.isUser, DateTime? createdAt})
    : createdAt = createdAt ?? DateTime.now();
}
