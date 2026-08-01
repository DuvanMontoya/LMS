from rest_framework import serializers

from domain.identity.models import PlatformRegistrationSettings


class RegistrationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformRegistrationSettings
        fields = (
            "public_signup_enabled",
            "signup_mode",
            "require_email_verification",
            "default_locale",
            "default_timezone",
            "updated_at",
            "lock_version",
        )
        read_only_fields = (
            "public_signup_enabled",
            "require_email_verification",
            "updated_at",
            "lock_version",
        )


class PublicRegistrationSettingsSerializer(RegistrationSettingsSerializer):
    """Expose the live browser decision without exposing administrative data."""

    signup_available = serializers.SerializerMethodField()

    class Meta(RegistrationSettingsSerializer.Meta):
        fields = (
            "signup_mode",
            "require_email_verification",
            "default_locale",
            "default_timezone",
            "signup_available",
        )
        read_only_fields = fields

    def get_signup_available(self, settings: PlatformRegistrationSettings) -> bool:
        if settings.signup_mode == PlatformRegistrationSettings.SignupMode.OPEN.value:
            return True
        if (
            settings.signup_mode
            != PlatformRegistrationSettings.SignupMode.INVITE_ONLY.value
        ):
            return False
        request = self.context.get("request")
        if request is None:
            return False
        from domain.organizations.services import session_has_valid_signup_invitation

        return session_has_valid_signup_invitation(request._request)


class RegistrationSettingsUpdateSerializer(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)
    signup_mode = serializers.ChoiceField(
        choices=PlatformRegistrationSettings.SignupMode.choices
    )
    default_locale = serializers.CharField(max_length=16)
    default_timezone = serializers.CharField(max_length=64)
