$(document).ready(function () {
  $('#preventivasTable').DataTable({
    processing: true,
    serverSide: true,
    ajax: {
      url: 'preventiva',  // A URL que vai retornar os dados
      type: 'GET',
    },
    columns: [
      { data: 'maquina' },
      { data: 'nome' },
      { data: 'descricao' },
      { data: 'periodicidade' },
      { data: 'abertura_automatica' },
      { // Coluna de Edição
        data: 'id',
        render: function (data, type, row) {
          return '<a href="/plano-preventiva/edit/' + data + '/" class="btn btn-sm btn-primary">Editar</a>';
          
        },
        orderable: false,  // Desabilita a ordenação para esta coluna
        searchable: false  // Desabilita a busca para esta coluna
      }
    ],
    language: {
      search: "Procurar por Nome do Plano:"  // Personaliza a label do campo de busca
    }
  });
});
