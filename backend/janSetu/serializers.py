from rest_framework import serializers

class EmailOTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class EmailOTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6)

class FirebaseVerifySerializer(serializers.Serializer):
    firebase_id_token = serializers.CharField()

