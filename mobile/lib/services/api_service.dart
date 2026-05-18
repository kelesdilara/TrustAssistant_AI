import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  static const String _baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://127.0.0.1:8000',
  );

  Future<String> analyzeProduct(String message) async {
    final input = message.trim();
    final uri = Uri.parse('$_baseUrl/api/v1/analysis/');
    final body = _buildRequestBody(input);

    final response = await http.post(
      uri,
      headers: await _headers(includeAuth: true),
      body: jsonEncode(body),
    );

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException('Analiz istegi basarisiz oldu: ${response.statusCode}');
    }

    final data = jsonDecode(utf8.decode(response.bodyBytes));
    if (data is! Map<String, dynamic>) {
      throw ApiException('Analiz cevabi beklenen formatta degil.');
    }

    return _formatAnalysis(data);
  }

  Future<List<Map<String, dynamic>>> fetchAnalysisHistory({
    int limit = 20,
  }) async {
    final uri = Uri.parse('$_baseUrl/api/v1/analysis/history?limit=$limit');
    final response = await http
        .get(uri, headers: await _headers(includeAuth: true))
        .timeout(const Duration(seconds: 20));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException('Gecmis istegi basarisiz oldu: ${response.statusCode}');
    }

    final data = jsonDecode(utf8.decode(response.bodyBytes));
    if (data is! List) {
      throw ApiException('Gecmis cevabi beklenen formatta degil.');
    }

    return data
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
  }

  Future<String> login({
    required String email,
    required String password,
  }) async {
    return _authenticate(
      path: '/api/v1/auth/login',
      email: email,
      password: password,
    );
  }

  Future<String> register({
    required String email,
    required String password,
  }) async {
    return _authenticate(
      path: '/api/v1/auth/register',
      email: email,
      password: password,
    );
  }

  Future<String> _authenticate({
    required String path,
    required String email,
    required String password,
  }) async {
    final uri = Uri.parse('$_baseUrl$path');
    final response = await http
        .post(
          uri,
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'email': email.trim(),
            'password': password,
          }),
        )
        .timeout(const Duration(seconds: 30));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException(_errorMessage(response));
    }

    final data = jsonDecode(utf8.decode(response.bodyBytes));
    if (data is! Map<String, dynamic>) {
      throw ApiException('Kimlik dogrulama cevabi beklenen formatta degil.');
    }

    final token = data['access_token'];
    final userEmail = data['email'];
    if (token is! String || userEmail is! String) {
      throw ApiException('Kimlik dogrulama bilgileri eksik geldi.');
    }

    final preferences = await SharedPreferences.getInstance();
    await preferences.setString('access_token', token);
    await preferences.setString('user_email', userEmail);

    return userEmail;
  }

  Map<String, dynamic> _buildRequestBody(String input) {
    final isUrl = input.startsWith('http://') || input.startsWith('https://');
    return {
      if (isUrl) 'product_url': input else 'product_name': input,
      'search_mode': 'fast',
    };
  }

  Future<Map<String, String>> _headers({bool includeAuth = false}) async {
    final headers = {'Content-Type': 'application/json'};
    if (!includeAuth) return headers;

    final preferences = await SharedPreferences.getInstance();
    final token = preferences.getString('access_token');
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  String _formatAnalysis(Map<String, dynamic> data) {
    final buffer = StringBuffer();
    final analysisScope = data['analysis_scope'];
    final isReviewOnly = analysisScope == 'product_name_review_only';
    final score = data['overall_trust_score'] ?? '-';
    final reviewCount = data['review_count'] ?? 0;
    final reviewSampleTarget = data['review_sample_target'] ?? 0;
    final reviewSampleMinimum = data['review_sample_minimum'] ?? 0;
    final reviewSources = _joinList(data['review_sources']);
    final complaintCount = data['complaint_count'] ?? 0;
    final complaintScope = _complaintScopeLabel(data['complaint_scope']);
    final complaintSources = _joinList(data['complaint_sources']);
    final priceSources = _joinList(data['price_sources']);
    final marketPriceCount = _listLength(data['current_market_prices']);
    final priceHistoryDays = data['price_history_days'] ?? 0;
    final priceHistoryIsEstimated = data['price_history_is_estimated'] == true;

    buffer.writeln('Genel Guven Skoru: $score/100');
    buffer.writeln();
    buffer.writeln('Ozet:');
    buffer.writeln(data['product_summary'] ?? '-');
    buffer.writeln();
    buffer.writeln('Yorum Analizi:');
    buffer.writeln(data['review_analysis'] ?? '-');
    buffer.writeln('Yorum sayisi: $reviewCount');
    if (reviewSampleTarget is int && reviewSampleTarget > 0) {
      buffer.writeln('Yorum hedefi: $reviewSampleTarget');
    }
    if (reviewSampleMinimum is int &&
        reviewSampleMinimum > 0 &&
        reviewCount is int &&
        reviewCount < reviewSampleMinimum) {
      buffer.writeln('Not: $reviewSampleMinimum altinda yorumla sonuc sinirlidir.');
    }
    if (reviewSources.isNotEmpty) {
      buffer.writeln('Yorum kaynaklari: $reviewSources');
    }
    buffer.writeln();
    if (!isReviewOnly) {
      buffer.writeln('Satici ve Sikayet Analizi:');
      buffer.writeln(data['seller_analysis'] ?? '-');
      buffer.writeln('Sikayet sayisi: $complaintCount');
      buffer.writeln('Sikayet kapsami: $complaintScope');
      if (complaintSources.isNotEmpty) {
        buffer.writeln('Sikayet kaynaklari: $complaintSources');
      }
      buffer.writeln();
      buffer.writeln('Fiyat Analizi:');
      buffer.writeln(data['discount_analysis'] ?? '-');
      if (priceHistoryDays is int && priceHistoryDays > 0) {
        buffer.writeln(
          'Fiyat gecmisi: $priceHistoryDays gun${priceHistoryIsEstimated ? ' (tahmini)' : ''}',
        );
      } else {
        buffer.writeln('Fiyat gecmisi: bulunamadi');
      }
      if (priceSources.isNotEmpty) {
        buffer.writeln('Fiyat kaynaklari: $priceSources');
        buffer.writeln('Piyasa fiyat adedi: $marketPriceCount');
      }
      buffer.writeln();
    }
    buffer.writeln('Risk Faktorleri:');
    final riskFactors = data['risk_factors'];
    if (riskFactors is List && riskFactors.isNotEmpty) {
      for (final factor in riskFactors) {
        buffer.writeln('- $factor');
      }
    } else {
      buffer.writeln('- Belirgin risk faktoru yok.');
    }
    buffer.writeln();
    buffer.writeln('Nihai Tavsiye:');
    buffer.writeln(data['final_recommendation'] ?? '-');

    return buffer.toString().trim();
  }

  String _joinList(dynamic value) {
    if (value is! List) return '';
    return value.where((item) => item != null).map((item) => '$item').join(', ');
  }

  int _listLength(dynamic value) {
    if (value is List) return value.length;
    return 0;
  }

  String _complaintScopeLabel(dynamic value) {
    switch ('$value') {
      case 'seller':
        return 'satici';
      case 'site':
        return 'site';
      case 'product':
        return 'urun';
      default:
        return 'yok';
    }
  }

  String _errorMessage(http.Response response) {
    try {
      final data = jsonDecode(utf8.decode(response.bodyBytes));
      if (data is Map && data['detail'] != null) {
        return '${data['detail']}';
      }
    } catch (_) {
      // Fall through to generic message.
    }
    return 'Istek basarisiz oldu: ${response.statusCode}';
  }
}

class ApiException implements Exception {
  final String message;

  ApiException(this.message);

  @override
  String toString() => message;
}
