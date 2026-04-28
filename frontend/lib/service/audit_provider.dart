import 'package:flutter/material.dart';
import 'dart:async';
import 'api_service.dart';

enum AuditStatus { idle, uploading, processing, complete, failed }

class AuditProvider with ChangeNotifier {
  final ApiService _apiService = ApiService();

  bool _isGeminiLoading = false;

  String _chatResponse = '';
  
  AuditStatus _status = AuditStatus.idle;
  AuditStatus get status => _status;

  String? _auditId;
  String? get auditId => _auditId;

  Map<String, dynamic>? _report;
  Map<String, dynamic>? get report => _report;

  String _errorMessage = '';
  String get errorMessage => _errorMessage;

  Future<void> startAudit(List<int> fileBytes, String filename) async {
    try {
      _status = AuditStatus.uploading;
      notifyListeners();

      _auditId = await _apiService.uploadAudit(fileBytes, filename);
      _status = AuditStatus.processing;
      notifyListeners();

      // Poll status every 2 seconds
      Timer.periodic(const Duration(seconds: 2), (timer) async {
        if (_status != AuditStatus.processing) {
          timer.cancel();
          return;
        }

        try {
          Map<String, dynamic> data = await _apiService.getStatus(_auditId!);
          String currentStatus = data['status'];
          
          if (currentStatus == 'complete') {
            _report = await _apiService.getReport(_auditId!);
            _status = AuditStatus.complete;
            notifyListeners();
            timer.cancel();
          } else if (currentStatus == 'failed') {
            _status = AuditStatus.failed;
            _errorMessage = data['error'] ?? 'Audit processing failed on server.';
            notifyListeners();
            timer.cancel();
          }
        } catch (e) {
          // Ignore polling errors or handle them
        }
      });
    } catch (e) {
      _status = AuditStatus.failed;
      _errorMessage = e.toString();
      notifyListeners();
    }
  }
  
  void reset() {
    _status = AuditStatus.idle;
    _auditId = null;
    _report = null;
    _errorMessage = '';
    notifyListeners();
  }
}
