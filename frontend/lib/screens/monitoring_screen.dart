import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';

class MonitoringScreen extends StatelessWidget {
  const MonitoringScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(48.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Continuous Monitoring',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
              ),
              ElevatedButton.icon(
                onPressed: () {},
                icon: const Icon(Icons.picture_as_pdf),
                label: const Text('Export PDF Report'),
              ),
            ],
          ),
          const SizedBox(height: 32),
          
          Container(
            height: 300,
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              boxShadow: [
                BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 10),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Fairness Score Over Time', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                const SizedBox(height: 16),
                Expanded(
                  child: LineChart(
                    LineChartData(
                      gridData: const FlGridData(show: true),
                      titlesData: const FlTitlesData(
                        rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                        topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                      ),
                      borderData: FlBorderData(show: true, border: Border.all(color: Colors.grey.shade300)),
                      minX: 0,
                      maxX: 6,
                      minY: 0.5,
                      maxY: 1.0,
                      lineBarsData: [
                        LineChartBarData(
                          spots: const [
                            FlSpot(0, 0.85),
                            FlSpot(1, 0.82),
                            FlSpot(2, 0.78), // Dip
                            FlSpot(3, 0.71), // Violation
                            FlSpot(4, 0.75),
                            FlSpot(5, 0.79),
                            FlSpot(6, 0.73),
                          ],
                          isCurved: true,
                          color: Colors.blue,
                          barWidth: 3,
                          isStrokeCapRound: true,
                          dotData: const FlDotData(show: true),
                          belowBarData: BarAreaData(show: true, color: Colors.blue.withOpacity(0.1)),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 32),
          
          const Text('Recent Bias Violations', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          Expanded(
            child: Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                boxShadow: [
                  BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 10),
                ],
              ),
              child: ListView(
                children: [
                  _buildViolationItem(context, 'Demographic Parity Gap', 'Hispanic group fell below 0.8 thresholds', '2 hours ago'),
                  const Divider(height: 1),
                  _buildViolationItem(context, 'Proxy Detected', 'Feature `zip_code` highly correlated with protected attribute', '1 day ago'),
                  const Divider(height: 1),
                  _buildViolationItem(context, 'Equalized Odds', 'FPR gap increased by 4%', '3 days ago'),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildViolationItem(BuildContext context, String title, String desc, String time) {
    return ListTile(
      leading: const Icon(Icons.warning, color: Colors.orange),
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
      subtitle: Text(desc),
      trailing: Text(time, style: TextStyle(color: Colors.grey.shade600, fontSize: 12)),
    );
  }
}
