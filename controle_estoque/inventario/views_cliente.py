from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.utils import timezone

from .models import Cliente, Sistema, Tecnico, Agendamento
from .forms import ClienteForm, SistemaForm, TecnicoForm, AgendamentoForm, FinalizarAgendamentoForm

# ==================================
# Views para Clientes
# ==================================
@login_required
def listar_clientes(request):
    clientes = Cliente.objects.select_related('sistema').all()
    sistemas = Sistema.objects.all()

    busca = request.GET.get('busca')
    sistema_id = request.GET.get('sistema')

    if busca:
        clientes = clientes.filter(
            Q(razao_social__icontains=busca) |
            Q(fantasia__icontains=busca) |
            Q(cnpj__icontains=busca)
        )
    
    if sistema_id:
        clientes = clientes.filter(sistema_id=sistema_id)
    
    context = {
        'page_obj': clientes,
        'sistemas': sistemas
    }
    return render(request, 'cliente/listar_clientes.html', context)

@login_required
def detalhe_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    agendamentos = Agendamento.objects.filter(cliente=cliente)
    context = {
        'cliente': cliente,
        'agendamentos': agendamentos,
    }
    return render(request, 'cliente/detalhe_cliente.html', context)

@login_required
def criar_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente criado com sucesso!')
            return redirect('listar_clientes')
    else:
        form = ClienteForm()
    return render(request, 'cliente/form_cliente.html', {'form': form, 'model_name': 'Cliente', 'cancel_url': reverse_lazy('listar_clientes')})

@login_required
def editar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente atualizado com sucesso!')
            return redirect('listar_clientes')
    else:
        form = ClienteForm(instance=cliente)
    return render(request, 'cliente/form_cliente.html', {'form': form, 'object': cliente, 'model_name': 'Cliente', 'cancel_url': reverse_lazy('listar_clientes')})

@login_required
def excluir_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        cliente.delete()
        messages.success(request, 'Cliente excluído com sucesso!')
        return redirect('listar_clientes')
    return render(request, 'cliente/confirmar_exclusao.html', {'object': cliente, 'model_name': 'Cliente', 'cancel_url': reverse_lazy('listar_clientes')})

# ==================================
# Views para Sistemas
# ==================================
@login_required
def listar_sistemas(request):
    sistemas = Sistema.objects.all()
    return render(request, 'cliente/listar_sistemas.html', {'sistemas': sistemas})

@login_required
def criar_sistema(request):
    if request.method == 'POST':
        form = SistemaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sistema criado com sucesso!')
            return redirect('listar_sistemas')
    else:
        form = SistemaForm()
    return render(request, 'cliente/form_sistema.html', {'form': form, 'model_name': 'Sistema', 'cancel_url': reverse_lazy('listar_sistemas')})
    
# ==================================
# Views para Técnicos
# ==================================
@login_required
def listar_tecnicos(request):
    tecnicos = Tecnico.objects.all()
    return render(request, 'cliente/listar_tecnicos.html', {'tecnicos': tecnicos})

@login_required
def criar_tecnico(request):
    if request.method == 'POST':
        form = TecnicoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Técnico criado com sucesso!')
            return redirect('listar_tecnicos')
    else:
        form = TecnicoForm()
    return render(request, 'cliente/form_tecnico.html', {'form': form, 'model_name': 'Técnico', 'cancel_url': reverse_lazy('listar_tecnicos')})

# ==================================
# Views para Agendamentos
# ==================================
@login_required
def listar_agendamentos(request):
    agendamentos = Agendamento.objects.filter(situacao='AGENDADO').select_related('cliente', 'tecnico')
    return render(request, 'cliente/listar_agendamentos.html', {'agendamentos': agendamentos})

@login_required
def criar_agendamento(request, cliente_pk):
    cliente = get_object_or_404(Cliente, pk=cliente_pk)
    if request.method == 'POST':
        form = AgendamentoForm(request.POST)
        if form.is_valid():
            agendamento = form.save(commit=False)
            agendamento.cliente = cliente
            agendamento.save()
            messages.success(request, 'Agendamento criado com sucesso!')
            return redirect('detalhe_cliente', pk=cliente.pk)
    else:
        form = AgendamentoForm()
    return render(request, 'cliente/form_agendamento.html', {'form': form, 'cliente': cliente})

@login_required
def finalizar_agendamento(request, pk):
    agendamento = get_object_or_404(Agendamento, pk=pk)
    if request.method == 'POST':
        form = FinalizarAgendamentoForm(request.POST, instance=agendamento)
        if form.is_valid():
            agendamento = form.save(commit=False)
            agendamento.data_resolvido = timezone.now()
            agendamento.save()
            messages.success(request, 'Agendamento atualizado com sucesso!')
            return redirect('detalhe_cliente', pk=agendamento.cliente.id)
    else:
        form = FinalizarAgendamentoForm(instance=agendamento)
    return render(request, 'cliente/form_agendamento.html', {'form': form, 'cliente': agendamento.cliente, 'finalizando': True})