import 'package:dio/dio.dart';
import 'package:http_parser/http_parser.dart';
import 'package:flutter/foundation.dart';
import '../services/dio_client.dart';
import '../models/document_model.dart';

class DocumentRepository {
  final DioClient _client = DioClient();

  // [1] 문서 업로드
  Future<Document?> uploadDocument({
    required String fileName,
    String? filePath,
    List<int>? fileBytes,
  }) async {
    try {
      MultipartFile filePart;

      if (kIsWeb && fileBytes != null) {
        filePart = MultipartFile.fromBytes(
          fileBytes,
          filename: fileName,
          contentType: MediaType('application', 'pdf'),
        );
      } else if (filePath != null) {
        filePart = await MultipartFile.fromFile(
          filePath,
          filename: fileName,
          contentType: MediaType('application', 'pdf'),
        );
      } else {
        throw Exception("파일 데이터가 없습니다.");
      }

      FormData formData = FormData.fromMap({
        "file": filePart,
        "title": fileName,
      });

      final response = await _client.dio.post('/documents', data: formData);

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = response.data;
        // 업로드 직후 응답 처리
        String realTitle = fileName;
        int realChars = 0;

        if (data['meta'] != null) {
          realTitle = data['meta']['filename'] ?? fileName;
          realChars = data['meta']['total_chars'] ?? 0;
        } else {
          realTitle = data['title'] ?? fileName;
          realChars = data['total_chars'] ?? data['char_count'] ?? 0;
        }

        return Document(
          id: data['document_id'] ?? data['id'] ?? '',
          title: realTitle,
          contentType: 'text/plain',
          charCount: realChars,
        );
      }
    } catch (e) {
      print("업로드 실패: $e");
    }
    return null;
  }

  // [2] 문서 목록 조회 (파일명 복구 로직 강화)
  Future<List<Document>> getDocuments() async {
    try {
      final response = await _client.dio.get('/documents');
      
      if (response.statusCode == 200) {
        List<dynamic> list = [];
        if (response.data is Map && response.data.containsKey('documents')) {
          list = response.data['documents'];
        } else if (response.data is List) {
          list = response.data;
        }

        // [핵심] 제목이 doc_... 이면 상세 조회로 진짜 이름 찾기
        final futures = list.map((e) async {
          String id = e['document_id'] ?? e['id'] ?? '';
          String title = e['title'] ?? e['filename'] ?? '제목 없음';
          int charCount = e['total_chars'] ?? e['char_count'] ?? 0;

          // 제목이 ID와 같거나 doc_로 시작하면 상세 조회 시도
          if (id.isNotEmpty && (title == id || title.startsWith('doc_'))) {
            try {
              final detailRes = await _client.dio.get('/documents/$id');
              if (detailRes.statusCode == 200) {
                final meta = detailRes.data['meta'];
                if (meta != null) {
                  title = meta['filename'] ?? title;
                  charCount = meta['total_chars'] ?? charCount;
                }
              }
            } catch (_) {
              // 실패하면 원래 제목 사용
            }
          }

          return Document(
            id: id,
            title: title,
            contentType: e['content_type'],
            charCount: charCount,
          );
        });

        return await Future.wait(futures);
      }
    } catch (e) {
      print("목록 조회 실패: $e");
    }
    return [];
  }

  // [3] 문서 삭제
  Future<bool> deleteDocument(String documentId) async {
    try {
      if (documentId.isEmpty) return false;
      final response = await _client.dio.delete('/documents/$documentId');
      return response.statusCode == 200 || response.statusCode == 204;
    } on DioException catch (e) {
      if (e.response?.statusCode == 405) return false;
      return false;
    } catch (e) {
      return false;
    }
  }

  // [4] 내용 조회
  Future<List<String>> getDocumentContent(String documentId) async {
    try {
      if (documentId.isEmpty) return ["ID 오류"];
      final response = await _client.dio.get('/documents/$documentId/chunks');
      if (response.statusCode == 200) {
        List<dynamic> rawList = [];
        if (response.data is List) rawList = response.data;
        else if (response.data is Map) {
          final map = response.data as Map;
          if (map.containsKey('chunks')) rawList = map['chunks'];
          else if (map.containsKey('data')) rawList = map['data'];
        }
        return rawList.map((item) {
          if (item is String) return item;
          if (item is Map && item.containsKey('text')) return item['text'].toString();
          return item.toString();
        }).toList();
      }
    } catch (e) {
      print("내용 조회 실패: $e");
    }
    return ["내용을 불러올 수 없습니다."];
  }
}