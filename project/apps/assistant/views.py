import logging

from django.http import StreamingHttpResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from .serializers import (
    AssistantChatRequestSerializer,
    AssistantChatResponseSerializer,
    AssistantFeedbackRequestSerializer,
    AssistantFeedbackResponseSerializer,
    AssistantStatusSerializer,
)
from .models import AssistantFeedback
from .services.api_key_resolver import resolve_api_key
from .services.assistant_service import AssistantService
from .services.ledger_query import LedgerNotFoundError, LedgerQueryService
from .services.reference_date import get_reference_date
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
        resolved = resolve_api_key(request.user)
        ledger_service = LedgerQueryService(request.user)
        data = {
            'api_key_configured': resolved.api_key is not None,
            'api_key_source': resolved.source,
            'ledger_exists': ledger_service.ledger_exists(),
            'ledger_path': ledger_service.ledger_path if ledger_service.ledger_exists() else '',
            'reference_date': get_reference_date(),
        }
        serializer = AssistantStatusSerializer(data)
        return Response(serializer.data)


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
            for msg in serializer.validated_data['messages']
        ]
        show_bql = serializer.validated_data.get('show_bql', False)

        try:
            service = AssistantService(request.user)
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
            'api_key_source': result.api_key_source,
            'thinking': result.thinking,
            'reasoning': result.reasoning,
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
                    'status, reasoning_delta, thinking_set, tool_start, tool_end, '
                    'delta, done, error'
                ),
            ),
        },
        summary='AI 账本助手对话（SSE 流式）',
    )
    def post(self, request):
        serializer = AssistantChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        messages = [
            {'role': msg['role'], 'content': msg['content']}
            for msg in serializer.validated_data['messages']
        ]
        show_bql = serializer.validated_data.get('show_bql', False)

        resolved = resolve_api_key(request.user)
        if not resolved.api_key:
            return Response(
                {'detail': '未配置 DeepSeek API Key，请在「输出配置」中填写，或联系管理员配置平台 Key。'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ledger_service = LedgerQueryService(request.user)
        if not ledger_service.ledger_exists():
            return Response(
                {'detail': '账本文件尚未创建，请先上传并解析账单。'},
                status=status.HTTP_404_NOT_FOUND,
            )

        def event_stream():
            stream_service = AssistantService(request.user)
            yield from stream_service.chat_stream(messages, show_bql=show_bql)

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
