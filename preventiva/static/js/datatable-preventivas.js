
$(document).ready(function () {

  let area = document.getElementById('area').value;

  const table = $('#preventivasTable').DataTable({
    processing: true,
    serverSide: true,
    ajax: {
      url: `?area=${area}`,  // Adiciona o parâmetro como query string
      type: 'GET',
      data: function (d) {
        d.maquina = $('#filtroMaquina').val(); // Adiciona o filtro de Máquina
        d.plano = $('#filtroPlano').val(); // Adiciona o filtro de Plano
      },
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
                  <a href="#" class="btn btn-sm badge btn-danger btnExcluir" data-id="${data}" data-bs-toggle="modal" data-bs-target="#modalConfirmarExclusao">Excluir</a>
                  <a href="#" class="btn btn-sm badge btn-info btnVisualizar" data-id="${data}">
                    <i class="fas fa-eye"></i>
                  </a>`
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
      paginate: {
        previous: "Anterior",
        next: "Próximo"
      }, 
      info: "Mostrando _START_ a _END_ de _TOTAL_ registros",  // Personaliza o texto de paginação
      zeroRecords: "Nenhum registro encontrado",  // Mensagem quando não há registros
      infoEmpty: "Mostrando 0 a 0 de 0 registros"
    },
    dom: 'lrtip'  // Remove o campo de pesquisa padrão ("f" foi removido)
  });

  // Função para truncar texto
  function truncateText(text, maxLength) {
    if (text.length > maxLength) {
      return text.substring(0, maxLength) + '...';
    }
    return text;
  }

  // Filtros
  $('#filtroMaquina, #filtroPlano').on('change', function () {
    table.ajax.reload(); // Recarrega a tabela quando o filtro muda
  });

  // Select2 para campos de filtros
  $('#filtroMaquina').select2({
    placeholder: 'Selecione a Máquina',
    allowClear: true,
    ajax: {
        url: '/get-maquinas-preventiva/',
        dataType: 'json',
        delay: 250,
        data: function (params) {
            return {
                search: params.term || '',
                page: params.page || 1,
                per_page: 10
            };
        },
        processResults: function (data, params) {
            params.page = params.page || 1;
            return {
                results: data.results.map(item => ({
                    id: item.id,
                    text: item.text
                })),
                pagination: {
                    more: data.pagination.more
                }
            };
        },
        cache: true
    },
    minimumInputLength: 0,
  });
  
});

