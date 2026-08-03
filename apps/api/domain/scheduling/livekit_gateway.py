# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnnecessaryComparison=false
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, TypeVar

from asgiref.sync import async_to_sync
from django.conf import settings
from livekit import api

from .exceptions import LiveKitRejected, LiveKitUnavailable
from .policies import LiveAccess

T = TypeVar("T")


@dataclass(frozen=True)
class LiveKitConfiguration:
    server_url: str
    api_key: str
    api_secret: str
    token_ttl_seconds: int
    room_empty_timeout_seconds: int
    max_participants: int
    egress_template_url: str = ""


def configuration() -> LiveKitConfiguration:
    if not settings.LIVEKIT_ENABLED:
        raise LiveKitUnavailable("LiveKit no está habilitado en este entorno.")
    if not all(
        (settings.LIVEKIT_URL, settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
    ):
        raise LiveKitUnavailable("La configuración LiveKit está incompleta.")
    return LiveKitConfiguration(
        server_url=settings.LIVEKIT_URL,
        api_key=settings.LIVEKIT_API_KEY,
        api_secret=settings.LIVEKIT_API_SECRET,
        token_ttl_seconds=settings.LIVEKIT_TOKEN_TTL_SECONDS,
        room_empty_timeout_seconds=settings.LIVEKIT_ROOM_EMPTY_TIMEOUT_SECONDS,
        max_participants=settings.LIVEKIT_MAX_PARTICIPANTS,
        egress_template_url=settings.LIVEKIT_EGRESS_TEMPLATE_URL,
    )


def participant_identity(user_id: object) -> str:
    return f"user:{user_id}"


class LiveKitGateway:
    def __init__(self, config: LiveKitConfiguration | None = None) -> None:
        self.config = config or configuration()

    def issue_token(
        self,
        *,
        user_id: object,
        participant_name: str = "Participante",
        room_name: str,
        access: LiveAccess,
        chat_enabled: bool = False,
        student_audio_enabled: bool = True,
        student_video_enabled: bool = True,
        student_screen_share_enabled: bool = False,
    ) -> str:
        publish_sources: list[str] = []
        if access.can_publish:
            if access.role != "student" or student_video_enabled:
                publish_sources.append("camera")
            if access.role != "student" or student_audio_enabled:
                publish_sources.append("microphone")
        if access.can_share_screen and (
            access.role != "student" or student_screen_share_enabled
        ):
            publish_sources.extend(("screen_share", "screen_share_audio"))
        grants = api.VideoGrants(
            room_join=True,
            room=room_name,
            can_subscribe=True,
            can_publish=bool(publish_sources),
            can_publish_data=chat_enabled,
            can_publish_sources=publish_sources,
            can_update_own_metadata=False,
        )
        token = (
            api.AccessToken(self.config.api_key, self.config.api_secret)
            .with_identity(participant_identity(user_id))
            .with_name(participant_name.strip() or "Participante")
            .with_attributes({"lms.role": access.role})
            .with_grants(grants)
            .with_ttl(timedelta(seconds=self.config.token_ttl_seconds))
        )
        return token.to_jwt()

    async def _with_client(
        self, operation: Callable[[api.LiveKitAPI], Awaitable[T]]
    ) -> T:
        client = api.LiveKitAPI(
            url=self.config.server_url,
            api_key=self.config.api_key,
            api_secret=self.config.api_secret,
        )
        try:
            return await operation(client)
        finally:
            await client.aclose()

    def create_room(
        self,
        *,
        room_name: str,
        metadata: str,
        empty_timeout_seconds: int | None = None,
        departure_timeout_seconds: int = 30,
        max_participants: int | None = None,
    ) -> Any:
        async def operation(client: api.LiveKitAPI):
            existing = await client.room.list_rooms(
                api.ListRoomsRequest(names=[room_name])
            )
            if existing.rooms:
                return existing.rooms[0]
            try:
                return await client.room.create_room(
                    api.CreateRoomRequest(
                        name=room_name,
                        empty_timeout=(
                            empty_timeout_seconds
                            or self.config.room_empty_timeout_seconds
                        ),
                        departure_timeout=departure_timeout_seconds,
                        max_participants=max_participants
                        or self.config.max_participants,
                        metadata=metadata,
                    )
                )
            except api.TwirpError:
                retried = await client.room.list_rooms(
                    api.ListRoomsRequest(names=[room_name])
                )
                if retried.rooms:
                    return retried.rooms[0]
                raise

        try:
            return async_to_sync(self._with_client)(operation)
        except LiveKitUnavailable:
            raise
        except Exception as error:
            raise LiveKitRejected("LiveKit rechazó la creación de la sala.") from error

    def close_room(self, *, room_name: str) -> None:
        async def operation(client: api.LiveKitAPI):
            existing = await client.room.list_rooms(
                api.ListRoomsRequest(names=[room_name])
            )
            if not existing.rooms:
                return None
            return await client.room.delete_room(api.DeleteRoomRequest(room=room_name))

        try:
            async_to_sync(self._with_client)(operation)
        except Exception as error:
            raise LiveKitRejected("LiveKit rechazó el cierre de la sala.") from error

    def start_room_recording(
        self,
        *,
        room_name: str,
        layout: str,
        resolution: str,
        filepath: str,
    ) -> Any:
        if layout == "screen_share" and not self.config.egress_template_url:
            raise LiveKitUnavailable(
                "La plantilla privada de grabación de pantalla no está configurada."
            )
        preset = (
            api.EncodingOptionsPreset.H264_1080P_30
            if resolution == "1080p"
            else api.EncodingOptionsPreset.H264_720P_30
        )

        async def operation(client: api.LiveKitAPI):
            return await client.egress.start_room_composite_egress(
                api.RoomCompositeEgressRequest(
                    room_name=room_name,
                    layout=(
                        "screen-share"
                        if layout == "screen_share"
                        else "grid"
                        if layout == "grid"
                        else "speaker-dark"
                    ),
                    custom_base_url=(
                        self.config.egress_template_url
                        if layout == "screen_share"
                        else ""
                    ),
                    preset=preset,
                    file_outputs=[
                        api.EncodedFileOutput(
                            file_type=api.EncodedFileType.MP4,
                            filepath=filepath,
                        )
                    ],
                )
            )

        try:
            return async_to_sync(self._with_client)(operation)
        except Exception as error:
            raise LiveKitRejected("LiveKit Egress rechazó la grabación.") from error

    def stop_recording(self, *, egress_id: str) -> Any:
        async def operation(client: api.LiveKitAPI):
            return await client.egress.stop_egress(
                api.StopEgressRequest(egress_id=egress_id)
            )

        try:
            return async_to_sync(self._with_client)(operation)
        except Exception as error:
            raise LiveKitRejected(
                "LiveKit Egress no pudo detener la grabación."
            ) from error

    def list_participants(self, *, room_name: str) -> list[Any]:
        async def operation(client: api.LiveKitAPI):
            response = await client.room.list_participants(
                api.ListParticipantsRequest(room=room_name)
            )
            return list(response.participants)

        try:
            return async_to_sync(self._with_client)(operation)
        except Exception as error:
            raise LiveKitRejected("No fue posible consultar participantes.") from error

    def has_active_screen_share(self, *, room_name: str) -> bool:
        return "screen_share" in self.active_visual_sources(room_name=room_name)

    def active_visual_sources(self, *, room_name: str) -> set[str]:
        source_names = {
            api.TrackSource.CAMERA: "camera",
            api.TrackSource.SCREEN_SHARE: "screen_share",
        }
        return {
            source_names[track.source]
            for participant in self.list_participants(room_name=room_name)
            for track in participant.tracks
            if track.source in source_names and not track.muted
        }

    def update_participant_permissions(
        self,
        *,
        room_name: str,
        identity: str,
        can_publish_audio: bool,
        can_publish_video: bool,
        can_share_screen: bool,
        chat_enabled: bool,
    ) -> None:
        sources: list[api.TrackSource] = []
        if can_publish_video:
            sources.append(api.TrackSource.CAMERA)
        if can_publish_audio:
            sources.append(api.TrackSource.MICROPHONE)
        if can_share_screen:
            sources.extend(
                (api.TrackSource.SCREEN_SHARE, api.TrackSource.SCREEN_SHARE_AUDIO)
            )

        async def operation(client: api.LiveKitAPI):
            return await client.room.update_participant(
                api.UpdateParticipantRequest(
                    room=room_name,
                    identity=identity,
                    permission=api.ParticipantPermission(
                        can_subscribe=True,
                        can_publish=bool(sources),
                        can_publish_data=chat_enabled,
                        can_publish_sources=sources,
                        can_update_metadata=False,
                    ),
                )
            )

        try:
            async_to_sync(self._with_client)(operation)
        except Exception as error:
            raise LiveKitRejected("No fue posible cambiar los permisos.") from error

    def mute_participant_microphone(self, *, room_name: str, identity: str) -> None:
        participant = next(
            (
                item
                for item in self.list_participants(room_name=room_name)
                if item.identity == identity
            ),
            None,
        )
        track_sids = [
            track.sid
            for track in getattr(participant, "tracks", ())
            if track.source == api.TrackSource.MICROPHONE and not track.muted
        ]
        if not track_sids:
            return

        async def operation(client: api.LiveKitAPI) -> None:
            for track_sid in track_sids:
                await client.room.mute_published_track(
                    api.MuteRoomTrackRequest(
                        room=room_name,
                        identity=identity,
                        track_sid=track_sid,
                        muted=True,
                    )
                )

        try:
            async_to_sync(self._with_client)(operation)
        except Exception as error:
            raise LiveKitRejected("No fue posible silenciar el micrófono.") from error

    def remove_participant(self, *, room_name: str, identity: str) -> None:
        async def operation(client: api.LiveKitAPI):
            return await client.room.remove_participant(
                api.RoomParticipantIdentity(room=room_name, identity=identity)
            )

        try:
            async_to_sync(self._with_client)(operation)
        except Exception as error:
            raise LiveKitRejected("No fue posible expulsar al participante.") from error

    def webhook_receiver(self) -> api.WebhookReceiver:
        return api.WebhookReceiver(
            api.TokenVerifier(self.config.api_key, self.config.api_secret)
        )
