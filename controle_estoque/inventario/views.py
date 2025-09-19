import calendar
from datetime import datetime
from django.db import IntegrityError
from django.forms import ValidationError
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.models import LogEntry, ADDITION
from django.core.paginator import Paginator
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from .forms import CadastroUsuarioForm, CategoriaForm, DateFilterForm, ProdutoForm, TransacaoForm
from .models import Produto, Categoria, TipoTransacao, Transacao, Item
from django.conf import settings
from django.db.models.deletion import ProtectedError
from django.db.models import Sum
from .utils import render_to_pdf
from django.utils import timezone

def staff_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_staff and not request.user.is_superuser:
            messages.error(request, "Acesso negado. Você não tem permissão para realizar esta ação.")
            return redirect('listar_produtos')  # Redireciona para uma página de listagem
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('/produtos/')
    else:
        return redirect('/login/')

@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('listar_produtos')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bem-vindo, {username}!')
                next_url = request.GET.get('next', 'listar_produtos')
                return redirect(next_url)
        else:
            messages.error(request, 'Usuário ou senha inválidos.')
    else:
        form = AuthenticationForm()

    return render(request, 'usuario/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, 'Você foi desconectado com sucesso.')
    return redirect('login')

def cadastro_usuario_view(request):
    if request.method == 'POST':
        form = CadastroUsuarioForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Usuario {username} criado com sucesso!')
            return redirect('login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label}: {error}")
    else:
        form = CadastroUsuarioForm()
    
    return render(request, 'usuario/cadastro.html', {'form': form})

@require_http_methods(["GET", "POST"])
def password_reset_request(request):
    if request.method == "POST":
        password_reset_form = PasswordResetForm(request.POST)
        if password_reset_form.is_valid():
            email = password_reset_form.cleaned_data['email']
            associated_users = User.objects.filter(email=email)
            if associated_users.exists():
                user = associated_users.first()
                subject = "Redefinição de Senha - Atec Estoque"
                email_template_name = "usuario/password_reset_email.txt"
                
                context = {
                    "email": user.email,
                    'domain': request.get_host(),
                    'site_name': 'Inventário',
                    "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                    "user": user,
                    'token': default_token_generator.make_token(user),
                    'protocol': 'https' if request.is_secure() else 'http',
                }
                
                email_content = render_to_string(email_template_name, context)
                
                try:
                    # Verifica se as configurações de email existem
                    if not all([settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD]):
                        raise ValueError("Configurações de email não encontradas no settings.py")
                    
                    send_mail(
                        subject=subject,
                        message=email_content,
                        from_email=settings.EMAIL_HOST_USER,  # Usa diretamente do settings
                        recipient_list=[user.email],
                        fail_silently=False
                    )
                    messages.success(request, 'Um email com instruções foi enviado para sua caixa de entrada.')
                    return redirect('password_reset_done')
                
                except Exception as e:
                    error_message = f"""Houve um problema ao enviar o email. Verifique:
                        1. As configurações de email no servidor
                        2. Se você habilitou 'Aplicativos menos seguros' ou criou uma 'Senha de App'
                        3. Sua conexão com a internet
                        Erro detalhado: {str(e)}"""
                    
                    # Log do erro para debug
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Erro ao enviar email de reset: {str(e)}")
                    
                    messages.error(request, error_message)
                    return redirect('password_reset')
            else:
                messages.error(request, 'Este email não está cadastrado em nosso sistema.')
    else:
        password_reset_form = PasswordResetForm()
    
    return render(
        request=request,
        template_name="usuario/password_reset.html",
        context={"password_reset_form": password_reset_form}
    )

@login_required
def listar_categorias(request):
    categorias = Categoria.objects.all()
    
    busca = request.GET.get('busca')
    if busca:
        categorias = categorias.filter(nome__icontains=busca)
    
    context = {
        'categorias': categorias,
    }
    return render(request, 'categoria/listar.html', context)

@login_required
@staff_required
def criar_categoria(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            categoria = form.save()
            messages.success(request, f'Categoria "{categoria.nome}" criada com sucesso!')
            return redirect('listar_categorias')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label}: {error}")
    else:
        form = CategoriaForm()
    
    context = {'form': form}
    return render(request, 'categoria/form.html', context)

@login_required
@staff_required
def editar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(categoria).pk,
                object_id=categoria.id,
                object_repr=str(categoria),
                action_flag=ADDITION,
                change_message='Categoria criada'
            )
            categoria = form.save()
            messages.success(request, f'Categoria "{categoria.nome}" atualizada com sucesso!')
            return redirect('listar_categorias')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label}: {error}")
    else:
        form = CategoriaForm(instance=categoria)
    
    context = {
        'form': form,
        'categoria': categoria,
    }
    return render(request, 'categoria/form.html', context)

@login_required
@staff_required
def excluir_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    
    produtos_vinculados = categoria.produto_set.exists()
    
    if produtos_vinculados:
        messages.error(request, f'Não é possível excluir a categoria "{categoria.nome}" porque existem produtos vinculados a ela.')
        return redirect('listar_categorias')
    
    if request.method == 'POST':
        nome_categoria = categoria.nome
        categoria.delete()
        messages.success(request, f'Categoria "{nome_categoria}" excluída com sucesso!')
        return redirect('listar_categorias')
    
    context = {'categoria': categoria}
    return render(request, 'categoria/confirmar_exclusao.html', context)

@login_required
def listar_produtos(request):
    produtos = Produto.objects.filter(ativo = 0).select_related('categoria')
    
    categoria_id = request.GET.get('categoria')
    if categoria_id:
        produtos = produtos.filter(categoria_id=categoria_id)
    
    busca = request.GET.get('busca')
    if busca:
        produtos = produtos.filter(nome__icontains=busca)
    
    paginator = Paginator(produtos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
                                  
    context = {
        'produtos': produtos,
        'categorias': Categoria.objects.all,
        'page_obj': page_obj,
    }
    return render(request, 'produto/listar.html', context)

@login_required
@staff_required
def criar_produto(request):
    if request.method == 'POST':
        form = ProdutoForm(request.POST)
        if form.is_valid():
            produto = form.save(commit=False)
            produto.usuario_responsavel = request.user
            produto.save()
            messages.success(request, f'Produto "{produto.nome}" criado com sucesso!')
            return redirect('listar_produtos')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label}: {error}")
    else:
        form = ProdutoForm()
    
    context = {'form': form}
    return render(request, 'produto/form.html', context)

@login_required
@staff_required
def editar_produto(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    
    if request.method == 'POST':
        form = ProdutoForm(request.POST, instance=produto)
        if form.is_valid():
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(produto).pk,
                object_id=produto.id,
                object_repr=str(produto),
                action_flag=ADDITION,
                change_message='Produto criado'
            )
            produto = form.save(commit=False)
            produto.usuario_responsavel = request.user
            produto.save()
            messages.success(request, f'Produto "{produto.nome}" atualizado com sucesso!')
            return redirect('listar_produtos')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label}: {error}")
    else:
        form = ProdutoForm(instance=produto)
    
    context = {
        'form': form,
        'produto': produto,
    }
    return render(request, 'produto/form.html', context)

@login_required
@staff_required
def excluir_produto(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    
    if request.method == 'POST':
        nome_produto = produto.nome
        tem_transacoes = Transacao.objects.filter(produto=produto).exists()
        tem_item = Item.objects.filter(produto=produto, disponivel=1).exists()
        
        if tem_item:
            messages.warning(
                request, 
                f'Produto "{nome_produto}" possuí estoque, produto não pode ser excluído '
            )

        elif tem_transacoes:
            produto.ativo = 1
            produto.save()
            messages.warning(request, f'Produto "{nome_produto}" excluído com sucesso!')
            
        else:
            try:
                produto.delete()
                messages.success(request, f'Produto "{nome_produto}" excluído com sucesso!')
            except IntegrityError:
                messages.warning(
                    request, 
                    f'Erro ao tentar excluir produto "{nome_produto}"'
                )
        
        return redirect('listar_produtos')
    
    context = {
        'produto': produto,
    }
    return render(request, 'produto/confirmar_exclusao.html', context)

@login_required
def listar_transacao(request):
    transacoes = Transacao.objects.all().select_related(
        'tipo_transacao', 'usuario', 'produto'
    ).order_by('-data')
    
    produto_id = request.GET.get('produto')
    tipo_transacao = request.GET.get('tipo')
    
    if produto_id:
        transacoes = transacoes.filter(produto_id=produto_id)
    
    if tipo_transacao:
        transacoes = transacoes.filter(tipo_transacao_id=tipo_transacao)
    
    paginator = Paginator(transacoes, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'transacoes': page_obj,
        'produtos': Produto.objects.all(),
        'tipos_transacao': TipoTransacao.objects.all(),
        'page_obj': page_obj,
    }
    return render(request, 'transacao/listar.html', context)

@login_required
@staff_required
def criar_transacao(request):
    if request.method == 'POST':
        form = TransacaoForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Transação registrada com sucesso!")
                return redirect('listar_produtos')
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
    else:
        form = TransacaoForm(user=request.user)
    
    return render(request, 'transacao/form.html', {'form': form})

@login_required
def gerenciamento_usuario(request):
    if request.user.is_superuser:
        users = User.objects.all().order_by('-date_joined')
        return render(request, 'usuario/usuario_admin.html', {'users': users})
    else:
        return render(request, 'usuario/usuario.html', {'user': request.user})

@require_http_methods(["POST"])
@login_required
@staff_required
def mudar_status_admin(request, user_id):
    """Toggle admin status for a user"""
    user_to_modify = get_object_or_404(User, id=user_id)
    
    # Prevent modifying yourself
    if user_to_modify == request.user:
        messages.error(request, "Você não pode modificar seu próprio status de administrador!")
        return redirect('gerenciamento_usuario')
    
    # Toggle the status
    user_to_modify.is_superuser = not user_to_modify.is_superuser
    user_to_modify.is_staff = user_to_modify.is_superuser  # Typically staff follows superuser status
    user_to_modify.save()
    
    action = "concedido" if user_to_modify.is_superuser else "removido"
    messages.success(request, f"Privilégios de administrador {action} para {user_to_modify.username}!")
    return redirect('gerenciamento_usuario')

@require_http_methods(["POST"])
@login_required
@staff_required
def mudar_status_ativo(request, user_id):
    """Toggle active status for a user"""
    user_to_modify = get_object_or_404(User, id=user_id)
    
    # Prevent modifying yourself
    if user_to_modify == request.user:
        messages.error(request, "Você não pode modificar seu próprio status de ativo!")
        return redirect('gerenciamento_usuario')
    
    # Toggle the status
    user_to_modify.is_active = not user_to_modify.is_active
    user_to_modify.save()
    
    action = "ativado" if user_to_modify.is_active else "desativado"
    messages.success(request, f"Usuário {user_to_modify.username} {action} com sucesso!")
    return redirect('gerenciamento_usuario')

@require_http_methods(["POST"])
@login_required
@staff_required
def excluir_usuario(request, user_id):
    user_to_delete = get_object_or_404(User, id=user_id)
    
    # Prevent deleting yourself
    if user_to_delete == request.user:
        messages.error(request, "Você não pode deletar sua própria conta!")
        return redirect('gerenciamento_usuario')
    
    try:
        username = user_to_delete.username
        user_to_delete.delete()
        messages.success(request, f"Usuário {username} deletado permanentemente!")
    except ProtectedError as e:
        protected_objects = list(e.protected_objects)
        messages.error(request, 
            f"Não é possível deletar {user_to_delete.username} porque existem registros vinculados: "
            f"{len(protected_objects)} transações. Em vez disso, desative a conta.")
        return redirect('gerenciamento_usuario')
    
    return redirect('gerenciamento_usuario')


def transacao_pdf_view(request):
    if request.method == 'POST':
        form = DateFilterForm(request.POST)
        if form.is_valid():
            month = int(form.cleaned_data['month'])
            year = int(form.cleaned_data['year'])
            
            _, last_day = calendar.monthrange(year, month)
            
            start_date = timezone.make_aware(datetime(year, month, 1))
            end_date = timezone.make_aware(datetime(year, month, last_day, 23, 59, 59))
            
            transacoes = Transacao.objects.filter(
                data__gte=start_date,
                data__lte=end_date
            ).order_by('data')
            
            total_entradas = transacoes.filter(
                tipo_transacao__entrada=True
            ).aggregate(Sum('quantidade'))['quantidade__sum'] or 0
            
            total_saidas = transacoes.filter(
                tipo_transacao__entrada=False
            ).aggregate(Sum('quantidade'))['quantidade__sum'] or 0
            
            saldo = total_entradas - total_saidas

            month_names = {
                1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
                5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
                9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
            }
            month_name = month_names[month]
            
            context = {
                'transacoes': transacoes,
                'month': month,
                'year': year,
                'month_name': month_name,
                'total_entradas': total_entradas,
                'total_saidas': total_saidas,
                'saldo': saldo,
                'data_geracao': timezone.now()
            }
            
            pdf = render_to_pdf('pdf_template.html', context)
            
            if pdf:
                response = HttpResponse(pdf, content_type='application/pdf')
                filename = f"transacoes_{month}_{year}.pdf"
                content = f"attachment; filename={filename}"
                response['Content-Disposition'] = content
                return response
            
            return HttpResponse("Error generating PDF", status=500)
    else:
        current_date = timezone.now()
        form = DateFilterForm(initial={
            'month': current_date.month,
            'year': current_date.year
        })
    
    return render(request, 'relatorio/relatorio_form.html', {'form': form})

