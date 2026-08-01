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
    )


def participant_identity(user_id: object) -> str:
    return f"user:{user_id}"


class LiveKitGateway:
    def __init__(self, config: LiveKitConfiguration | None = None) -> None:
        self.config = config or configuration()

    def issue_token(
        self, *, user_id: object, room_name: str, access: LiveAccess
    ) -> str:
        publish_sources: list[str] = []
        if access.can_publish:
            if access.role != "student" or settings.LIVEKIT_STUDENT_CAN_PUBLISH_VIDEO:
                publish_sources.append("camera")
            if access.role != "student" or settings.LIVEKIT_STUDENT_CAN_PUBLISH_AUDIO:
                publish_sources.append("microphone")
        if access.can_share_screen:
            publish_sources.extend(("screen_share", "screen_share_audio"))
        grants = api.VideoGrants(
            room_join=True,
            room=room_name,
            can_subscribe=True,
            can_publish=bool(publish_sources),
            can_publish_data=False,
            can_publish_sources=publish_sources,
            can_update_own_metadata=False,
        )
        token = (
            api.AccessToken(self.config.api_key, self.config.api_secret)
            .with_identity(participant_identity(user_id))
            .with_name(f"Participante {str(user_id)[:8]}")
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

    def create_room(self, *, room_name: str, metadata: str) -> Any:
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
                        empty_timeout=self.config.room_empty_timeout_seconds,
                        departure_timeout=30,
                        max_participants=self.config.max_participants,
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

    def update_participant_permissions(
        self,
        *,
        room_name: str,
        identity: str,
        can_publish_audio: bool,
        can_publish_video: bool,
        can_share_screen: bool,
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
                        can_publish_data=False,
                        can_publish_sources=sources,
                        can_update_metadata=False,
                    ),
                )
            )

        try:
            async_to_sync(self._with_client)(operation)
        except Exception as error:
            raise LiveKitRejected("No fue posible cambiar los permisos.") from error

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
