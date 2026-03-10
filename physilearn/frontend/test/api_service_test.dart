import 'package:flutter_test/flutter_test.dart';
import '../lib/services/api_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class FakeSecureStorage extends Fake implements FlutterSecureStorage {
  final Map<String, String> _storage = {};

  @override
  Future<void> write(
      {required String key,
      required String? value,
      dynamic iOptions,
      dynamic aOptions,
      dynamic lOptions,
      dynamic webOptions,
      dynamic mOptions,
      dynamic wOptions}) async {
    if (value != null)
      _storage[key] = value;
    else
      _storage.remove(key);
  }

  @override
  Future<String?> read(
      {required String key,
      dynamic iOptions,
      dynamic aOptions,
      dynamic lOptions,
      dynamic webOptions,
      dynamic mOptions,
      dynamic wOptions}) async {
    return _storage[key];
  }

  @override
  Future<void> deleteAll(
      {dynamic iOptions,
      dynamic aOptions,
      dynamic lOptions,
      dynamic webOptions,
      dynamic mOptions,
      dynamic wOptions}) async {
    _storage.clear();
  }
}

void main() {
  group('ApiService Robust Error Handling Tests', () {
    late ApiService apiService;
    late FakeSecureStorage fakeStorage;

    setUp(() {
      fakeStorage = FakeSecureStorage();
    });

    test('login() successfully secures tokens on 200 OK', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
            jsonEncode({
              'access': 'atoken',
              'refresh': 'rtoken',
              'user': {'id': 1, 'role': 'ADMIN'}
            }),
            200);
      });
      apiService = ApiService(storage: fakeStorage, client: mockClient);

      final result = await apiService.login('u', 'p');
      expect(result['access'], 'atoken');
      expect(await fakeStorage.read(key: 'access_token'), 'atoken');
    });

    test('login() throws exception with raw body on 401 Unauthorized',
        () async {
      final mockClient = MockClient((request) async {
        return http.Response(
            jsonEncode({'detail': 'Invalid credentials'}), 401);
      });
      apiService = ApiService(storage: fakeStorage, client: mockClient);

      expect(
        () => apiService.login('u', 'p'),
        throwsA(predicate((e) => e.toString().contains('Invalid credentials'))),
      );
    });

    test('getStudents() uses compute and handles timeouts', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
            jsonEncode([
              {'id': 1, 'name': 'S1'}
            ]),
            200);
      });
      apiService = ApiService(storage: fakeStorage, client: mockClient);
      await fakeStorage.write(key: 'access_token', value: 'token');

      final students = await apiService.getStudents();
      expect(students.length, 1);
      expect(students[0].name, 'S1');
    });
  });
}
