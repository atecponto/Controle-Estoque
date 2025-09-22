from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from inventario import views, views_cliente

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.root_redirect, name='root-redirect'),

    # Tela de navegação principal
    path('navegacao/', views.navegacao_view, name='navegacao'),

    # Autenticação
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('cadastro/', views.cadastro_usuario_view, name='cadastro'),

    # Módulo Estoque
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
    path('relatorios/', views.transacao_pdf_view, name='relatorio_transacoes'),
    
    # Módulo Usuários
    path('usuario/', views.gerenciamento_usuario, name='gerenciamento_usuario'),
    path('usuario/toggle-admin/<int:user_id>/', views.mudar_status_admin, name='mudar_status_admin'),
    path('usuario/toggle-ativo/<int:user_id>/', views.mudar_status_ativo, name='mudar_status_ativo'),
    path('usuario/excluir/<int:user_id>/', views.excluir_usuario, name='excluir_usuario'),

    # Módulo de Clientes e Ordem de Serviço
    path('clientes/', views_cliente.listar_clientes, name='listar_clientes'),
    path('clientes/novo/', views_cliente.criar_cliente, name='criar_cliente'),
    path('clientes/editar/<int:pk>/', views_cliente.editar_cliente, name='editar_cliente'),
    path('clientes/excluir/<int:pk>/', views_cliente.excluir_cliente, name='excluir_cliente'),
    path('clientes/detalhe/<int:pk>/', views_cliente.detalhe_cliente, name='detalhe_cliente'),
    
    # Sistemas
    path('sistemas/', views_cliente.listar_sistemas, name='listar_sistemas'),
    path('sistemas/novo/', views_cliente.criar_sistema, name='criar_sistema'),
    
    # Técnicos
    path('tecnicos/', views_cliente.listar_tecnicos, name='listar_tecnicos'),
    path('tecnicos/novo/', views_cliente.criar_tecnico, name='criar_tecnico'),

    # Agendamentos
    path('agendamentos/', views_cliente.listar_agendamentos, name='listar_agendamentos'),
    path('clientes/<int:cliente_pk>/agendar/', views_cliente.criar_agendamento, name='criar_agendamento'),
    path('agendamentos/finalizar/<int:pk>/', views_cliente.finalizar_agendamento, name='finalizar_agendamento'),

    # Ordens de Serviço (OS)
    path('clientes/<int:cliente_pk>/os/nova/', views_cliente.criar_ordem_de_servico, name='criar_os'),
    path('os/<int:pk>/', views_cliente.detalhe_ordem_de_servico, name='detalhe_os'),
    path('os/<int:pk>/fechar/', views_cliente.fechar_ordem_de_servico, name='fechar_os'),
    path('os/<int:pk>/imprimir/', views_cliente.imprimir_ordem_de_servico_pdf, name='imprimir_os'),
    
    # Redefinição de Senha
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='usuario/password_reset_done.html'), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='usuario/password_reset_confirm.html', success_url='/password-reset-complete/'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='usuario/password_reset_complete.html'), name='password_reset_complete'),
]