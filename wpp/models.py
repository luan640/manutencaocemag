from django.db import models

class StatusMensagemWhatsApp(models.Model):
    message_id = models.CharField("ID da Mensagem", max_length=100, unique=True)
    telefone = models.CharField("Telefone (WhatsApp ID)", max_length=20)
    
    STATUS_CHOICES = [
        ('sent', 'Enviado'),
        ('delivered', 'Entregue'),
        ('read', 'Lido'),
        ('failed', 'Falha'),
        ('deleted', 'Deletado'),
    ]
    status = models.CharField("Status", max_length=20, choices=STATUS_CHOICES)
    descricao_erro = models.TextField("Descrição do erro", blank=True, null=True)
    
    data_status = models.DateTimeField("Data do status")
    data_registro = models.DateTimeField("Registrado em", auto_now_add=True)

    class Meta:
        verbose_name = "Status da Mensagem WhatsApp"
        verbose_name_plural = "Status das Mensagens WhatsApp"
        ordering = ['-data_status']

    def __str__(self):
        return f"{self.telefone} - {self.status} - {self.message_id}"
