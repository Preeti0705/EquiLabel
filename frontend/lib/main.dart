import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:google_fonts/google_fonts.dart';

import 'service/audit_provider.dart';
import 'screens/dashboard_screen.dart';

void main() {
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuditProvider()),
      ],
      child: const EquiLabelApp(),
    ),
  );
}

class EquiLabelApp extends StatelessWidget {
  const EquiLabelApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'EquiLabel',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF1E3A8A), // Deep Blue
          primary: const Color(0xFF1E3A8A),
          secondary: const Color(0xFF10B981), // Emerald Green
          error: const Color(0xFFEF4444), // Red
          background: const Color(0xFFF3F4F6), // Light Gray
        ),
        textTheme: GoogleFonts.interTextTheme(
          Theme.of(context).textTheme,
        ),
        useMaterial3: true,
      ),
      home: const DashboardScreen(),
    );
  }
}
