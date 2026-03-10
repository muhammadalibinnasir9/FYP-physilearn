import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import '../lib/screens/admin_dashboard.dart';
import '../lib/services/api_service.dart';
import '../lib/models/student.dart';

class MockApiService extends Mock implements ApiService {
  @override
  Future<List<Map<String, dynamic>>> getUsers() async => [
        {
          'id': 1,
          'username': 'teacher1',
          'role': 'TEACHER',
          'email': 't1@test.com'
        },
        {
          'id': 2,
          'username': 'parent1',
          'role': 'PARENT',
          'email': 'p1@test.com'
        },
      ];

  @override
  Future<List<Student>> getStudents() async => [];
}

void main() {
  testWidgets('AdminDashboard blocks empty Roll Number submission',
      (WidgetTester tester) async {
    final mockApi = MockApiService();

    // Build the widget
    await tester.pumpWidget(MaterialApp(
      home: AdminDashboard(apiService: mockApi),
    ));

    // Wait for data load
    await tester.pumpAndSettle();

    // Navigate to Students tab
    await tester.tap(find.text('Students'));
    await tester.pumpAndSettle();

    // Click "Add New Student"
    await tester.tap(find.text('Add New Student'));
    await tester.pumpAndSettle();

    // Enter Name but leave Roll Number empty
    await tester.enterText(
        find.widgetWithText(TextFormField, 'Full Name'), 'John Doe');

    // Tap Save
    await tester.tap(find.text('Save'));
    await tester.pump(); // Start building the error messages

    // Check for validation error
    expect(find.text('Roll Number is required'), findsOneWidget);
    expect(find.text('Section is required'), findsOneWidget);
  });
}
