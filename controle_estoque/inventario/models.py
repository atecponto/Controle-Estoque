from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

ATIVO = 0
INATIVO = 1
ACTIVE_CHOICES = ((ATIVO, 'Ativo'), (INATIVO, 'Inativo'))

class Categoria(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    def __str__(self): return self.nome
    class Meta:
        verbose_name = "Categoria"; verbose_name_plural = "Categorias"

class TipoTransacao(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    entrada = models.BooleanField(default=True)
    def __str__(self): return f"{self.nome} ({'Entrada' if self.entrada else 'Saída'})"
    class Meta:
        verbose_name = "Tipo de Transação"; verbose_name_plural = "Tipos de Transação"

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
        return self.item_set.filter(disponivel=True).count()
    
    def __str__(self): return f"{self.nome} (Estoque: {self.estoque_total})"
    class Meta:
        verbose_name = "Produto"; verbose_name_plural = "Produtos"; ordering = ['nome']

class Transacao(models.Model):
    tipo_transacao = models.ForeignKey(TipoTransacao, on_delete=models.PROTECT)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT)
    produto =  models.ForeignKey(Produto, on_delete=models.PROTECT)
    data = models.DateTimeField(default=timezone.now)
    quantidade = models.IntegerField()
    observacoes = models.TextField(blank=True, null=True)
    def __str__(self): return f"{self.tipo_transacao.nome} - {self.quantidade} itens - {self.data.strftime('%d/%m/%Y %H:%M')}"
    class Meta:
        verbose_name = "Transação"; verbose_name_plural = "Transações"; ordering = ['-data']

class Item(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    lote = models.CharField(max_length=100, blank=True, null=True)
    transacao = models.ForeignKey(Transacao, on_delete=models.CASCADE)
    disponivel = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(default=timezone.now)
    def __str__(self): return f"{self.produto.nome} - Lote: {self.lote}"
    class Meta:
        verbose_name = "Item"; verbose_name_plural = "Itens"

# ### MODELS DO MÓDULO DE CLIENTES ###

class Sistema(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True, null=True)
    def __str__(self): return self.nome

class Tecnico(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.nome

class Cliente(models.Model):
    TIPO_CONTRATO_CHOICES = [
        ('CONTRATO', 'Contrato'),
        ('VITALICIO', 'Vitalício'),
        ('CONTRATO_WEB', 'Contrato Web'),
        ('OUTRO', 'Outro'),
    ]
    razao_social = models.CharField(max_length=255)
    fantasia = models.CharField(max_length=255, blank=True, null=True)
    cnpj = models.CharField(max_length=18, unique=True)
    inscricao_estadual = models.CharField(max_length=20, blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)
    bairro = models.CharField(max_length=100, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    cep = models.CharField(max_length=9, blank=True, null=True)
    cidade = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=2, blank=True, null=True)
    contato = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    observacoes = models.TextField(blank=True, null=True)
    sistema = models.ForeignKey(Sistema, on_delete=models.SET_NULL, null=True, blank=True)
    tipo_contrato = models.CharField(max_length=20, choices=TIPO_CONTRATO_CHOICES, blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['razao_social']
    def __str__(self): return self.razao_social

class Agendamento(models.Model):
    SITUACAO_CHOICES = [('AGENDADO', 'Agendado'), ('CONCLUIDO', 'Concluído'), ('CANCELADO', 'Cancelado')]
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    tecnico = models.ForeignKey(Tecnico, on_delete=models.SET_NULL, null=True, blank=True, related_name="agendamentos_associados")
    descricao = models.TextField()
    data_agendamento = models.DateField()
    hora_agendamento = models.TimeField()
    situacao = models.CharField(max_length=10, choices=SITUACAO_CHOICES, default='AGENDADO')
    laudo_tecnico = models.TextField(blank=True, null=True)
    data_resolvido = models.DateTimeField(null=True, blank=True)
    atendido_por = models.ForeignKey(Tecnico, related_name='atendimentos_realizados', on_delete=models.SET_NULL, null=True, blank=True)
    class Meta:
        ordering = ['-data_agendamento']
    def __str__(self): return f"Agendamento para {self.cliente.fantasia}"

class OrdemDeServico(models.Model):
    STATUS_CHOICES = [
        ('ABERTA', 'Aberta'),
        ('EM_ANDAMENTO', 'Em Andamento'),
        ('CONCLUIDA', 'Concluída'),
        ('CANCELADA', 'Cancelada'),
    ]
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='ordens_servico')
    tecnico_responsavel = models.ForeignKey(Tecnico, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ABERTA')
    problema_relatado = models.TextField()
    solucao_aplicada = models.TextField(blank=True, null=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    data_abertura = models.DateTimeField(default=timezone.now)
    data_fechamento = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ['-data_abertura']
    def __str__(self):
        return f"OS #{self.id} - {self.cliente.razao_social}"