$(document).ready(function () {
  $('#execucaoTable').DataTable({
    processing: true,   // Mostra o indicador de processamento enquanto carrega os dados
    serverSide: true,    // Habilita o processamento no servidor
    ajax: {
      url: 'processa-historico/',  // A URL que vai retornar os dados
      type: 'POST',  // Método de envio (GET ou POST)
      data: function (d) {
        // Aqui você pode adicionar parâmetros extras que quer enviar ao servidor
        // Exemplo: d.extra_search = $('#extra').val();
      }
    },
    columns: [
      { data: 'ordem' },
      { data: 'data_inicio' },
      { data: 'data_fim' },
      { data: 'solicitante' },
      { data: 'che_maq_parada' },
      { data: 'exec_maq_parada' },
      { data: 'apos_exec_maq_parada' },
      { data: 'observacao' },
      { data: 'ultima_atualizacao' },
      { data: 'setor' },
      { data: 'maquina' },
      { data: 'status' },
      { data: 'area' }
      
    ],
    language: {
      search: "Procurar por número da ordem:"  // Aqui você define a label desejada
    }
  });
});
