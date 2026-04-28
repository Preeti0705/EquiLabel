import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  final String baseUrl = 'http://localhost:8000/api/v1';

  Future<String> getGeminiExplanation(String auditId, String question) async {
  final response = await http.post(
    Uri.parse('$baseUrl/audit/$auditId/explain'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({'question': question, 'audience': 'hospital_admin'}),
  );

  if (response.statusCode == 200) {
    return jsonDecode(response.body)['explanation'];
  } else {
    throw Exception('Gemini failed to respond');
  }
}

  Future<String> uploadAudit(List<int> bytes, String filename) async {
    var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/audit/upload'));
    request.files.add(http.MultipartFile.fromBytes('file', bytes, filename: filename));
    
    var response = await request.send();
    if (response.statusCode == 200) {
      var responseData = await response.stream.bytesToString();
      var data = jsonDecode(responseData);
      return data['audit_id'];
    } else {
      throw Exception('Failed to upload file');
    }
  }

  Future<Map<String, dynamic>> getStatus(String auditId) async {
    var response = await http.get(Uri.parse('$baseUrl/audit/$auditId/status'));
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to get status');
    }
  }

  Future<Map<String, dynamic>> getReport(String auditId) async {
    var response = await http.get(Uri.parse('$baseUrl/audit/$auditId/report'));
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to get report');
    }
  }
}
