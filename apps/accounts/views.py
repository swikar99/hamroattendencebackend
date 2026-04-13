from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes as perm_dec
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import update_session_auth_hash
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import CustomUser
from .serializers import (
    CustomTokenObtainPairSerializer, UserSerializer,
    RegisterSerializer, ChangePasswordSerializer
)
from .permissions import IsOrgAdminOrAbove, IsHROrAbove, IsSameOrg


class CustomTokenObtainPairView(TokenObtainPairView):
    """Login — returns access+refresh tokens plus user info."""
    serializer_class = CustomTokenObtainPairSerializer


class UserViewSet(viewsets.ModelViewSet):
    serializer_class   = UserSerializer
    permission_classes = [IsAuthenticated, IsSameOrg]
    queryset           = CustomUser.objects.all()
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['email', 'first_name', 'last_name', 'employee_id']
    ordering_fields    = ['email', 'first_name', 'joining_date']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'superadmin':
            return CustomUser.objects.all()
        return CustomUser.objects.filter(organization=user.organization).select_related('organization', 'department', 'manager')

    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            return [IsAuthenticated(), IsHROrAbove()]
        if self.action in ['update', 'partial_update']:
            return [IsAuthenticated(), IsSameOrg()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Return logged-in user's full profile."""
        return Response(UserSerializer(request.user, context={'request': request}).data)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            return Response({'message': 'Password changed successfully.'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def by_department(self, request):
        dept_id = request.query_params.get('department')
        qs = self.get_queryset()
        if dept_id:
            qs = qs.filter(department_id=dept_id)
        return Response(UserSerializer(qs, many=True, context={'request': request}).data)

    @action(detail=False, methods=['get'])
    def by_role(self, request):
        role = request.query_params.get('role')
        qs = self.get_queryset()
        if role:
            qs = qs.filter(role=role)
        return Response(UserSerializer(qs, many=True, context={'request': request}).data)


@extend_schema(
    request=RegisterSerializer,
    responses={
        201: OpenApiResponse(description='Registration successful'),
        400: OpenApiResponse(description='Validation errors'),
    },
    tags=['Auth'],
    summary='Register a new user (email domain determines organisation)',
)
@api_view(['POST'])
@perm_dec([AllowAny])
def register_view(request):
    """Public registration — email domain determines organization."""
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            'message':      'Registration successful.',
            'email':        user.email,
            'organization': user.organization.name if user.organization else None,
            'org_type':     user.organization.get_type_display() if user.organization else None,
            'role':         user.role,
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
