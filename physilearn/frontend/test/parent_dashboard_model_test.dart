import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/models/parent_dashboard.dart';

void main() {
  group('ParentDashboard Model Deserialization', () {
    late Map<String, dynamic> sampleJson;

    setUp(() {
      // Sample JSON matching backend schema
      sampleJson = {
        'student': {
          'id': 1,
          'name': 'Ali Khan',
          'roll_number': 'R001',
          'section': '7-A',
        },
        'current_health': {
          'height': 145.0,
          'weight': 42.5,
          'bmi': 20.2,
          'fitness_status': 'Normal',
          'ai_recommendations': 'Maintain a healthy lifestyle with balanced diet and regular physical activity.',
          'updated_at': '2024-03-15T10:30:00Z',
        },
        'health_history': [
          {
            'date': '2024-01-15',
            'bmi': 20.5,
            'health_score': 85.0,
          },
          {
            'date': '2024-02-15',
            'bmi': 20.3,
            'health_score': 87.0,
          },
          {
            'date': '2024-03-15',
            'bmi': 20.2,
            'health_score': 88.0,
          },
        ],
        'fitness_progress': [
          {
            'metric_name': 'Stamina',
            'latest_score': 78.0,
          },
          {
            'metric_name': 'Strength',
            'latest_score': 72.0,
          },
          {
            'metric_name': 'Flexibility',
            'latest_score': 80.0,
          },
        ],
        'ml_insights': {
          'health_score': 88.0,
          'risk_score': 15.0,
          'trend': {
            'metric': 'BMI',
            'direction': 'improving',
            'slope': -0.15,
            'r_squared': 0.92,
            'message': 'BMI is showing healthy improvement trend',
          },
        },
        'recommendations': {
          'plan_type': 'maintenance',
          'exercises': [
            'Jogging',
            'Jumping Rope',
            'Stretching',
            'Swimming',
          ],
          'frequency': '3-4 times per week',
          'duration_minutes': 45,
          'dietary_tip': 'Eat balanced meals with fruits and vegetables',
          'priority': 'normal',
        },
      };
    });

    test('should deserialize ParentDashboard from JSON', () {
      final dashboard = ParentDashboard.fromJson(sampleJson);

      // Assert student fields
      expect(dashboard.student.name, equals('Ali Khan'));

      // Assert current health fields
      expect(dashboard.currentHealth, isNotNull);
      expect(dashboard.currentHealth!.bmi, equals(20.2));

      // Assert ML insights fields
      expect(dashboard.mlInsights, isNotNull);
      expect(dashboard.mlInsights!.healthScore, equals(88.0));

      // Assert trend fields
      expect(dashboard.mlInsights!.trend.direction, equals('improving'));

      // Assert recommendations fields
      expect(dashboard.recommendations, isNotNull);
      expect(dashboard.recommendations!.planType, equals('maintenance'));
    });

    test('should parse health history list correctly', () {
      final dashboard = ParentDashboard.fromJson(sampleJson);

      expect(dashboard.healthHistory, hasLength(3));
      expect(dashboard.healthHistory[0].bmi, equals(20.5));
      expect(dashboard.healthHistory[1].healthScore, equals(87.0));
      expect(dashboard.healthHistory[2].date, isNotNull);
    });

    test('should parse fitness progress list correctly', () {
      final dashboard = ParentDashboard.fromJson(sampleJson);

      expect(dashboard.fitnessProgress, hasLength(3));
      expect(dashboard.fitnessProgress[0].metricName, equals('Stamina'));
      expect(dashboard.fitnessProgress[1].latestScore, equals(72.0));
      expect(dashboard.fitnessProgress[2].metricName, equals('Flexibility'));
    });

    test('should parse exercises list correctly', () {
      final dashboard = ParentDashboard.fromJson(sampleJson);

      expect(dashboard.recommendations, isNotNull);
      expect(dashboard.recommendations!.exercises, hasLength(4));
      expect(dashboard.recommendations!.exercises[0], equals('Jogging'));
      expect(dashboard.recommendations!.exercises[1], equals('Jumping Rope'));
      expect(dashboard.recommendations!.exercises[2], equals('Stretching'));
      expect(dashboard.recommendations!.exercises[3], equals('Swimming'));
    });

    test('should handle null values gracefully', () {
      final jsonWithNulls = {
        'student': {
          'id': 2,
          'name': 'Test Student',
          'roll_number': 'R002',
          'section': '8-B',
        },
        'current_health': null,
        'health_history': [],
        'fitness_progress': [],
        'ml_insights': null,
        'recommendations': null,
      };

      final dashboard = ParentDashboard.fromJson(jsonWithNulls);

      expect(dashboard.currentHealth, isNull);
      expect(dashboard.mlInsights, isNull);
      expect(dashboard.recommendations, isNull);
      expect(dashboard.healthHistory, isEmpty);
      expect(dashboard.fitnessProgress, isEmpty);
    });

    test('should handle missing fields with defaults', () {
      final emptyJson = <String, dynamic>{};

      final dashboard = ParentDashboard.fromJson(emptyJson);

      expect(dashboard.student.name, equals(''));
      expect(dashboard.healthHistory, isEmpty);
      expect(dashboard.fitnessProgress, isEmpty);
      expect(dashboard.currentHealth, isNull);
      expect(dashboard.mlInsights, isNull);
      expect(dashboard.recommendations, isNull);
    });

    test('ParentDashboard handles null ml_insights and recommendations', () {
      // Sample JSON with null ml_insights and recommendations
      final jsonWithNullMlAndRec = {
        'student': {
          'id': 3,
          'name': 'Fatima Ali',
          'roll_number': 'R003',
          'section': '9-C',
        },
        'current_health': {
          'height': 150.0,
          'weight': 45.0,
          'bmi': 20.0,
          'fitness_status': 'Normal',
          'ai_recommendations': 'Keep up the good work!',
          'updated_at': '2024-03-15T10:30:00Z',
        },
        'health_history': [],
        'fitness_progress': [],
        'ml_insights': null,
        'recommendations': null,
      };

      // Ensure parsing does not throw exceptions
      final dashboard = ParentDashboard.fromJson(jsonWithNullMlAndRec);

      // Assertions for null handling
      expect(dashboard.mlInsights, isNull);
      expect(dashboard.recommendations, isNull);

      // Verify other fields still parse correctly
      expect(dashboard.student.name, equals('Fatima Ali'));
      expect(dashboard.currentHealth, isNotNull);
      expect(dashboard.currentHealth!.bmi, equals(20.0));
      expect(dashboard.healthHistory, isEmpty);
      expect(dashboard.fitnessProgress, isEmpty);
    });
  });
}
