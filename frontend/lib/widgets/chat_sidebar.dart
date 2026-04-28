import 'package:flutter/material.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;

class ChatSidebar extends StatefulWidget {
  final String auditId;

  const ChatSidebar({super.key, required this.auditId});

  @override
  State<ChatSidebar> createState() => _ChatSidebarState();
}

class _ChatSidebarState extends State<ChatSidebar> {
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<Map<String, String>> _messages = [];
  bool _isLoading = false;

  @override
  void dispose() {
    _textController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _sendMessage() async {
    final question = _textController.text.trim();
    if (question.isEmpty || _isLoading) return;

    setState(() {
      _messages.add({'role': 'user', 'content': question});
      _messages.add({'role': 'assistant', 'content': 'Thinking...'});
      _isLoading = true;
    });

    _textController.clear();
    _scrollToBottom();

    String assistantReply;

    try {
      final uri = Uri.parse(
        'http://localhost:8000/api/v1/audit/${widget.auditId}/chat',
      );

      final response = await http
          .post(
            uri,
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'question': question, 'audience': 'hospital_admin'}),
          )
          .timeout(const Duration(seconds: 120));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        assistantReply =
            (data['answer'] ?? data['explanation'] ?? '').toString().trim();
        if (assistantReply.isEmpty) assistantReply = 'No response received.';
      } else {
        String detail = 'Error ${response.statusCode}';
        try {
          final err = jsonDecode(response.body) as Map<String, dynamic>;
          detail = err['detail']?.toString() ?? detail;
        } catch (_) {}
        assistantReply = detail;
      }
    } catch (e) {
      // Broad catch: Flutter web can throw DOMException / Error (not just Exception)
      final msg = e.toString();
      if (msg.contains('TimeoutException') || msg.contains('timeout')) {
        assistantReply =
            'Request timed out (>2 min). The AI model may be busy — please try again.';
      } else if (msg.contains('XMLHttpRequest') || msg.contains('Failed host')) {
        assistantReply =
            'Cannot reach the backend. Make sure the server is running on port 8000.';
      } else {
        assistantReply = 'Error: $msg';
      }
    }

    if (!mounted) return;

    setState(() {
      _messages.last['content'] = assistantReply;
      _isLoading = false;
    });

    _scrollToBottom();
  }

  Widget _buildMessage(Map<String, String> msg) {
    final isUser = msg['role'] == 'user';
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 320),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: isUser ? const Color(0xFF1A73E8) : Colors.grey.shade100,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(isUser ? 16 : 4),
            bottomRight: Radius.circular(isUser ? 4 : 16),
          ),
          border: isUser
              ? null
              : Border.all(color: Colors.grey.shade300),
        ),
        child: SelectableText(
          msg['content'] ?? '',
          style: TextStyle(
            fontSize: 13.5,
            color: isUser ? Colors.white : Colors.black87,
            height: 1.4,
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white,
      child: Column(
        children: [
          // Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            color: Theme.of(context).colorScheme.primary,
            child: const Row(
              children: [
                Icon(Icons.auto_awesome, color: Colors.white, size: 20),
                SizedBox(width: 8),
                Text(
                  'Ask Gemini',
                  style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
              ],
            ),
          ),

          // Messages
          Expanded(
            child: _messages.isEmpty
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.chat_bubble_outline,
                            size: 40, color: Colors.grey.shade300),
                        const SizedBox(height: 12),
                        Text(
                          'Ask about your audit results',
                          style: TextStyle(
                            color: Colors.grey.shade500,
                            fontSize: 13,
                          ),
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.all(16),
                    itemCount: _messages.length,
                    itemBuilder: (context, index) =>
                        _buildMessage(_messages[index]),
                  ),
          ),

          // Loading indicator
          if (_isLoading)
            LinearProgressIndicator(
              backgroundColor: Colors.grey.shade200,
              color: Theme.of(context).colorScheme.primary,
            ),

          // Input row
          Container(
            padding: const EdgeInsets.fromLTRB(12, 8, 8, 12),
            decoration: BoxDecoration(
              color: Colors.white,
              border: Border(top: BorderSide(color: Colors.grey.shade200)),
            ),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _textController,
                    enabled: !_isLoading,
                    decoration: InputDecoration(
                      hintText: 'Why is my model biased?',
                      hintStyle: TextStyle(color: Colors.grey.shade400),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide(color: Colors.grey.shade300),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide(color: Colors.grey.shade300),
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 10),
                      isDense: true,
                    ),
                    onSubmitted: (_) => _sendMessage(),
                    maxLines: 1,
                  ),
                ),
                const SizedBox(width: 6),
                IconButton(
                  icon: const Icon(Icons.send_rounded),
                  color: _isLoading
                      ? Colors.grey.shade400
                      : Theme.of(context).colorScheme.primary,
                  onPressed: _isLoading ? null : _sendMessage,
                  tooltip: 'Send',
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
