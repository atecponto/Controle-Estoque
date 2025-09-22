from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from inventario import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.root_redirect, name='root-redirect'),

    # Nova tela de navegação principal
    path('navegacao/', views.navegacao_view, name='navegacao'),

    # Autenticação
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('cadastro/', views.cadastro_usuario_view, name='cadastro'),

    # Módulos
    path('produtos/', views.listar_produtos, name='listar_produtos'),
    path('produtos/novo/', views.criar_produto, name='criar_produto'),
    path('produtos/editar/<int:pk>/', views.editar_produto, name='editar_produto'),
    path('produtos/excluir/<int:pk>/', views.excluir_produto, name='excluir_produto'),
    path('categorias/', views.listar_categorias, name='listar_categorias'),
    path('categorias/novo/', views.criar_categoria, name='criar_categoria'),
    path('categorias/editar/<int:pk>/', views.editar_categoria, name='editar_categoria'),
    path('categorias/excluir/<int:pk>/', views.excluir_categoria, name='excluir_categoria'),
    path('transacao/',views.listar_transacao, name='listar_transacao'),
    path('transacao/novo/', views.criar_transacao, name='criar_transacao'),
    path('usuario/', views.gerenciamento_usuario, name='gerenciamento_usuario'),
    path('usuario/toggle-admin/<int:user_id>/', views.mudar_status_admin, name='mudar_status_admin'),
    path('usuario/toggle-ativo/<int:user_id>/', views.mudar_status_ativo, name='mudar_status_ativo'),
    path('usuario/excluir/<int:user_id>/', views.excluir_usuario, name='excluir_usuario'),
    path('relatorios/', views.transacao_pdf_view, name='relatorio_transacoes'),
    
    # Redefinição de Senha
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='usuario/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='usuario/password_reset_confirm.html',
             success_url='/password-reset-complete/'
         ), 
         name='password_reset_confirm'),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='usuario/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
]