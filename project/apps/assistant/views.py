import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from .serializers import (
    AssistantChatRequestSerializer,
    AssistantChatResponseSerializer,
    AssistantStatusSerializer,
)
from .services.api_key_resolver import resolve_api_key
from .services.assistant_service import AssistantService
from .services.ledger_query import LedgerNotFoundError, LedgerQueryService
from .throttles import AssistantChatThrottle

logger = logging.getLogger(__name__)


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
        }
        return Response(AssistantChatResponseSerializer(response_data).data)
