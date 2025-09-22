from django import forms
from django.forms import ValidationError
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
import calendar
from django.utils import timezone

# LINHA DE IMPORTAÇÃO COMPLETA COM TODOS OS MODELS DO PROJETO
from .models import (Produto, Categoria, TipoTransacao, Transacao, Item, 
                     Sistema, Tecnico, Cliente, Agendamento, OrdemDeServico)

class DateFilterForm(forms.Form):
    MONTH_CHOICES = [(m, calendar.month_name[m]) for m in range(1, 13)]
    YEAR_CHOICES = [(y, y) for y in range(2020, timezone.now().year + 2)]
    month = forms.ChoiceField(choices=MONTH_CHOICES, label="Mês")
    year = forms.ChoiceField(choices=YEAR_CHOICES, label="Ano")

class CadastroUsuarioForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True, label="Nome")
    last_name = forms.CharField(max_length=30, required=True, label="Sobrenome")

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = ['nome', 'descricao', 'categoria']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        self.fields['categoria'].queryset = Categoria.objects.all()

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nome', 'descricao']
        widgets = { 'descricao': forms.Textarea(attrs={'rows': 3}), }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class TransacaoForm(forms.ModelForm):
    produto = forms.ModelChoiceField(queryset=Produto.objects.all(), label="Produto")
    lote = forms.CharField(required=False, label="Número do Lote", help_text="Obrigatório para entradas de estoque")
    
    class Meta:
        model = Transacao
        fields = ['produto', 'tipo_transacao', 'quantidade', 'observacoes']
        widgets = { 'observacoes': forms.Textarea(attrs={'rows': 3}), }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        self.fields['tipo_transacao'].queryset = TipoTransacao.objects.all()
    
    def clean(self):
        cleaned_data = super().clean()
        tipo_transacao = cleaned_data.get('tipo_transacao')
        produto = cleaned_data.get('produto')
        quantidade = cleaned_data.get('quantidade')
        lote = cleaned_data.get('lote')
        
        if tipo_transacao and tipo_transacao.entrada:
            if not lote:
                raise ValidationError({'lote': "Informe o número do lote para entrada de estoque"})
        
        if tipo_transacao and not tipo_transacao.entrada and produto and quantidade:
            disponivel = produto.estoque_total
            if disponivel < quantidade:
                raise ValidationError(f"Estoque insuficiente. Disponível: {disponivel}, Requerido: {quantidade}")
        return cleaned_data
    
    def save(self, commit=True):
        transacao = super().save(commit=False)
        transacao.usuario = self.user
        transacao.produto = self.cleaned_data['produto']
        if commit:
            transacao.save()
            self.processar_itens(transacao)
        return transacao
    
    def processar_itens(self, transacao):
        lote = self.cleaned_data.get('lote')
        produto = self.cleaned_data.get('produto')
        quantidade = self.cleaned_data['quantidade']
        
        if transacao.tipo_transacao.entrada:
            itens = [ Item(produto=produto, transacao=transacao, lote=lote, disponivel=True) for _ in range(quantidade) ]
            Item.objects.bulk_create(itens)
        else:
            itens = Item.objects.filter(produto=produto, disponivel=True).order_by('data_criacao')[:quantidade]
            if itens.count() < quantidade:
                raise ValidationError("Estoque insuficiente para completar a transação")
            for item in itens:
                item.disponivel = False
                item.transacao = transacao
                item.save()

# ### FORMS DO MÓDULO DE CLIENTES ###

class SistemaForm(forms.ModelForm):
    class Meta:
        model = Sistema
        fields = ['nome', 'descricao']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

class TecnicoForm(forms.ModelForm):
    class Meta:
        model = Tecnico
        fields = ['nome']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome'].widget.attrs.update({'class': 'form-control'})

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            'razao_social', 'fantasia', 'tipo_contrato', 'contato', 'cnpj', 'inscricao_estadual',
            'endereco', 'bairro', 'telefone', 'cep', 'cidade', 'estado', 
            'email', 'sistema', 'observacoes'
        ]
        widgets = { 'observacoes': forms.Textarea(attrs={'rows': 3}) }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in ['sistema', 'tipo_contrato']:
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})

class AgendamentoForm(forms.ModelForm):
    class Meta:
        model = Agendamento
        fields = ['tecnico', 'descricao', 'data_agendamento', 'hora_agendamento']
        widgets = {
            'data_agendamento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'hora_agendamento': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tecnico'].widget.attrs.update({'class': 'form-select'})

class FinalizarAgendamentoForm(forms.ModelForm):
    class Meta:
        model = Agendamento
        fields = ['laudo_tecnico', 'atendido_por', 'situacao']
        widgets = {
            'laudo_tecnico': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['atendido_por'].widget.attrs.update({'class': 'form-select'})
        self.fields['situacao'].widget.attrs.update({'class': 'form-select'})
        self.fields['situacao'].choices = [('CONCLUIDO', 'Concluído'), ('CANCELADO', 'Cancelado')]

class OrdemDeServicoAberturaForm(forms.ModelForm):
    class Meta:
        model = OrdemDeServico
        fields = ['tecnico_responsavel', 'problema_relatado']
        widgets = {
            'problema_relatado': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tecnico_responsavel'].widget.attrs.update({'class': 'form-select'})
        self.fields['tecnico_responsavel'].label = "Técnico Responsável"
        self.fields['problema_relatado'].label = "Problema Relatado"

class OrdemDeServicoFechamentoForm(forms.ModelForm):
    class Meta:
        model = OrdemDeServico
        fields = ['solucao_aplicada', 'status', 'valor']
        widgets = {
            'solucao_aplicada': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].widget.attrs.update({'class': 'form-select'})
        self.fields['valor'].widget.attrs.update({'class': 'form-control'})
        self.fields['solucao_aplicada'].label = "Solução Aplicada / Laudo Técnico"
        self.fields['status'].choices = [('CONCLUIDA', 'Concluída'), ('CANCELADA', 'Cancelada')]