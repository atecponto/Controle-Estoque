from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

ATIVO = 0
INATIVO = 1

ACTIVE_CHOICES = (
    (ATIVO, 'Ativo'),
    (INATIVO, 'Inativo'),
)

class Categoria(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
    
    def __str__(self):
        return self.nome

class TipoTransacao(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    entrada = models.BooleanField(default=True)  # True para entrada, False para saída
    
    class Meta:
        verbose_name = "Tipo de Transação"
        verbose_name_plural = "Tipos de Transação"
    
    def __str__(self):
        return f"{self.nome} ({'Entrada' if self.entrada else 'Saída'})"


class Produto(models.Model):
    nome = models.CharField(max_length=255) 
    descricao = models.TextField(blank=True, null=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    data_criacao = models.DateTimeField(default=timezone.now)
    ultima_alteracao = models.DateTimeField(default=timezone.now)
    usuario_responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    ativo = models.IntegerField(choices=ACTIVE_CHOICES, default=ATIVO)
    
    @property
    def estoque_total(self):
        """Calcula o estoque total somando todos os itens disponíveis"""
        return self.item_set.filter(disponivel=True).count()
    
    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ['nome']
    
    def __str__(self):
        return f"{self.nome} (Estoque: {self.estoque_total})"


class Transacao(models.Model):
    tipo_transacao = models.ForeignKey(TipoTransacao, on_delete=models.PROTECT)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT)
    produto =  models.ForeignKey(Produto, on_delete=models.PROTECT)
    data = models.DateTimeField(default=timezone.now)
    quantidade = models.IntegerField()
    observacoes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Transação"
        verbose_name_plural = "Transações"
        ordering = ['-data']
    
    def __str__(self):
        return f"{self.tipo_transacao.nome} - {self.quantidade} itens - {self.data.strftime('%d/%m/%Y %H:%M')}"


class Item(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    lote = models.CharField(max_length=100, blank=True, null=True)
    transacao = models.ForeignKey(Transacao, on_delete=models.CASCADE)
    disponivel = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name = "Item"
        verbose_name_plural = "Itens"
    
    def __str__(self):
        return f"{self.produto.nome} - Lote: {self.lote}"