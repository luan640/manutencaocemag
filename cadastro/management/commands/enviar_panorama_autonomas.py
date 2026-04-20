from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from cadastro.services import execute_daily_autonomous_overview


class Command(BaseCommand):
    help = 'Envia o panorama diario das respostas das manutencoes autonomas.'

    def add_arguments(self, parser):
        parser.add_argument('--date', dest='report_date', help='Data no formato YYYY-MM-DD.')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Monta o panorama e registra logs sem enviar e-mail.',
        )

    def handle(self, *args, **options):
        report_date = self._parse_date(options.get('report_date'))
        result = execute_daily_autonomous_overview(report_date, dry_run=options.get('dry_run'))
        self.stdout.write(
            f"Panorama de {report_date.strftime('%d/%m/%Y')}: "
            f"{result['response_count']} resposta(s), "
            f"{result['missing_count']} nao realizada(s), "
            f"{result['recipient_count']} destinatario(s)."
        )

        if result['skipped_reason']:
            self.stdout.write(self.style.WARNING(f"{result['skipped_reason']} Envio ignorado."))
            return

        if options.get('dry_run'):
            self.stdout.write(self.style.SUCCESS('Dry-run concluido sem envio de e-mail.'))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"E-mail enviado com sucesso. "
                f"Destinatarios: {result['recipient_count']} | "
                f"Respostas: {result['response_count']} | "
                f"Entregas reportadas: {result['sent_count']}"
            )
        )

    def _parse_date(self, raw_value):
        if not raw_value:
            return timezone.now().date() - timedelta(days=1)

        try:
            return datetime.strptime(raw_value, '%Y-%m-%d').date()
        except ValueError as exc:
            raise CommandError('Use --date no formato YYYY-MM-DD.') from exc
