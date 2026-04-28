import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';

class NutritionLabel extends StatelessWidget {
  final Map<String, dynamic> report;

  const NutritionLabel({super.key, required this.report});

  Color _getFairnessColor(double score) {
    if (score >= 0.9) return const Color(0xFF10B981); // Green
    if (score >= 0.8) return const Color(0xFFF59E0B); // Yellow
    return const Color(0xFFEF4444); // Red
  }

  @override
  Widget build(BuildContext context) {
    final double fairnessScore = report['fairness_score'];
    final double accuracy = (report['accuracy'] ?? report['model_accuracy'] ?? 0.0).toDouble();
    final String auditId = report['audit_id'];

    return Container(
      width: 450,
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: Colors.black, width: 4),
        boxShadow: const [
          BoxShadow(
            color: Colors.black12,
            blurRadius: 20,
            offset: Offset(0, 10),
          )
        ],
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header
          const Text(
            'Algorithmic Fairness Label',
            style: TextStyle(fontSize: 32, fontWeight: FontWeight.w900, height: 1.1, letterSpacing: -0.5),
          ),
          const SizedBox(height: 4),
          Text(
            'Model: Production Classifier v2.1',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.grey[800]),
          ),
          Text(
            'Audit ID: $auditId',
            style: TextStyle(fontSize: 14, color: Colors.grey[600]),
          ),
          const Divider(thickness: 8, color: Colors.black, height: 24),

          // Top Scores
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Accuracy Score', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  Text('${(accuracy * 100).toStringAsFixed(1)}%', style: const TextStyle(fontSize: 42, fontWeight: FontWeight.w900)),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  const Text('Fairness Score', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  Text(
                    '${(fairnessScore * 100).toStringAsFixed(1)}%',
                    style: TextStyle(
                      fontSize: 42,
                      fontWeight: FontWeight.w900,
                      color: _getFairnessColor(fairnessScore),
                    ),
                  ),
                ],
              ),
            ],
          ),
          const Divider(thickness: 4, color: Colors.black, height: 24),

          // Demographic Parity
          const Text('Demographic Parity', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          const Text('Positive outcome rates across groups', style: TextStyle(fontSize: 12, color: Colors.grey)),
          const SizedBox(height: 16),
          SizedBox(
            height: 120,
            child: _buildDemographicChart(),
          ),
          const Divider(thickness: 2, color: Colors.black, height: 24),

          // Equalized Odds
          const Text('Equalized Odds Gaps', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildMetricCard('TPR Gap', report['equalized_odds']['tpr_gap'], Colors.blue),
              _buildMetricCard('FPR Gap', report['equalized_odds']['fpr_gap'], Colors.orange),
            ],
          ),
          const Divider(thickness: 2, color: Colors.black, height: 24),

          // Proxy Alerts
          const Text('Proxy Alerts', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.red)),
          const SizedBox(height: 8),
          ..._buildProxyAlerts(),
          const Divider(thickness: 8, color: Colors.black, height: 32),

          // Footer
          Center(
            child: Column(
              children: [
                const Text('Certified by EquiLabel™', style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1)),
                Text('Date: ${DateTime.now().toString().split(' ')[0]}', style: const TextStyle(fontSize: 12)),
                Text('Hash: ${auditId.hashCode.toRadixString(16).toUpperCase()}', style: const TextStyle(fontSize: 10, color: Colors.grey)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDemographicChart() {
    Map<String, dynamic> groups = report['demographic_parity']['groups'];
    List<BarChartGroupData> barGroups = [];
    int i = 0;
    
    groups.forEach((key, value) {
      barGroups.add(
        BarChartGroupData(
          x: i,
          barRods: [
            BarChartRodData(
              toY: value * 100,
              color: Colors.blue.shade800,
              width: 24,
              borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
            ),
          ],
        ),
      );
      i++;
    });

    return BarChart(
      BarChartData(
        alignment: BarChartAlignment.spaceAround,
        maxY: 100,
        barTouchData: BarTouchData(enabled: false),
        titlesData: FlTitlesData(
          show: true,
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              getTitlesWidget: (value, meta) {
                String title = groups.keys.elementAt(value.toInt());
                return Padding(
                  padding: const EdgeInsets.only(top: 8.0),
                  child: Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 10)),
                );
              },
            ),
          ),
          leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        gridData: const FlGridData(show: false),
        borderData: FlBorderData(show: false),
        barGroups: barGroups,
      ),
    );
  }

  Widget _buildMetricCard(String title, double value, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.5)),
      ),
      child: Column(
        children: [
          Text(title, style: TextStyle(fontWeight: FontWeight.bold, color: color.withOpacity(0.8))),
          const SizedBox(height: 4),
          Text('${(value * 100).toStringAsFixed(1)}%', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: color)),
        ],
      ),
    );
  }

  List<Widget> _buildProxyAlerts() {
    List<dynamic> alerts = report['proxy_alerts'];
    if (alerts.isEmpty) {
      return [const Text('No strong proxies detected.', style: TextStyle(color: Colors.green, fontWeight: FontWeight.bold))];
    }

    return alerts.map((alert) {
      return Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: Colors.red.shade50,
          border: Border(left: BorderSide(color: Colors.red.shade600, width: 4)),
        ),
        child: Row(
          children: [
            const Icon(Icons.warning_amber_rounded, color: Colors.red, size: 20),
            const SizedBox(width: 8),
            Expanded(
              child: RichText(
                text: TextSpan(
                  style: const TextStyle(color: Colors.black87, fontSize: 13),
                  children: [
                    const TextSpan(text: 'Feature '),
                    TextSpan(text: alert['feature'], style: const TextStyle(fontWeight: FontWeight.bold)),
                    const TextSpan(text: ' correlates strongly with '),
                    TextSpan(text: alert['correlates_with'], style: const TextStyle(fontWeight: FontWeight.bold)),
                    TextSpan(text: ' (r=${alert['correlation']})'),
                  ],
                ),
              ),
            ),
          ],
        ),
      );
    }).toList();
  }
}
