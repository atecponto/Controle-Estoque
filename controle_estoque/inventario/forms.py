from django import forms
from django.forms import ValidationError
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Produto, Categoria, TipoTransacao, Transacao, Item
from django.utils import timezone

class DateFilterForm(forms.Form):
    MONTH_CHOICES = [
        (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
        (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
        (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
    ]
    
    YEAR_CHOICES = [(year, year) for year in range(2020, timezone.now().year + 1)]
    
    month = forms.ChoiceField(choices=MONTH_CHOICES, label="Mês")
    year = forms.ChoiceField(choices=YEAR_CHOICES, label="Ano")

class CadastroUsuarioForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True, label="Nome")
    last_name = forms.CharField(max_length=30, required=True, label="Sobrenome")

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add classes to all fields
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})
            
            # Add specific classes for certain fields if needed
            if field_name == 'password1' or field_name == 'password2':
                field.widget.attrs.update({'class': 'form-control password-field'})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user

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
        self.fields['categoria'].queryset = Categoria.objects.filter()

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nome', 'descricao']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        self.fields['nome'].widget.attrs.update({'placeholder': 'Nome da categoria'})

class TransacaoForm(forms.ModelForm):
    produto = forms.ModelChoiceField(
        queryset=Produto.objects.all(),
        label="Produto"
    )

    lote = forms.CharField(
        required=False,
        label="Número do Lote",
        help_text="Obrigatório para entradas de estoque"
    )
    
    class Meta:
        model = Transacao
        fields = ['produto', 'tipo_transacao', 'quantidade', 'observacoes']
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        self.fields['tipo_transacao'].queryset = TipoTransacao.objects.filter()
        if 'tipo_transacao' in self.data:
            try:
                tipo_id = int(self.data.get('tipo_transacao'))
                tipo = TipoTransacao.objects.get(id=tipo_id)
                if not tipo.entrada:
                    self.fields['lote'].widget = forms.HiddenInput()
            except (ValueError, TipoTransacao.DoesNotExist):
                pass
    
    def clean(self):
        cleaned_data = super().clean()
        tipo_transacao = cleaned_data.get('tipo_transacao')
        produto = cleaned_data.get('produto')
        quantidade = cleaned_data.get('quantidade')
        lote = cleaned_data.get('lote')
        
        if tipo_transacao and tipo_transacao.entrada:
            if not lote:
                raise ValidationError({
                    'lote': "Informe o número do lote para entrada de estoque"
                })
        
        if tipo_transacao and not tipo_transacao.entrada and produto and quantidade:
            disponivel = produto.estoque_total
            if disponivel < quantidade:
                raise ValidationError(
                    f"Estoque insuficiente. Disponível: {disponivel}, Requerido: {quantidade}"
                )
        
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
            itens = [
                Item(
                    produto=produto,
                    transacao=transacao,
                    lote=lote,
                    disponivel=True
                )
                for _ in range(quantidade)
            ]
            Item.objects.bulk_create(itens)
        else:
            itens = Item.objects.filter(
                produto=produto,
                disponivel=True
            ).order_by('data_criacao')[:quantidade]
            
            if itens.count() < quantidade:
                raise ValidationError("Estoque insuficiente para completar a transação")
            
            for item in itens:
                item.disponivel = False
                item.transacao = transacao
                item.save()