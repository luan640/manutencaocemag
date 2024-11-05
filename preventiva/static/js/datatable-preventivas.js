$(document).ready(function () {

  let area = document.getElementById('area').value;

  $('#preventivasTable').DataTable({
    processing: true,
    serverSide: true,
    ajax: {
      url: `?area=${area}`,  // Adiciona o parâmetro como query string
      type: 'GET',
    },
    columns: [
      { 
        data: 'maquina',
        render: function (data) {
          return `<span title="${data}">${truncateText(data, 20)}</span>`;  // Trunca e adiciona title
        }
      },
      { 
        data: 'nome'
      },
      { 
        data: 'descricao',
        render: function (data) {
          return `<span title="${data}">${truncateText(data, 20)}</span>`;  // Trunca e adiciona title
        }
      },
      { data: 'periodicidade' },
      { data: 'abertura_automatica' },
      { 
        data: 'id',
        render: function (data) {
          return `<a href="/plano-preventiva/edit/${data}/" class="btn btn-sm badge btn-primary">Editar</a>
                  <a href="#" class="btn btn-sm badge btn-danger btnExcluir" data-id="${data}" data-bs-toggle="modal" data-bs-target="#modalConfirmarExclusao">Excluir</a>`
        },
        orderable: false,  // Desabilita a ordenação para esta coluna
        searchable: false  // Desabilita a busca para esta coluna
      }
    ],
    pageLength: 5,  // Define que a tabela terá 5 registros por página
    lengthChange: false,  // Desativa o seletor de número de registros por página
    autoWidth: false,  // Impede o DataTables de definir uma largura fixa
    responsive: true,  // Torna a tabela responsiva
    language: {
      search: "Procurar por Nome do Plano:",
      paginate: {
        previous: "Anterior",
        next: "Próximo"
      }, 
      info: "Mostrando _START_ a _END_ de _TOTAL_ registros",  // Personaliza o texto de paginação
      zeroRecords: "Nenhum registro encontrado",  // Mensagem quando não há registros
      infoEmpty: "Mostrando 0 a 0 de 0 registros"
    }
  });

  // Função para truncar texto
  function truncateText(text, maxLength) {
    if (text.length > maxLength) {
      return text.substring(0, maxLength) + '...';
    }
    return text;
  }
});
