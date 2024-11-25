$(document).ready(function () {
  const table = $('#execucaoTable').DataTable({
      processing: true,
      serverSide: true,
      ajax: {
          url: 'processa-historico/',
          type: 'POST',
          data: function (d) {
              // Adiciona os filtros personalizados aos dados enviados ao backend
              d.status = $('#filterStatus').val();
              d.area = $('#filterArea').val();
              d.solicitante = $('#filterSolicitante').val();
              d.data_inicio = $('#filterDataInicio').val();
          }
      },
      columns: [
          { data: 'ordem' },
          { data: 'execucao' },
          { data: 'setor' },
          { data: 'solicitante' },
          { data: 'maquina' },
          { data: 'comentario_manutencao' },
          { data: 'motivo' },
          { data: 'data_abertura' },
          { data: 'data_inicio' },
          { data: 'data_fim' },
          { data: 'observacao' },
          { data: 'status' },
          { data: 'tipo_manutencao' },
          { data: 'area_manutencao' },
          { data: 'ultima_atualizacao' },
          { data: 'horas_executada' }
      ],
      language: {
        lengthMenu: "Exibir _MENU_ registros por página",
        zeroRecords: "Nenhuma execução encontrada",
        info: "Exibindo _START_ a _END_ de _TOTAL_ registros",
        infoEmpty: "Nenhum registro disponível",
        infoFiltered: "(filtrado de _MAX_ registros no total)"
      }
  });

  // Eventos para aplicar filtros
  $('#filterStatus, #filterArea, #filterSolicitante, #filterDataInicio').on('change keyup', function () {
      table.ajax.reload(); // Recarrega os dados da tabela
  });
});
