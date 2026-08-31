import logging
from collections.abc import Iterator

from django.http import StreamingHttpResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import ChatSession
from .serializers import (
    AssistantChatRequestSerializer,
    AssistantChatResponseSerializer,
    AssistantFeedbackRequestSerializer,
    AssistantFeedbackResponseSerializer,
    AssistantKeyTestRequestSerializer,
    AssistantKeyTestResponseSerializer,
    AssistantStatusSerializer,
    ChatSessionDetailSerializer,
    ChatSessionListSerializer,
    ChatSessionUpdateSerializer,
)
from .models import AssistantFeedback
from .services.api_key_resolver import resolve_llm_provider
from .services.assistant_service import AssistantService, format_sse
from .services.key_tester import evaluate_assistant_key
from .services.ledger_query import LedgerNotFoundError, LedgerQueryService
from .services.reference_date import get_reference_date
from .services.session_service import (
    append_user_message,
    build_llm_messages,
    create_session_with_user_message,
    feedback_map_for_messages,
    get_user_session,
    list_user_sessions,
    save_assistant_message,
    update_session_title,
)
from .throttles import AssistantChatThrottle

logger = logging.getLogger(__name__)


class EventStreamRenderer(BaseRenderer):
    media_type = 'text/event-stream'
    format = 'event-stream'
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class AssistantStatusView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: AssistantStatusSerializer},
        summary='获取 AI 账本助手状态',
    )
    def get(self, request):
        provider = resolve_llm_provider(request.user)
        ledger_service = LedgerQueryService(request.user)
        data = {
            'api_key_configured': provider.configured,
            'assistant_model': provider.model if provider.configured else '',
            'deep_think_supported': provider.supports_thinking_param,
            'ledger_exists': ledger_service.ledger_exists(),
            'ledger_path': ledger_service.ledger_path if ledger_service.ledger_exists() else '',
            'reference_date': get_reference_date(),
        }
        serializer = AssistantStatusSerializer(data)
        return Response(serializer.data)


class ChatSessionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return ChatSession.objects.filter(user=self.request.user).order_by('-modified')

    def get_serializer_class(self):
        if self.action == 'list':
            return ChatSessionListSerializer
        if self.action == 'partial_update':
            return ChatSessionUpdateSerializer
        return ChatSessionDetailSerializer

    def list(self, request, *args, **kwargs):
        search = request.query_params.get('search', '')
        sessions = list_user_sessions(request.user, search=search)
        serializer = ChatSessionListSerializer(sessions, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        session = self.get_object()
        message_ids = list(session.messages.values_list('id', flat=True))
        feedback_map = feedback_map_for_messages(request.user, message_ids)
        serializer = ChatSessionDetailSerializer(
            session,
            context={'feedback_map': feedback_map},
        )
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        session = self.get_object()
        serializer = ChatSessionUpdateSerializer(session, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        session = update_session_title(session, serializer.validated_data['title'])
        message_ids = list(session.messages.values_list('id', flat=True))
        feedback_map = feedback_map_for_messages(request.user, message_ids)
        detail = ChatSessionDetailSerializer(
            session,
            context={'feedback_map': feedback_map},
        )
        return Response(detail.data)

    def destroy(self, request, *args, **kwargs):
        session = self.get_object()
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssistantChatView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [AssistantChatThrottle]

    @extend_schema(
        request=AssistantChatRequestSerializer,
        responses={200: AssistantChatResponseSerializer},
        summary='AI 账本助手对话',
    )
    def post(self, request):
        serializer = AssistantChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        messages = [
            {'role': msg['role'], 'content': msg['content']}
            for msg in serializer.validated_data.get('messages') or []
        ]
        show_bql = serializer.validated_data.get('show_bql', False)
        deep_think = serializer.validated_data.get('deep_think', False)

        try:
            service = AssistantService(request.user, deep_think=deep_think)
            result = service.chat(messages, show_bql=show_bql)
        except LedgerNotFoundError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception('AI 助手调用失败')
            return Response(
                {'detail': f'AI 助手暂时不可用: {exc}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        response_data = {
            'reply': result.reply,
            'queries': [
                {'bql': q.bql, 'result_preview': q.result_preview}
                for q in result.queries
            ],
            'thinking': result.thinking,
            'reasoning': result.reasoning,
            'model': service.model,
        }
        return Response(AssistantChatResponseSerializer(response_data).data)


class AssistantChatStreamView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [AssistantChatThrottle]
    renderer_classes = [EventStreamRenderer]

    @extend_schema(
        request=AssistantChatRequestSerializer,
        responses={
            200: OpenApiResponse(
                description=(
                    'SSE 流式响应 (text/event-stream)。事件类型：'
                    'session, status, reasoning_delta, thinking_set, tool_start, tool_end, '
                    'delta, done, error'
                ),
            ),
        },
        summary='AI 账本助手对话（SSE 流式）',
    )
    def post(self, request):
        serializer = AssistantChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated = serializer.validated_data
        show_bql = validated.get('show_bql', False)
        deep_think = validated.get('deep_think', False)
        session_id = validated.get('session_id')
        content = validated.get('content')
        legacy_messages = validated.get('messages')

        provider = resolve_llm_provider(request.user)
        if not provider.configured:
            return Response(
                {'detail': '尚未配置助手模型，请在「输出配置」的账本助手中填写接口与密钥（Ollama 可省略密钥）。'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ledger_service = LedgerQueryService(request.user)
        if not ledger_service.ledger_exists():
            return Response(
                {'detail': '账本文件尚未创建，请先上传并解析账单。'},
                status=status.HTTP_404_NOT_FOUND,
            )

        persist_session = None
        user_message = None
        llm_messages = None

        if session_id is not None or content:
            text = (content or '').strip()
            try:
                if session_id is None:
                    persist_session, user_message = create_session_with_user_message(
                        request.user,
                        text,
                    )
                else:
                    persist_session = get_user_session(request.user, session_id)
                    user_message = append_user_message(persist_session, text)
                llm_messages = build_llm_messages(persist_session)
            except ChatSession.DoesNotExist:
                return Response({'detail': '会话不存在'}, status=status.HTTP_404_NOT_FOUND)
        else:
            llm_messages = [
                {'role': msg['role'], 'content': msg['content']}
                for msg in legacy_messages or []
            ]

        def event_stream() -> Iterator[str]:
            stream_service = AssistantService(request.user, deep_think=deep_think)
            if persist_session is not None and user_message is not None:
                yield format_sse('session', {
                    'id': str(persist_session.id),
                    'title': persist_session.title,
                    'user_message_id': str(user_message.id),
                })

            done_payload = None
            try:
                for event in stream_service._iter_chat_events(llm_messages, show_bql=show_bql):
                    if event.event == 'done' and persist_session is not None and user_message is not None:
                        assistant_message = save_assistant_message(
                            persist_session,
                            content=event.data['reply'],
                            thinking=event.data.get('thinking', ''),
                            reasoning=event.data.get('reasoning', ''),
                            queries=event.data.get('queries', []),
                        )
                        event.data = {
                            **event.data,
                            'session_id': str(persist_session.id),
                            'user_message_id': str(user_message.id),
                            'assistant_message_id': str(assistant_message.id),
                        }
                        done_payload = event.data
                    yield format_sse(event.event, event.data)
            except (ValueError, LedgerNotFoundError) as exc:
                yield format_sse('error', {'detail': str(exc)})
            except Exception as exc:
                logger.exception('AI 助手流式调用失败')
                yield format_sse('error', {'detail': f'AI 助手暂时不可用: {exc}'})

            if done_payload is None and persist_session is not None:
                logger.warning(
                    'Assistant stream ended without done event for session %s',
                    persist_session.id,
                )

        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response


class AssistantFeedbackView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=AssistantFeedbackRequestSerializer,
        responses={200: AssistantFeedbackResponseSerializer},
        summary='提交 AI 账本助手回复评价',
    )
    def post(self, request):
        serializer = AssistantFeedbackRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        message_id = data['message_id']
        rating = data.get('rating')

        if rating is None:
            AssistantFeedback.objects.filter(
                user=request.user,
                message_id=message_id,
            ).delete()
            response_data = {
                'message_id': message_id,
                'rating': None,
                'comment': '',
            }
            return Response(AssistantFeedbackResponseSerializer(response_data).data)

        feedback, _created = AssistantFeedback.objects.update_or_create(
            user=request.user,
            message_id=message_id,
            defaults={
                'rating': rating,
                'user_message': data['user_message'],
                'assistant_reply': data['assistant_reply'],
                'queries': data.get('queries', []),
                'comment': data.get('comment', ''),
            },
        )
        response_data = {
            'message_id': feedback.message_id,
            'rating': feedback.rating,
            'comment': feedback.comment,
        }
        return Response(AssistantFeedbackResponseSerializer(response_data).data)


class AssistantKeyTestView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [AssistantChatThrottle]

    @extend_schema(
        request=AssistantKeyTestRequestSerializer,
        responses={200: AssistantKeyTestResponseSerializer},
        summary='测试 Copilot API 密钥',
    )
    def post(self, request):
        serializer = AssistantKeyTestRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = evaluate_assistant_key(
            api_key=serializer.validated_data.get('api_key', ''),
            base_url=serializer.validated_data.get('base_url', ''),
            model=serializer.validated_data.get('model', ''),
        )
        return Response(AssistantKeyTestResponseSerializer(result.__dict__).data)
