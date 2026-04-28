import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../service/audit_provider.dart';
import 'upload_screen.dart';
import 'monitoring_screen.dart';
import '../widgets/nutrition_label.dart';
import '../widgets/chat_sidebar.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  int _selectedIndex = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('EquiLabel Platform', style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: Theme.of(context).colorScheme.primary,
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: Row(
        children: [
          NavigationRail(
            selectedIndex: _selectedIndex,
            onDestinationSelected: (int index) {
              setState(() {
                _selectedIndex = index;
              });
            },
            labelType: NavigationRailLabelType.all,
            selectedIconTheme: IconThemeData(color: Theme.of(context).colorScheme.primary),
            destinations: const [
              NavigationRailDestination(
                icon: Icon(Icons.upload_file_outlined),
                selectedIcon: Icon(Icons.upload_file),
                label: Text('Audit'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.monitor_heart_outlined),
                selectedIcon: Icon(Icons.monitor_heart),
                label: Text('Monitoring'),
              ),
            ],
          ),
          const VerticalDivider(thickness: 1, width: 1),
          Expanded(
            child: _buildMainContent(),
          ),
        ],
      ),
    );
  }

  Widget _buildMainContent() {
    if (_selectedIndex == 1) {
      return const MonitoringScreen();
    }

    return Consumer<AuditProvider>(
      builder: (context, auditProvider, child) {
        if (auditProvider.status == AuditStatus.idle || auditProvider.status == AuditStatus.failed) {
          return const UploadScreen();
        } else if (auditProvider.status == AuditStatus.uploading || auditProvider.status == AuditStatus.processing) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const CircularProgressIndicator(),
                const SizedBox(height: 24),
                Text(
                  auditProvider.status == AuditStatus.uploading ? 'Uploading model data...' : 'Auditing fairness metrics...',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ],
            ),
          );
        } else if (auditProvider.status == AuditStatus.complete) {
          return Row(
            children: [
              Expanded(
                flex: 2,
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(32.0),
                  child: Center(
                    child: NutritionLabel(report: auditProvider.report!),
                  ),
                ),
              ),
              const VerticalDivider(width: 1, thickness: 1),
              SizedBox(
                width: 400,
                child: ChatSidebar(auditId: auditProvider.auditId!),
              ),
            ],
          );
        }
        return const SizedBox.shrink();
      },
    );
  }
}
