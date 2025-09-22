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

# IMPORTAÇÕES PARA GERAR GRÁFICOS
import matplotlib
matplotlib.use('Agg')  # Configura o Matplotlib para não usar interface gráfica
import matplotlib.pyplot as plt
import io
import base64
from django.db.models.functions import Coalesce


# FUNÇÃO AUXILIAR PARA CRIAR GRÁFICOS DE PIZZA
def generate_pie_chart_image(data, title):
    """Gera um gráfico de pizza como uma imagem base64."""
    if not data:
        return None

    labels = [item['produto__nome'] for item in data]
    sizes = [item['total_quantidade'] for item in data]

    fig, ax = plt.subplots(figsize=(6, 4)) # Tamanho ajustado para PDF
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 8})
    ax.axis('equal')  # Garante que o gráfico seja um círculo.
    
    plt.title(title, fontsize=12)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    
    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()
    
    return f"data:image/png;base64,{image_base64}"


def staff_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_staff and not request.user.is_superuser:
            messages.error(request, "Acesso negado. Você não tem permissão para realizar esta ação.")
            return redirect('listar_produtos')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@login_required
def navegacao_view(request):
    return render(request, 'navegacao/navegacao.html')

def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('navegacao')
    else:
        return redirect('/login/')

@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('navegacao')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bem-vindo, {username}!')
                next_url = request.GET.get('next', 'navegacao')
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
                    if not all([settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD]):
                        raise ValueError("Configurações de email não encontradas no settings.py")
                    
                    send_mail(subject, email_content, settings.EMAIL_HOST_USER, [user.email], fail_silently=False)
                    messages.success(request, 'Um email com instruções foi enviado para sua caixa de entrada.')
                    return redirect('password_reset_done')
                
                except Exception as e:
                    error_message = f"Houve um problema ao enviar o email. Erro: {str(e)}"
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Erro ao enviar email de reset: {str(e)}")
                    messages.error(request, error_message)
            else:
                messages.error(request, 'Este email não está cadastrado em nosso sistema.')
    else:
        password_reset_form = PasswordResetForm()
    
    return render(request, "usuario/password_reset.html", {"password_reset_form": password_reset_form})

@login_required
def listar_categorias(request):
    categorias = Categoria.objects.all()
    if 'busca' in request.GET:
        categorias = categorias.filter(nome__icontains=request.GET['busca'])
    return render(request, 'categoria/listar.html', {'categorias': categorias})

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
        form = CategoriaForm()
    return render(request, 'categoria/form.html', {'form': form})

@login_required
@staff_required
def editar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            categoria = form.save()
            messages.success(request, f'Categoria "{categoria.nome}" atualizada com sucesso!')
            return redirect('listar_categorias')
    else:
        form = CategoriaForm(instance=categoria)
    return render(request, 'categoria/form.html', {'form': form, 'categoria': categoria})

@login_required
@staff_required
def excluir_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if categoria.produto_set.exists():
        messages.error(request, f'Não é possível excluir a categoria "{categoria.nome}" porque existem produtos vinculados a ela.')
        return redirect('listar_categorias')
    
    if request.method == 'POST':
        nome_categoria = categoria.nome
        categoria.delete()
        messages.success(request, f'Categoria "{nome_categoria}" excluída com sucesso!')
        return redirect('listar_categorias')
    
    return render(request, 'categoria/confirmar_exclusao.html', {'categoria': categoria})

@login_required
def listar_produtos(request):
    produtos = Produto.objects.filter(ativo=0).select_related('categoria')
    if 'categoria' in request.GET and request.GET['categoria']:
        produtos = produtos.filter(categoria_id=request.GET['categoria'])
    if 'busca' in request.GET:
        produtos = produtos.filter(nome__icontains=request.GET['busca'])
    
    paginator = Paginator(produtos, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'produto/listar.html', {'page_obj': page_obj, 'categorias': Categoria.objects.all()})

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
        form = ProdutoForm()
    return render(request, 'produto/form.html', {'form': form})

@login_required
@staff_required
def editar_produto(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    if request.method == 'POST':
        form = ProdutoForm(request.POST, instance=produto)
        if form.is_valid():
            produto = form.save(commit=False)
            produto.usuario_responsavel = request.user
            produto.save()
            messages.success(request, f'Produto "{produto.nome}" atualizado com sucesso!')
            return redirect('listar_produtos')
    else:
        form = ProdutoForm(instance=produto)
    return render(request, 'produto/form.html', {'form': form, 'produto': produto})

@login_required
@staff_required
def excluir_produto(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    if request.method == 'POST':
        nome_produto = produto.nome
        if Item.objects.filter(produto=produto, disponivel=True).exists():
            messages.warning(request, f'Produto "{nome_produto}" possui estoque e não pode ser excluído.')
        elif Transacao.objects.filter(produto=produto).exists():
            produto.ativo = 1
            produto.save()
            messages.warning(request, f'Produto "{nome_produto}" possui transações e foi inativado.')
        else:
            produto.delete()
            messages.success(request, f'Produto "{nome_produto}" excluído com sucesso!')
        return redirect('listar_produtos')
    return render(request, 'produto/confirmar_exclusao.html', {'produto': produto})

@login_required
def listar_transacao(request):
    transacoes = Transacao.objects.select_related('tipo_transacao', 'usuario', 'produto').order_by('-data')
    if 'produto' in request.GET and request.GET['produto']:
        transacoes = transacoes.filter(produto_id=request.GET['produto'])
    if 'tipo' in request.GET and request.GET['tipo']:
        transacoes = transacoes.filter(tipo_transacao_id=request.GET['tipo'])
    
    paginator = Paginator(transacoes, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'transacao/listar.html', {'page_obj': page_obj, 'produtos': Produto.objects.all(), 'tipos_transacao': TipoTransacao.objects.all()})

@login_required
@staff_required
def criar_transacao(request):
    if request.method == 'POST':
        form = TransacaoForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Transação registrada com sucesso!")
            return redirect('listar_produtos')
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
    user_to_modify = get_object_or_404(User, id=user_id)
    if user_to_modify != request.user:
        user_to_modify.is_superuser = not user_to_modify.is_superuser
        user_to_modify.is_staff = user_to_modify.is_superuser
        user_to_modify.save()
        messages.success(request, f"Status de admin de {user_to_modify.username} alterado.")
    return redirect('gerenciamento_usuario')

@require_http_methods(["POST"])
@login_required
@staff_required
def mudar_status_ativo(request, user_id):
    user_to_modify = get_object_or_404(User, id=user_id)
    if user_to_modify != request.user:
        user_to_modify.is_active = not user_to_modify.is_active
        user_to_modify.save()
        messages.success(request, f"Status de atividade de {user_to_modify.username} alterado.")
    return redirect('gerenciamento_usuario')

@require_http_methods(["POST"])
@login_required
@staff_required
def excluir_usuario(request, user_id):
    user_to_delete = get_object_or_404(User, id=user_id)
    if user_to_delete != request.user:
        try:
            user_to_delete.delete()
            messages.success(request, f"Usuário {user_to_delete.username} deletado.")
        except ProtectedError:
            messages.error(request, f"Não é possível deletar {user_to_delete.username} devido a registros vinculados.")
    return redirect('gerenciamento_usuario')

def transacao_pdf_view(request):
    if request.method == 'POST':
        form = DateFilterForm(request.POST)
        if form.is_valid():
            month = int(form.cleaned_data['month'])
            year = int(form.cleaned_data['year'])
            
            start_date = timezone.make_aware(datetime(year, month, 1))
            _, last_day = calendar.monthrange(year, month)
            end_date = timezone.make_aware(datetime(year, month, last_day, 23, 59, 59))
            
            transacoes = Transacao.objects.filter(data__range=(start_date, end_date)).order_by('data')
            
            entradas_data = list(transacoes.filter(tipo_transacao__entrada=True)
                .values('produto__nome')
                .annotate(total_quantidade=Sum('quantidade'))
                .order_by('-total_quantidade'))

            saidas_data = list(transacoes.filter(tipo_transacao__entrada=False)
                .values('produto__nome')
                .annotate(total_quantidade=Sum('quantidade'))
                .order_by('-total_quantidade'))

            chart_entradas_b64 = generate_pie_chart_image(entradas_data, f"Entradas de Produtos - {month}/{year}")
            chart_saidas_b64 = generate_pie_chart_image(saidas_data, f"Saídas de Produtos - {month}/{year}")
            
            total_entradas = sum(item['total_quantidade'] for item in entradas_data)
            total_saidas = sum(item['total_quantidade'] for item in saidas_data)

            month_name = calendar.month_name[month]
            
            context = {
                'transacoes': transacoes,
                'month_name': month_name,
                'year': year,
                'total_entradas': total_entradas,
                'total_saidas': total_saidas,
                'data_geracao': timezone.now(),
                'chart_entradas_b64': chart_entradas_b64,
                'chart_saidas_b64': chart_saidas_b64,
            }
            
            pdf = render_to_pdf('pdf_template.html', context)
            if pdf:
                response = HttpResponse(pdf, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="relatorio_{month}_{year}.pdf"'
                return response
            return HttpResponse("Erro ao gerar o PDF.", status=500)
    else:
        form = DateFilterForm(initial={'month': timezone.now().month, 'year': timezone.now().year})
    
    return render(request, 'relatorio/relatorio_form.html', {'form': form})